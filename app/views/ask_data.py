import re

import pandas as pd
import plotly.express as px
import streamlit as st

from ai.ask_data.answer import RATIO_METRICS
from ai.ask_data.filters import ALLOWED_CHANNELS, ALLOWED_PLATFORMS
from ai.ask_data.narrative import SENTIMENT_LABELS, THEME_LABELS
from ai.ask_data.semantic_layer import get_metric
from ai.ask_data.service import run_ask_data
from common import get_language_model
from theme import BISSAP, GINGEMBRE_DARK, SENTIMENT_COLORS, icon, month_label, section, show_chart


HISTORY_KEY = "ask_data_history"
PENDING_KEY = "ask_data_pending"

# Infobulle du titre : une seule ligne HTML, une ligne vide casserait le rendu.
HELP = (
    "<ul>"
    "<li><b>Métriques</b> : chiffre d'affaires net, dépenses marketing, mix produit ; "
    "voix du client : sentiment, commentaires positifs, négatifs et neutres, "
    "spam, volume de commentaires, thèmes abordés.</li>"
    "<li><b>Découpages</b> : par mois, par canal, par produit, par format, "
    "par plateforme pour les commentaires (selon la métrique).</li>"
    "<li><b>Filtres</b> : un mois (« en juin 2026 », « en mai » ou « ce mois-ci » pour le plus récent), "
    "une période relative (« ces 3 derniers mois », « le dernier trimestre »), "
    "un canal (Meta, TikTok, Google, Radio…), un produit (bissap, bouye, gingembre), "
    "une plateforme de commentaires (Facebook, Instagram, TikTok).</li>"
    "<li><b>Hors périmètre</b> : les questions causales (« quel canal a causé… »), "
    "les prévisions et les métriques non définies (ROI, coût par litre…) "
    "sont refusées plutôt que d'inventer une réponse.</li>"
    "<li><b>Questions libres</b> : si la question n'est pas reconnue, l'IA en propose "
    "une interprétation (quoi mesurer, comment découper), affichée avec la réponse. "
    "Les produits, canaux et dates sont toujours lus dans votre question.</li>"
    "<li><b>Toutes les réponses sont calculées à partir des données réelles</b>, "
    "selon des définitions de métriques validées.</li>"
    "</ul>"
)

# (clé, titre, icône, questions) : un bloc d'exemples par domaine.
EXAMPLE_GROUPS = [
    (
        "sales",
        "Ventes et marketing",
        "payments",
        [
            "Quel est le CA net en juin 2026 ?",
            "Quel est le CA net par mois ?",
            "Combien avons-nous dépensé sur Meta en juin 2026 ?"
        ],
    ),
    (
        "voice",
        "Voix du client",
        "forum",
        [
            "Quel est le sentiment des clients ?",
            "Comment évolue le sentiment des clients par mois ?",
            "Quel est le taux de commentaires négatifs ?",
        ],
    ),
]


# ---------------------------------------------------------------------
# MESSAGES D'ERREUR
# ---------------------------------------------------------------------
# Le pipeline renvoie des messages techniques (vérifiés par les tests) :
# ils sont traduits ici en langage courant, avec une question à essayer.

METRIC_LABELS = {
    "ca_net": "le chiffre d'affaires",
    "spend_marketing": "les dépenses marketing",
    "mix_produit": "le mix produit",
    "repartition_sentiment": "le sentiment des clients",
    "themes_commentaires": "les thèmes des commentaires",
    "commentaires_positifs": "les commentaires positifs",
    "commentaires_negatifs": "les commentaires négatifs",
    "commentaires_neutres": "les commentaires neutres",
    "commentaires_total": "le volume de commentaires",
    "commentaires_exploitables": "les commentaires exploitables",
    "commentaires_spam": "les commentaires indésirables",
    "sentiment_client": "la part de commentaires négatifs",
    "taux_positifs": "la part de commentaires positifs",
    "taux_spam": "le taux de spam",
}

DIMENSION_LABELS = {
    "month": "par mois",
    "channel": "par canal",
    "product": "par produit",
    "format": "par format",
    "platform": "par plateforme",
    "commune": "par commune",
    "product_sku": "par référence produit",
    "sale_date": "par jour",
    "pos_key": "par point de vente",
}

UNSUPPORTED_LABELS = {
    "roi": "le retour sur investissement (ROI)",
    "retour sur investissement": "le retour sur investissement (ROI)",
    "coût par litre": "le coût par litre vendu",
    "cout par litre": "le coût par litre vendu",
    "chiffre d'affaires livraison": "le chiffre d'affaires de la livraison",
    "ca livraison": "le chiffre d'affaires de la livraison",
}

AVAILABLE_METRICS = (
    "Je peux vous renseigner sur le chiffre d'affaires, les dépenses marketing, "
    "le mix produit et les commentaires clients (sentiment, spam, thèmes)."
)


def _join(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " ou " + items[-1]


def friendly_error(error: str) -> dict:
    """Traduit une erreur du pipeline en message compréhensible par tous."""

    if error.startswith("Analyse causale"):
        return {
            "title": "Je ne peux pas dire ce qui a provoqué un résultat.",
            "body": "Les données montrent ce qui s'est passé, pas pourquoi. "
            "Comparer les chiffres côte à côte peut toutefois vous aider "
            "à vous faire une idée.",
            "suggestion": "Quel est le spend par canal ?",
        }

    if error.startswith("Prévision"):
        return {
            "title": "Je ne fais pas de prévisions.",
            "body": "Je réponds uniquement à partir des chiffres déjà "
            "enregistrés. Regarder l'évolution des derniers mois peut "
            "donner une tendance.",
            "suggestion": "Quel est le CA net par mois ?",
        }

    if error.startswith("Métrique non supportée"):
        term = re.search(r"'(.+?)'", error)
        label = UNSUPPORTED_LABELS.get(term.group(1) if term else "", "cet indicateur")
        return {
            "title": "Cet indicateur n'est pas encore disponible.",
            "body": f"Je ne sais pas encore calculer {label}. {AVAILABLE_METRICS}",
            "suggestion": "Quel est le spend par canal ?",
        }

    if error.startswith("Question hors périmètre"):
        return {
            "title": "Je n'ai pas compris quel chiffre vous cherchez.",
            "body": f"{AVAILABLE_METRICS} Précisez lequel vous intéresse.",
            "suggestion": "Quel est le CA net par mois ?",
        }

    dimension = re.search(
        r"dimension '(\w+)'.*métrique '(\w+)'.*Dimensions disponibles : \[(.*)\]",
        error,
    )
    if dimension:
        asked, metric, allowed = dimension.groups()
        allowed = [
            DIMENSION_LABELS[d]
            for d in re.findall(r"'(\w+)'", allowed)
            if d in DIMENSION_LABELS
        ]
        body = (
            f"Il n'est pas possible d'afficher {METRIC_LABELS.get(metric, 'cet indicateur')} "
            f"{DIMENSION_LABELS.get(asked, 'de cette façon')}."
        )
        if allowed:
            body += f" Découpages disponibles : {_join(allowed)}."
        return {
            "title": "Ce découpage n'est pas disponible.",
            "body": body,
            "suggestion": None,
        }

    if error.startswith("Période ambiguë"):
        return {
            "title": "La question contient deux périodes différentes.",
            "body": "Indiquez soit un mois précis (« en juin 2026 »), soit une "
            "période récente (« ces 3 derniers mois »), mais pas les deux.",
            "suggestion": "Quel est le spend par canal ces 3 derniers mois ?",
        }

    if error.startswith("Mois invalide") or "nombre de mois" in error:
        return {
            "title": "Je n'ai pas reconnu la période demandée.",
            "body": "Écrivez le mois en toutes lettres suivi de l'année "
            "(« en juin 2026 ») ou un nombre de mois "
            "(« ces 3 derniers mois »).",
            "suggestion": "Quel est le CA net en juin 2026 ?",
        }

    if error.startswith("Plateforme inconnue"):
        return {
            "title": "Les commentaires ne sont suivis que sur trois plateformes.",
            "body": "Les commentaires clients proviennent de "
            f"{', '.join(ALLOWED_PLATFORMS)}.",
            "suggestion": "Donne-moi le sentiment par plateforme.",
        }

    if error.startswith("Canal inconnu"):
        return {
            "title": "Je ne connais pas ce canal.",
            "body": f"Les canaux suivis sont : {', '.join(ALLOWED_CHANNELS)}.",
            "suggestion": "Quel est le spend par canal ?",
        }

    return {
        "title": "Je n'ai pas pu répondre à cette question.",
        "body": "Essayez de la reformuler plus simplement, en précisant "
        "l'indicateur et la période qui vous intéressent.",
        "suggestion": "Quel est le CA net par mois ?",
    }


DATA_UNAVAILABLE = {
    "title": "Les données ne sont pas accessibles pour le moment.",
    "body": "Réessayez dans quelques instants. Si le problème persiste, "
    "contactez l'équipe data.",
    "suggestion": None,
}


def answer_question(question: str, use_llm: bool) -> dict:
    """Exécute le pipeline Ask the Data et prépare les données pour l'affichage."""
    # Le modèle n'est chargé que si les règles ne comprennent pas la question.
    model_loader = get_language_model if use_llm else None

    try:
        response = run_ask_data(question, model_loader=model_loader)
    except Exception:
        # Base absente ou verrouillée : le pipeline ne gère que les ValueError.
        return {"question": question, "error": DATA_UNAVAILABLE}

    if response.error:
        return {
            "question": question,
            "error": friendly_error(response.error),
        }

    return {
        "question": question,
        "answer": response.narrative or response.answer,
        "intent": response.intent,
        "result": response.result,
        # Autres métriques citées (« les ventes et les dépenses »).
        "extras": [(part.intent, part.result) for part in response.extras],
        # Interprétation affichée quand la question a été comprise par l'IA.
        "interpretation": response.interpretation if response.used_llm else None,
    }


def ask_suggestion(suggestion: str) -> None:
    st.session_state[PENDING_KEY] = suggestion


def composite_chart(intent, result: pd.DataFrame, components: list[str], key: str) -> None:
    """Répartitions : sentiment empilé (positif, neutre, négatif) ou thèmes classés."""
    data = result.copy()

    if intent.metric == "themes_commentaires":
        totals = data[components].sum().rename(index=THEME_LABELS).sort_values()
        fig = px.bar(
            x=totals.values,
            y=totals.index,
            orientation="h",
            color_discrete_sequence=[GINGEMBRE_DARK],
        )
        fig.update_layout(xaxis_title=None, yaxis_title=None)
        show_chart(fig, height=340, key=key)
        return

    dimensions = [d for d in intent.dimensions if d in data.columns]

    if "month" in data.columns:
        data["month"] = pd.to_datetime(data["month"])
        data = data.sort_values("month")
        data["mois"] = data["month"].map(month_label)

    x = "mois" if "month" in dimensions else (dimensions[0] if dimensions else None)
    facet = "platform" if "month" in dimensions and "platform" in dimensions else None
    keys = [k for k in (x, facet) if k]

    long = (
        data.groupby(keys, as_index=False, sort=False)[components].sum()
        if keys
        else data[components].sum().to_frame().T
    ).melt(id_vars=keys, value_vars=components, var_name="sentiment", value_name="commentaires")
    long["sentiment"] = long["sentiment"].map(SENTIMENT_LABELS)

    fig = px.bar(
        long,
        x=x or "sentiment",
        y="commentaires",
        color="sentiment",
        facet_col=facet,
        color_discrete_map=SENTIMENT_COLORS,
        category_orders={"sentiment": list(SENTIMENT_LABELS.values())},
    )
    fig.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    fig.update_layout(xaxis_title=None, yaxis_title=None, legend_title_text="")
    show_chart(fig, height=340, key=key)


def result_chart(intent, result: pd.DataFrame, key: str) -> None:
    """Graphique simple lorsque la réponse est découpée par une ou deux dimensions."""
    components = list((get_metric(intent.metric) or {}).get("composantes", {}))

    if components:
        composite_chart(intent, result, components, key)
        return

    dimensions = [d for d in intent.dimensions if d in result.columns]

    if not dimensions or len(result) < 2:
        return

    data = result.copy()
    x = dimensions[0]
    color = dimensions[1] if len(dimensions) > 1 else None

    if x == "month":
        data["month"] = pd.to_datetime(data["month"])
        data = data.sort_values("month")
        data["mois"] = data["month"].map(month_label)
        x = "mois"

    fig = px.bar(
        data,
        x=x,
        y=intent.metric,
        color=color,
        barmode="group",
        color_discrete_sequence=None if color else [BISSAP],
    )
    fig.update_layout(xaxis_title=None, yaxis_title=None)

    if intent.metric in RATIO_METRICS:
        fig.update_yaxes(tickformat=".0%")

    # Clé obligatoire : deux réponses identiques donneraient le même graphique.
    show_chart(fig, height=320, key=key)


def show_entry(index: int, entry: dict) -> None:
    # Conteneurs nommés : le thème aligne la question à droite, la réponse à gauche.
    with st.container(key=f"chat_user_{index}"), st.chat_message("user"):
        st.markdown(entry["question"])

    with st.container(key=f"chat_assistant_{index}"), st.chat_message("assistant"):
        if "error" in entry:
            error = entry["error"]
            st.markdown(f"**{error['title']}**  \n{error['body']}")

            if error["suggestion"]:
                st.button(
                    f"Essayer : {error['suggestion']}",
                    key=f"ask_suggestion_{index}",
                    icon=":material/lightbulb:",
                    on_click=ask_suggestion,
                    args=(error["suggestion"],),
                )
        else:
            if entry.get("interpretation"):
                st.caption(
                    ":material/auto_awesome: Question interprétée par l'IA : "
                    f"{entry['interpretation']}. Reformulez si ce n'est pas ce que vous cherchiez."
                )

            st.markdown(entry["answer"].replace("\n", "  \n"))
            if entry["result"] is not None:
                result_chart(entry["intent"], entry["result"], key=f"ask_chart_{index}")

            for part_index, (intent, result) in enumerate(entry.get("extras", [])):
                result_chart(intent, result, key=f"ask_chart_{index}_{part_index}")


section(
    6,
    "Ask the Data",
    "Posez une question sur les ventes, les dépenses marketing ou les commentaires "
    "clients : la réponse est calculée directement à partir des données.",
    help=HELP,
)

history = st.session_state.setdefault(HISTORY_KEY, [])


# ---------------------------------------------------------------------
# EXEMPLES
# ---------------------------------------------------------------------

caption_col, toggle_col = st.columns([3, 2], vertical_alignment="center")

with caption_col:
    st.caption("Exemples de questions")

with toggle_col:
    use_llm = st.toggle(
        "Comprendre les questions libres (IA)",
        value=True,
        key="ask_data_use_llm",
        help=(
            "Si la question n'est pas reconnue, l'IA propose une interprétation, "
            "vérifiée avant tout calcul et affichée avec la réponse. "
            "La première utilisation charge le modèle (plus long)."
        ),
    )

clicked = None

for group_key, group_title, group_icon, examples in EXAMPLE_GROUPS:
    with st.container(key=f"ask_examples_{group_key}"):
        st.markdown(
            f'<div class="examples-title">{icon(group_icon)}{group_title}</div>',
            unsafe_allow_html=True,
        )
        example_cols = st.columns(3)

        for i, example in enumerate(examples):
            with example_cols[i % 3]:
                if st.button(
                    example,
                    key=f"ask_example_{group_key}_{i}",
                    icon=":material/north_east:",
                    width="stretch",
                ):
                    clicked = example


# ---------------------------------------------------------------------
# CONVERSATION
# ---------------------------------------------------------------------

question = (
    st.chat_input("Ex. : Quel est le spend par canal ?")
    or clicked
    or st.session_state.pop(PENDING_KEY, None)
)

if question:
    with st.spinner("Analyse de la question…"):
        history.append(answer_question(question, use_llm))

for index, entry in enumerate(history):
    show_entry(index, entry)

if history and st.button("Effacer la conversation", icon=":material/delete:"):
    st.session_state[HISTORY_KEY] = []
    st.rerun()
