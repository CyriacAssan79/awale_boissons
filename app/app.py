from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

from theme import apply_theme, footer, sidebar_brand


# Le rapport IA importe le package `ai`, situé à la racine du projet.
ROOT_DIR = Path(__file__).resolve().parent.parent

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


st.set_page_config(
    page_title="Awalé Boissons — Marketing Decision Cockpit",
    page_icon="🥤",
    layout="wide",
)

apply_theme()

sidebar_brand("Awalé Boissons", "Marketing Decision Cockpit", "🥤")


pages = [
    st.Page("views/overview.py", title="Vue d'ensemble", icon=":material/dashboard:", default=True),
    st.Page("views/marketing.py", url_path="marketing", title="Marketing", icon=":material/payments:"),
    st.Page("views/sales.py", url_path="ventes", title="Ventes", icon=":material/trending_up:"),
    st.Page("views/customers.py", url_path="voix-client", title="Voix client", icon=":material/forum:"),
    st.Page("views/recommendation.py", url_path="recommandation", title="Recommandation", icon=":material/lightbulb:"),
    st.Page("views/report.py", url_path="rapport", title="Rapport IA", icon=":material/auto_awesome:"),
]

page = st.navigation(pages, position="top")
page.run()


footer(
    "Awalé Boissons — Challenge Kômian | "
    "Pipeline DuckDB + dbt | Dashboard décisionnel"
)
