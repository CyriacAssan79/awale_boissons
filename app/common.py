"""Accès aux données et helpers partagés par toutes les pages du dashboard."""

from __future__ import annotations

import duckdb
import pandas as pd
import streamlit as st

from theme import month_label


DB_PATH = "data/awale.duckdb"


@st.cache_resource
def get_connection():
    return duckdb.connect(DB_PATH, read_only=True)


@st.cache_data(ttl=300)
def load_query(query: str) -> pd.DataFrame:
    con = get_connection()
    return con.execute(query).df()


@st.cache_data(ttl=300)
def table_exists(table_name: str) -> bool:
    con = get_connection()

    result = con.execute(
        """
        SELECT COUNT(*) > 0
        FROM information_schema.tables
        WHERE table_name = ?
        """,
        [table_name],
    ).fetchone()

    return bool(result[0])


def safe_query(query: str) -> pd.DataFrame | None:
    """Comme load_query, mais renvoie None si la table ou une colonne n'existe pas
    encore (base à reconstruire avec python run_pipeline.py) au lieu de planter."""
    try:
        return load_query(query)
    except duckdb.Error:
        return None


def money(value: float) -> str:
    if pd.isna(value):
        return "—"

    return f"{value:,.0f} FCFA".replace(",", " ")


def pct(value: float) -> str:
    if pd.isna(value):
        return "—"

    return f"{value * 100:.1f} %"


def integer(value: float) -> str:
    return f"{value:,.0f}".replace(",", " ")


def totals(df: pd.DataFrame, mapping: dict[str, str], label: str) -> pd.DataFrame:
    """Somme chaque colonne de `mapping` présente dans `df`, sous son libellé."""
    rows = [
        (name, df[column].sum())
        for column, name in mapping.items()
        if column in df.columns
    ]

    return pd.DataFrame(rows, columns=[label, "comments"])


def load_monthly() -> pd.DataFrame:
    return load_query(
        """
        SELECT *
        FROM mart_monthly_performance
        ORDER BY month
        """
    )


# ---------------------------------------------------------------------
# FILTRE DE PÉRIODE
# ---------------------------------------------------------------------

_MONTHS_KEY = "selected_months"
_MONTHS_WIDGET_KEY = "_selected_months_widget"


def _store_months() -> None:
    st.session_state[_MONTHS_KEY] = st.session_state[_MONTHS_WIDGET_KEY]


def period_filter() -> list:
    """Filtre de période dans la barre latérale, conservé d'une page à l'autre.

    Streamlit efface l'état d'un widget absent de la page affichée : la
    sélection est donc recopiée dans une clé de session indépendante.
    """
    months = list(load_monthly()["month"].dropna().sort_values().unique())

    if _MONTHS_KEY not in st.session_state:
        st.session_state[_MONTHS_KEY] = months

    st.session_state[_MONTHS_WIDGET_KEY] = [
        m for m in st.session_state[_MONTHS_KEY] if m in months
    ]

    st.sidebar.header("Filtres")

    st.sidebar.multiselect(
        "Période",
        options=months,
        format_func=month_label,
        key=_MONTHS_WIDGET_KEY,
        on_change=_store_months,
    )

    st.sidebar.caption(
        "Données observées uniquement. Le filtre s'applique aux ventes "
        "et aux commentaires clients."
    )

    # Sans sélection, tout le jeu de données est affiché (ventes comme social).
    return st.session_state[_MONTHS_WIDGET_KEY] or months
