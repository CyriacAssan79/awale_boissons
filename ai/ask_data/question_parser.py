from __future__ import annotations

import re
import unicodedata

from .dimensions import resolve_dimension
from .filters import (
    CHANNEL_ALIASES,
    PLATFORM_ALIASES,
    PRODUCT_ALIASES,
    resolve_channel,
    resolve_platform,
    resolve_product,
)
from .intent import build_intent
from .periods import (
    LATEST_MONTH,
    extract_month,
    extract_month_without_year,
    extract_relative_months,
    extract_since,
    mentions_latest_month,
)
from .resolver import resolve_metric


def normalize(text: str) -> str:
    """Minuscules, sans accents, apostrophes et espaces uniformisés.

    « Chiffre d’Affaire », « chiffre d'affaires » et « CHIFFRE D'AFFAIRES »
    deviennent comparables.
    """
    # « ça » est un pronom : sans la cédille, il deviendrait « ca » (chiffre d'affaires).
    text = re.sub(r"\bça\b", "cela", text.lower())
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = re.sub(r"[’`´]", "'", text)
    return re.sub(r"\s+", " ", text).strip()


def _contains(term: str, text: str) -> bool:
    """Cherche un terme comme mot entier : « ca » ne doit pas trouver « canal »."""
    return re.search(rf"(?<!\w){re.escape(normalize(term))}(?!\w)", text) is not None


# Façons de désigner chaque métrique (texte normalisé, sans accents).
METRIC_PATTERNS = {
    "mix_produit": [
        r"\bmix\b",
    ],
    "spend_marketing": [
        r"\bdepens\w*",             # dépense, dépenses, dépensé, dépenser
        r"\bspend\b",
        r"\bbudgets?\b",
        r"\binvesti\w*",            # investi, investissement
        r"\bcout\w*",               # coût, coûte, coûté (« combien coûte la pub »)
    ],
    # Voix du client : la métrique précise (sentiment, spam, volume…) est
    # choisie ensuite par _comment_metric.
    "voix_client": [
        r"\bcommentaires?\b",
        r"\bsentiments?\b",
        r"\bressenti\b",
        r"\b(?:in)?satisf\w*",           # satisfaits, insatisfaction
        r"\bmecontent\w*",
        r"\bavis\b",
        r"\bretours? (?:des |de nos )?clients?\b",
        r"\bretours? (?:positifs?|negatifs?|neutres?)\b",
        r"\bclients?\b.*\b(?:pensent|disent|parlent|reagiss\w*)\b",
        r"\b(?:pensent|disent|parlent|reagiss\w*)\b.*\bclients?\b",
        r"\breactions? des clients?\b",
        r"\bvoix (?:du|des) clients?\b",
        r"\bthemes?\b",
        r"\bsujets? (?:les plus )?abordes\b",
        r"\bspams?\b",
        r"\bindesirables?\b",
        r"\bpositi(?:f|fs|ve|ves|vement)\b",
        r"\bnegati(?:f|fs|ve|ves|vement)\b",
    ],
    "ca_net": [
        r"\bchiffres? d\s*'?\s*affaires?\b",
        r"\bca\b",
        r"\brevenus?\b",
        r"\brecettes?\b",
        r"\bventes?\b",
        r"\bvend(?:u|us|ue|ues|re|ons|ez|ent|ait|aient)\b",   # « combien avons-nous vendu »
        r"\brapport(?:e|es|ent|ait|aient)\b",   # « combien rapporte… »
        r"\bfait combien\b",                    # « on a fait combien »
        r"\bcombien\b.*\bfait\b",               # « combien avons-nous fait »
        r"\b(?:les|nos) affaires\b",            # « comment vont les affaires »
        r"\bactivite\b",
        r"\bbusiness\b",
    ],
}

UNSUPPORTED_METRICS = [
    "roi",
    "retour sur investissement",
    "coût par litre",
    "cout par litre",
    "chiffre d'affaires livraison",
    "ca livraison",
]

# Motifs sur le texte normalisé. « influenc… » est limité aux formes du
# verbe : « influenceurs » est un canal, pas une question causale.
CAUSAL_PATTERNS = [
    r"\bcaus\w*",
    r"\bpourquoi\b",
    r"\bimpact\w*",
    r"\binfluenc(?:e|es|ee|ees|er|ent|ait|aient)\b",
    r"\bresponsab\w*",
]

FORECAST_TERMS = [
    "prévoir",
    "prévision",
    "prévisions",
    "prédire",
    "prédiction",
    "prévisionnel",
    "sera",
    "seront",
    "prochain mois",
    "mois prochain",
]

# Mots désignant chaque découpage, au singulier et au pluriel.
DIMENSION_WORDS = {
    "mois": "mois",
    "canal": "canal|canaux",
    "produit": "produits?",
    "plateforme": "plateformes?",
    "commune": "communes?",
    "format": "formats?",
}

# « par canal », « chaque produit », « quel mois », « selon le canal »…
# « entre les produits », « des canaux »
DIMENSION_BEFORE = (
    r"par|chaque|quel|quels|quelle|quelles|des"
    r"|selon(?: le| la| les)?|entre(?: les)?"
)

# « le canal qui… », « les produits ayant… », « le produit le plus vendu »
DIMENSION_AFTER = r"qui|ou|ayant|dont|(?:le|la|les) (?:plus|moins|mieux)"

# Évolution, tendance ou résumé dans le temps : découpage par mois implicite.
MONTH_TRIGGERS = [
    r"\bmensuel\w*",            # mensuel, mensuellement
    r"\bevolu\w*",              # évolue, évolution
    r"\bau fil des mois\b",
    r"\bmois apres mois\b",
    r"\bdans le temps\b",
    r"\btendance\w*",
    r"\bse port\w*",            # « comment se porte le CA »
    r"\bcomment va\b",
    r"\bcela va\b",             # « ça va les affaires ? »
    r"\ben ce moment\b",
    r"\bces derniers temps\b",
    r"\brecemment\b",
    r"\bactuellement\b",
    r"\baugment\w*",
    r"\bdiminu\w*",
    r"\bbaiss\w*",
    r"\bhausse\b",
    r"\bprogress\w*",
    r"\brecul\w*",
    r"\bamelior\w*",          # « les retours s'améliorent »
    r"\bdegrad\w*",
    r"\bresum\w*",              # résumé, résume-moi
    r"\bbilan\b",
    r"\bsynthese\b",
]

# Dépenses : « sur quoi avons-nous dépensé » = par canal.
CHANNEL_TRIGGERS = [
    r"\bsur quoi\b",
    r"\bdans quoi\b",
    r"\bou va l'argent\b",
    r"\bou (?:avons-nous|a-t-on|on a|est passe)\b",
]

# Le chiffre d'affaires par produit ou par format est porté par la
# métrique mix_produit (même chiffre d'affaires, détaillé par produit).
PRODUCT_DIMENSIONS = {"produit", "format"}

# Classement demandé : les termes « min » sont testés en premier
# (« le moins bien » avant « bien »).
COMPARISON_TERMS = {
    "min": ["le moins", "la moins", "les moins", "plus faible", "plus faibles",
            "plus bas", "plus basse", "minimum"],
    "max": ["le plus", "la plus", "les plus", "plus élevé", "plus élevée",
            "plus gros", "plus grosse", "maximum", "meilleur", "meilleure",
            "en tête", "le mieux"],
}


# ---------------------------------------------------------------------
# VOIX DU CLIENT
# ---------------------------------------------------------------------

COMMENT_METRICS = {
    "repartition_sentiment",
    "commentaires_positifs",
    "commentaires_negatifs",
    "commentaires_neutres",
    "taux_positifs",
    "sentiment_client",
    "commentaires_total",
    "commentaires_exploitables",
    "commentaires_spam",
    "taux_spam",
    "themes_commentaires",
}

RATE_WORDS = r"\b(?:taux|part|pourcentage|proportion|ratio)\b"
POSITIVE_WORDS = r"\bpositi(?:f|fs|ve|ves|vement)\b|\bsatisf\w*|\bcontents?\b"
NEGATIVE_WORDS = r"\bnegati(?:f|fs|ve|ves|vement)\b|\bmecontent\w*|\binsatisf\w*"
NEUTRAL_WORDS = r"\bneutres?\b"
SPAM_WORDS = r"\bspams?\b|\bindesirables?\b"
USABLE_WORDS = r"\bexploitables?\b|\bnon[- ]spam\b|\butiles\b|\bvalides\b"
VOLUME_WORDS = (
    r"\bcombien\b.*\bcommentaires\b|\bnombre de commentaires\b"
    r"|\bvolume\b|\bquantite de commentaires\b"
)
THEME_WORDS = r"\bthemes?\b|\bsujets?\b"

COUNT_TO_RATE = {
    "commentaires_negatifs": "sentiment_client",
    "commentaires_positifs": "taux_positifs",
}

TREND_WORDS = (
    r"\baugment\w*|\bdiminu\w*|\bbaiss\w*|\bhausse\b|\bevolu\w*"
    r"|\bamelior\w*|\bdegrad\w*|\btendance\w*|\bprogress\w*|\brecul\w*"
)

# Questions de synthèse : les thèmes abordés complètent le sentiment.
SUMMARY_WORDS = (
    r"\bresum\w*|\bbilan\b|\bsynthese\b|\bressort\w*"
    r"|\b(?:pensent|disent|reagiss\w*)\b|\bde quoi\b"
)


def _comment_metric(text: str) -> str:
    """Métrique précise d'une question sur les commentaires clients."""
    rate = re.search(RATE_WORDS, text)

    if re.search(SPAM_WORDS, text):
        return "taux_spam" if rate else "commentaires_spam"

    if re.search(USABLE_WORDS, text):
        return "commentaires_exploitables"

    if re.search(THEME_WORDS, text):
        return "themes_commentaires"

    positive = bool(re.search(POSITIVE_WORDS, text))
    negative = bool(re.search(NEGATIVE_WORDS, text))
    neutral = bool(re.search(NEUTRAL_WORDS, text))

    # « satisfaits ou mécontents », « positivement ou négativement » : répartition.
    if positive + negative + neutral > 1:
        return "repartition_sentiment"

    if negative:
        return "sentiment_client" if rate else "commentaires_negatifs"

    if positive:
        return "taux_positifs" if rate else "commentaires_positifs"

    if neutral:
        return "commentaires_neutres"

    if re.search(VOLUME_WORDS, text):
        return "commentaires_total"

    return "repartition_sentiment"


def comment_platforms(text: str) -> str | list[str] | None:
    """Plateformes citées dans une question sur les commentaires (texte normalisé).

    « Meta » vaut Facebook et Instagram. Un canal sans commentaires
    (Google, radio…) est refusé plutôt qu'ignoré.
    """
    platforms = _find_all(PLATFORM_ALIASES, resolve_platform, text)

    if re.search(r"(?<!\w)meta(?!\w)", text):
        platforms = list(dict.fromkeys([*platforms, "Facebook", "Instagram"]))

    channels = set(_find_all(CHANNEL_ALIASES, resolve_channel, text)) - {"Meta", "TikTok"}

    if channels:
        raise ValueError(
            f"Plateforme inconnue : '{sorted(channels)[0]}'. "
            "Plateformes disponibles : Facebook, Instagram, TikTok"
        )

    return _single_or_list(platforms)


def _resolve_comment_metrics(metrics: list[str], text: str) -> list[str]:
    """Remplace « voix_client » par la métrique précise, plus les thèmes pour une synthèse."""
    if "voix_client" not in metrics:
        return metrics

    metric = _comment_metric(text)
    resolved = [metric]

    if metric == "repartition_sentiment" and re.search(SUMMARY_WORDS, text):
        resolved.append("themes_commentaires")

    # « Les avis négatifs augmentent-ils ? » : un nombre dépend du volume du
    # mois, la part est donnée à côté.
    if metric in COUNT_TO_RATE and re.search(TREND_WORDS, text):
        resolved.append(COUNT_TO_RATE[metric])

    index = metrics.index("voix_client")
    return list(dict.fromkeys(metrics[:index] + resolved + metrics[index + 1:]))


def _find_all(aliases: dict, resolve, text: str) -> list[str]:
    """Valeurs citées dans la question, sans doublon, dans l'ordre d'apparition."""
    found = []

    for alias in aliases:
        match = re.search(rf"(?<!\w){re.escape(normalize(alias))}(?!\w)", text)

        if match:
            found.append((match.start(), resolve(alias)))

    return list(dict.fromkeys(value for _, value in sorted(found)))


def _single_or_list(values: list[str]) -> str | list[str] | None:
    """Un seul élément : filtre simple. Plusieurs : comparaison entre eux."""
    if not values:
        return None

    return values[0] if len(values) == 1 else values


def _detect_metrics(text: str) -> list[str]:
    """Métriques citées, dans l'ordre de la question (« les ventes et les dépenses »)."""
    positions = {}

    for metric, patterns in METRIC_PATTERNS.items():
        matches = [m.start() for p in patterns if (m := re.search(p, text))]

        if matches:
            positions[metric] = min(matches)

    # Le mix produit est déjà du chiffre d'affaires : pas de doublon.
    if "mix_produit" in positions:
        positions.pop("ca_net", None)

    return sorted(positions, key=positions.get)


def _detect_dimensions(text: str) -> list[str]:
    names = []

    for dimension_name, words in DIMENSION_WORDS.items():
        before = rf"\b(?:{DIMENSION_BEFORE})\s+(?:{words})\b"
        after = rf"\b(?:le|la|les)\s+(?:{words})\s+(?:{DIMENSION_AFTER})\b"

        mentioned = re.search(before, text) or re.search(after, text)

        if dimension_name == "mois" and any(
            re.search(trigger, text) for trigger in MONTH_TRIGGERS
        ):
            mentioned = True

        if mentioned:
            names.append(dimension_name)

    return names


def extract_period(question: str) -> dict:
    """Période citée, sous forme de paramètres de build_intent.

    Partagé avec l'interprétation par le modèle : les mois et années
    viennent toujours du texte de la question, jamais du modèle.
    """
    since, since_month_of_year = extract_since(question)
    relative_months = extract_relative_months(question)

    month = month_of_year = None

    # « depuis janvier » : le mois cité est un point de départ, pas un filtre.
    if not (since or since_month_of_year):
        month = extract_month(question)

        # « en mai » sans année : résolu plus tard d'après les données.
        month_of_year = None if month else extract_month_without_year(question)

        # « le mois dernier » : dernier mois disponible, résolu de la même façon.
        if not month and not month_of_year and not relative_months and mentions_latest_month(question):
            month_of_year = LATEST_MONTH

    periods = [
        bool(month or month_of_year),
        bool(since or since_month_of_year),
        bool(relative_months),
    ]

    if sum(periods) > 1:
        raise ValueError(
            "Période ambiguë : la question contient à la fois "
            "un mois précis et une période relative."
        )

    found = {
        "month": month,
        "month_of_year": month_of_year,
        "since": since,
        "since_month_of_year": since_month_of_year,
        "relative_months": relative_months,
    }
    return {key: value for key, value in found.items() if value}


def extract_mentions(question: str) -> tuple:
    """Produits et canaux cités : valeur simple, liste (comparaison) ou None."""
    text = normalize(question)

    return (
        _single_or_list(_find_all(PRODUCT_ALIASES, resolve_product, text)),
        _single_or_list(_find_all(CHANNEL_ALIASES, resolve_channel, text)),
    )


def parse_question(question: str):
    """Transforme une question simple en QueryIntent."""

    text = normalize(question)

    # ---------------------------------------------------------
    # 0. Détection des analyses non supportées
    # ---------------------------------------------------------

    if any(re.search(pattern, text) for pattern in CAUSAL_PATTERNS):
        raise ValueError(
            "Analyse causale non supportée : "
            "Ask the Data ne permet pas d'attribuer une causalité "
            "à partir des données disponibles."
        )

    if any(normalize(term) in text for term in FORECAST_TERMS):
        raise ValueError(
            "Prévision non supportée : "
            "Ask the Data fournit uniquement des analyses "
            "des données observées."
        )

    # ---------------------------------------------------------
    # 1. Résolution de la métrique
    # ---------------------------------------------------------

    metrics = _resolve_comment_metrics(_detect_metrics(text), text)
    dimension_names = _detect_dimensions(text)

    product = _single_or_list(_find_all(PRODUCT_ALIASES, resolve_product, text))
    channel = _single_or_list(_find_all(CHANNEL_ALIASES, resolve_channel, text))
    platform = None

    # Commentaires : Facebook, Instagram et TikTok sont des plateformes,
    # pas des canaux de dépense.
    if metrics and metrics[0] in COMMENT_METRICS:
        platform = comment_platforms(text)
        channel = None

    # Sans mot de métrique, le sujet de la question la désigne :
    # « Combien de bissap en mai ? », « Quel produit marche le mieux ? »
    # → chiffre d'affaires ; « Compare Meta et TikTok » → dépenses.
    if not metrics and (product or PRODUCT_DIMENSIONS & set(dimension_names)):
        metrics = ["ca_net"]

    if not metrics and channel:
        metrics = ["spend_marketing"]

    for unsupported in UNSUPPORTED_METRICS:
        if _contains(unsupported, text):
            raise ValueError(
                f"Métrique non supportée : '{unsupported}'. "
                "Cette métrique n'est pas définie dans le semantic layer."
            )

    if not metrics:
        raise ValueError(
            "Question hors périmètre : "
            "aucune métrique prise en charge n'a été identifiée."
        )

    # La première métrique citée porte la question ; les suivantes
    # (« les ventes et les dépenses ») sont traitées par le service.
    metric, other_metrics = metrics[0], metrics[1:]

    # ---------------------------------------------------------
    # 2. Résolution de la période
    # ---------------------------------------------------------

    period = extract_period(question)

    # ---------------------------------------------------------
    # 3. Résolution des dimensions
    # ---------------------------------------------------------

    # Plusieurs produits ou canaux cités (« compare le bissap et le
    # gingembre ») : on découpe par cet axe, limité aux éléments cités.
    if isinstance(product, list) and "produit" not in dimension_names:
        dimension_names.insert(0, "produit")

    if isinstance(channel, list) and "canal" not in dimension_names:
        dimension_names.insert(0, "canal")

    if isinstance(platform, list) and "plateforme" not in dimension_names:
        dimension_names.insert(0, "plateforme")

    # « Sur quoi avons-nous le plus dépensé ? » : par canal.
    if (
        metric == "spend_marketing"
        and "canal" not in dimension_names
        and any(re.search(trigger, text) for trigger in CHANNEL_TRIGGERS)
    ):
        dimension_names.insert(0, "canal")

    # « Quel est le mix produit ? » : le mix est une répartition par
    # produit, sauf si la question vise un seul produit ou un format.
    if (
        metric == "mix_produit"
        and not isinstance(product, str)
        and not PRODUCT_DIMENSIONS & set(dimension_names)
    ):
        dimension_names.append("produit")

    if metric == "ca_net" and (product or PRODUCT_DIMENSIONS & set(dimension_names)):
        metric = "mix_produit"

    metric = resolve_metric(metric)

    # Un filtre produit exige une métrique découpable par produit
    # (sinon : erreur « dimension 'product' non disponible »).
    if product:
        resolve_dimension("produit", metric)

    dimensions = [
        resolve_dimension(dimension_name, metric)
        for dimension_name in dimension_names
    ]

    # ---------------------------------------------------------
    # 4. Classement (« le canal qui dépense le plus »)
    # ---------------------------------------------------------

    comparison = None

    if dimensions:
        for direction, terms in COMPARISON_TERMS.items():
            if any(_contains(term, text) for term in terms):
                comparison = direction
                break

    # ---------------------------------------------------------
    # 5. Construction de l'intention
    # ---------------------------------------------------------

    return build_intent(
        question=question,
        metric=metric,
        dimensions=dimensions,
        channel=channel,
        comparison=comparison,
        product=product,
        platform=platform,
        other_metrics=other_metrics,
        **period,
    )


if __name__ == "__main__":
    questions = [
        "Quel est le CA net en juin 2026 ?",
        "Quel est le CA net par mois ?",
        "Quel est le chiffre d'affaires en mars 2026 ?",
        "Combien avons-nous dépensé sur Meta ?",
        "Quel est le spend TikTok ?",
        "Combien avons-nous dépensé sur Google en juin 2026 ?",
        "Quel est le montant dépensé par canal ?",
        "Quel est le spend par canal ?",
    ]

    for question in questions:
        print(f"\nQuestion : {question}")

        try:
            intent = parse_question(question)
            print(f"Intent : {intent}")

        except ValueError as exc:
            print(f"Erreur : {exc}")
