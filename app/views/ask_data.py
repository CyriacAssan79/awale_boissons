import pandas as pd
import plotly.express as px
import streamlit as st

from ai.ask_data.answer import format_answer
from ai.ask_data.question_parser import parse_question
from ai.ask_data.sql_builder import build_sql
from common import safe_query
from theme import BISSAP, month_label, section, show_chart


HISTORY_KEY = "ask_data_history"

# Infobulle du titre : une seule ligne HTML, une ligne vide casserait le rendu.
HELP = (
    "<ul>"
    "<li><b>Métriques</b> : chiffre d'affaires net, dépenses marketing, mix produit.</li>"
    "<li><b>Découpages</b> : par mois, par canal, par produit, par format (selon la métrique).</li>"
    "<li><b>Filtres</b> : un mois précis (« en juin 2026 »), une période relative "
    "(« ces 3 derniers mois »), un canal (Meta, TikTok, Google, Radio…).</li>"
    "<li><b>Hors périmètre</b> : les questions causales (« quel canal a causé… »), "
    "les prévisions et les métriques non définies (ROI, coût par litre…) "
    "sont refusées plutôt que d'inventer une réponse.</li>"
    "<li><b>Toutes les réponses sont calculées à partir des données réelles</b>, "
    "selon des définitions de métriques validées.</li>"
    "</ul>"
)

EXAMPLES = [
    "Quel est le CA net en juin 2026 ?",
    "Quel est le CA net par mois ?",
    "Combien avons-nous dépensé sur Meta en juin 2026 ?",
    "Quel est le spend par canal ?",
    "Donne moi les dépenses publicitaires par canal ces 3 derniers mois",
    "Quel est le mix produit par mois et par produit ?",
]


def answer_question(question: str) -> dict:
    """Exécute le pipeline Ask the Data et garde les étapes pour l'affichage."""
    try:
        intent = parse_question(question)
        sql = build_sql(intent)
    except ValueError as exc:
        return {"question": question, "error": str(exc)}

    # Requête exécutée sur la connexion partagée du dashboard (mise en cache).
    result = safe_query(sql)

    if result is None:
        return {
            "question": question,
            "error": "Les données nécessaires ne sont pas disponibles. "
            "Relancez le pipeline (python run_pipeline.py).",
        }

    return {
        "question": question,
        "answer": format_answer(intent, result),
        "intent": intent,
        "result": result,
    }


def result_chart(intent, result: pd.DataFrame) -> None:
    """Graphique simple lorsque la réponse est découpée par une ou deux dimensions."""
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
    show_chart(fig, height=320)


def show_entry(entry: dict) -> None:
    with st.chat_message("user"):
        st.markdown(entry["question"])

    with st.chat_message("assistant"):
        if "error" in entry:
            st.warning(entry["error"])
        else:
            st.markdown(entry["answer"].replace("\n", "  \n"))
            result_chart(entry["intent"], entry["result"])


section(
    6,
    "Ask the Data",
    "Posez une question sur les ventes ou les dépenses marketing : "
    "la réponse est calculée directement à partir des données.",
    help=HELP,
)

history = st.session_state.setdefault(HISTORY_KEY, [])


# ---------------------------------------------------------------------
# EXEMPLES
# ---------------------------------------------------------------------

st.caption("Exemples de questions")

example_cols = st.columns(3)
clicked = None

for i, example in enumerate(EXAMPLES):
    with example_cols[i % 3]:
        if st.button(example, key=f"ask_example_{i}", width="stretch"):
            clicked = example


# ---------------------------------------------------------------------
# CONVERSATION
# ---------------------------------------------------------------------

question = st.chat_input("Ex. : Quel est le spend par canal ?") or clicked

if question:
    history.append(answer_question(question))

for entry in history:
    show_entry(entry)

if history and st.button("Effacer la conversation", icon=":material/delete:"):
    st.session_state[HISTORY_KEY] = []
    st.rerun()
