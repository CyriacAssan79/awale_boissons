from __future__ import annotations

import sys
from pathlib import Path

import streamlit as st

from theme import apply_theme, footer, sidebar_active_link, sidebar_brand, sidebar_nav_section


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

sidebar_brand("Awalé Boissons", "Marketing Decision Cockpit")


# Pages regroupées par rubrique dans la barre latérale.
NAVIGATION = {
    "Tableau de bord": [
        st.Page("views/overview.py", title="Vue d'ensemble", icon=":material/dashboard:", default=True),
        st.Page("views/marketing.py", url_path="marketing", title="Marketing", icon=":material/payments:"),
        st.Page("views/sales.py", url_path="ventes", title="Ventes", icon=":material/trending_up:"),
        st.Page("views/customers.py", url_path="voix-client", title="Voix client", icon=":material/forum:"),
    ],
    "Décision": [
        st.Page("views/recommendation.py", url_path="recommandation", title="Recommandation", icon=":material/lightbulb:"),
    ],
    "Intelligence artificielle": [
        st.Page("views/report.py", url_path="rapport", title="Rapport IA", icon=":material/auto_awesome:"),
        st.Page("views/ask_data.py", url_path="ask-data", title="Demander à l'IA", icon=":material/smart_toy:"),
    ],
}

# Menu natif masqué : les liens sont placés sous le logo et au-dessus des
# filtres, que la navigation native afficherait sinon en tête de la barre.
page = st.navigation(NAVIGATION, position="hidden")
sidebar_active_link(page.url_path)

for group, group_pages in NAVIGATION.items():
    sidebar_nav_section(group)

    for nav_page in group_pages:
        st.sidebar.page_link(nav_page)

page.run()


footer(
    "Awalé Boissons — Challenge Kômian | "
    "Pipeline DuckDB + dbt | Dashboard décisionnel"
)
