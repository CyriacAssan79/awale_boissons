"""Identité visuelle du dashboard : palette, CSS, template Plotly, composants."""

from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st


# ---------------------------------------------------------------------
# PALETTE — boissons locales (bissap, bouye, gingembre)
# ---------------------------------------------------------------------

BISSAP = "#9C1F3F"
BISSAP_DARK = "#5E1226"
BOUYE = "#D4922A"
GINGEMBRE = "#4F7A3C"
LAGON = "#2F6F7E"
PRUNE = "#6B3F69"
SABLE = "#B8A88F"
TERRACOTTA = "#C2492F"

CREME = "#FBF6EF"
SURFACE = "#FFFFFF"
BORDER = "#EADFD0"
GRID = "#F0E7DA"
INK = "#2B1D18"
MUTED = "#7A6A60"

COLORWAY = [BISSAP, BOUYE, GINGEMBRE, LAGON, PRUNE, SABLE]

PRODUCT_COLORS = {
    "bissap": BISSAP,
    "gingembre": GINGEMBRE,
    "bouye": BOUYE,
}

SENTIMENT_COLORS = {
    "Positif": GINGEMBRE,
    "Neutre": SABLE,
    "Négatif": TERRACOTTA,
}

FONT = "Source Sans Pro, Segoe UI, Helvetica, Arial, sans-serif"

FR_MONTHS = [
    "janv.", "févr.", "mars", "avr.", "mai", "juin",
    "juil.", "août", "sept.", "oct.", "nov.", "déc.",
]


def month_label(value) -> str:
    ts = pd.Timestamp(value)
    return f"{FR_MONTHS[ts.month - 1]} {ts.year}"


# ---------------------------------------------------------------------
# PLOTLY
# ---------------------------------------------------------------------

def _register_plotly_template() -> None:
    axis_common = dict(
        automargin=True,
        linecolor=BORDER,
        tickcolor=BORDER,
        tickfont=dict(color=MUTED, size=12),
        title=dict(font=dict(color=MUTED, size=12)),
    )

    pio.templates["awale"] = go.layout.Template(
        layout=dict(
            font=dict(family=FONT, size=13, color=INK),
            colorway=COLORWAY,
            paper_bgcolor=SURFACE,
            plot_bgcolor=SURFACE,
            separators=", ",
            title=dict(
                font=dict(size=16, color=INK),
                x=0,
                xanchor="left",
                y=0.95,
            ),
            margin=dict(l=8, r=8, t=56, b=8),
            xaxis=dict(showgrid=False, zeroline=False, **axis_common),
            yaxis=dict(
                showgrid=True,
                gridcolor=GRID,
                zeroline=False,
                **axis_common,
            ),
            hoverlabel=dict(
                bgcolor=SURFACE,
                bordercolor=BORDER,
                font=dict(family=FONT, size=13, color=INK),
            ),
            legend=dict(font=dict(color=MUTED)),
        )
    )
    pio.templates.default = "awale"


_register_plotly_template()


def show_chart(fig: go.Figure, height: int = 340) -> None:
    fig.update_layout(height=height)
    st.plotly_chart(
        fig,
        width="stretch",
        theme=None,
        config={"displayModeBar": False},
    )


# ---------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------

_CSS = f"""
<style>
.block-container {{
    max-width: 1280px;
    padding-top: 2.2rem;
    padding-bottom: 4rem;
}}

[data-testid="stHeader"] {{
    background: transparent;
}}

/* ---- Bandeau ---- */
.hero {{
    background: linear-gradient(120deg, {BISSAP_DARK} 0%, {BISSAP} 55%, {TERRACOTTA} 100%);
    border-radius: 22px;
    padding: 2rem 2.4rem 1.8rem;
    color: #fff;
    box-shadow: 0 12px 32px rgba(94, 18, 38, .22);
}}
.hero-eyebrow {{
    font-size: .74rem;
    font-weight: 700;
    letter-spacing: .16em;
    text-transform: uppercase;
    opacity: .78;
}}
.hero-title {{
    font-size: 2.3rem;
    font-weight: 800;
    line-height: 1.15;
    margin: .3rem 0 .55rem;
    color: #fff;
}}
.hero-text {{
    max-width: 62rem;
    margin: 0;
    font-size: .98rem;
    line-height: 1.5;
    color: rgba(255, 255, 255, .88);
}}
.hero-pills {{
    display: flex;
    flex-wrap: wrap;
    gap: .5rem;
    margin-top: 1.1rem;
}}
.hero-pills span {{
    background: rgba(255, 255, 255, .16);
    border: 1px solid rgba(255, 255, 255, .28);
    border-radius: 999px;
    padding: .22rem .8rem;
    font-size: .78rem;
    font-weight: 600;
}}

/* ---- En-têtes de section ---- */
.section-head {{
    display: flex;
    align-items: center;
    gap: .95rem;
    margin: 2.6rem 0 1.1rem;
}}
.section-num {{
    flex: 0 0 auto;
    width: 2.5rem;
    height: 2.5rem;
    border-radius: 12px;
    background: {BISSAP};
    color: #fff;
    font-weight: 800;
    font-size: 1.1rem;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: 0 4px 10px rgba(156, 31, 63, .25);
}}
.section-title {{
    font-size: 1.5rem;
    font-weight: 800;
    line-height: 1.2;
    color: {INK};
}}
.section-sub {{
    margin-top: .1rem;
    font-size: .9rem;
    color: {MUTED};
}}

/* ---- Cartes (conteneurs avec key="card_*") ---- */
[class*="st-key-card_"] {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 18px;
    padding: .35rem .5rem;
    box-shadow: 0 1px 3px rgba(60, 30, 20, .05);
}}
/* Streamlit impose les couleurs du thème sur le papier et la zone de tracé Plotly. */
[data-testid="stPlotlyChart"] .main-svg {{
    background: transparent !important;
}}
[data-testid="stPlotlyChart"] .main-svg .bg {{
    fill: transparent !important;
}}
.subsection {{
    display: flex;
    align-items: baseline;
    gap: .7rem;
    margin: 2rem 0 .8rem;
    padding-bottom: .5rem;
    border-bottom: 1px solid {BORDER};
}}
.subsection-title {{
    font-size: 1.1rem;
    font-weight: 800;
    color: {INK};
}}
.subsection-sub {{
    font-size: .85rem;
    color: {MUTED};
}}
.card-title {{
    font-size: .8rem;
    font-weight: 700;
    letter-spacing: .06em;
    text-transform: uppercase;
    color: {MUTED};
    margin: .35rem 0 .3rem;
}}

/* ---- KPI ---- */
[data-testid="stMetric"] {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-left: 5px solid {BISSAP};
    border-radius: 16px;
    padding: 1rem 1.2rem;
    box-shadow: 0 1px 3px rgba(60, 30, 20, .05);
}}
[data-testid="stMetricLabel"] * {{
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
}}
[data-testid="stMetricLabel"] p {{
    font-size: .78rem;
    font-weight: 700;
    letter-spacing: .05em;
    text-transform: uppercase;
    color: {MUTED};
}}
[data-testid="stMetricValue"] {{
    font-weight: 800;
    color: {INK};
}}
[data-testid="stMetricValue"] * {{
    font-size: 1.55rem;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
}}

/* ---- Tableaux statiques (st.table) ---- */
[data-testid="stTable"] table {{
    border: none;
    font-size: .88rem;
}}
[data-testid="stTable"] thead th,
[data-testid="stTable"] thead th * {{
    background: {CREME};
    color: {MUTED};
    font-weight: 700;
    font-size: .74rem !important;
    letter-spacing: .04em;
    text-transform: uppercase;
    border-color: {BORDER};
}}
[data-testid="stTable"] td {{
    vertical-align: top;
    border-color: {BORDER};
    padding: .65rem .75rem;
}}
[data-testid="stTable"] tbody th {{
    vertical-align: top;
    padding: .65rem .75rem;
    color: {INK};
    font-size: .88rem;
    text-transform: none;
    letter-spacing: 0;
}}

/* ---- Alertes ---- */
[data-testid="stAlert"] {{
    border-radius: 14px;
}}

/* ---- Barre latérale ---- */
.sidebar-brand {{
    display: flex;
    align-items: center;
    gap: .7rem;
    padding: .2rem 0 1rem;
    margin-bottom: .6rem;
    border-bottom: 1px solid {BORDER};
}}
.sidebar-logo {{
    width: 2.6rem;
    height: 2.6rem;
    border-radius: 14px;
    background: {BISSAP};
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.4rem;
}}
.sidebar-name {{
    font-weight: 800;
    line-height: 1.15;
    color: {INK};
}}
.sidebar-tag {{
    font-size: .78rem;
    color: {MUTED};
}}

/* ---- Pied de page ---- */
.footer {{
    margin-top: 3.2rem;
    padding-top: 1.4rem;
    border-top: 1px solid {BORDER};
    text-align: center;
    font-size: .82rem;
    color: {MUTED};
}}
</style>
"""


def apply_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------
# COMPOSANTS
# ---------------------------------------------------------------------

def hero(eyebrow: str, title: str, text: str, pills: list[str]) -> None:
    pills_html = "".join(f"<span>{p}</span>" for p in pills)

    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-eyebrow">{eyebrow}</div>
            <div class="hero-title">{title}</div>
            <p class="hero-text">{text}</p>
            <div class="hero-pills">{pills_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(number: int, title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="section-head">
            <div class="section-num">{number}</div>
            <div>
                <div class="section-title">{title}</div>
                <div class="section-sub">{subtitle}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def subsection(title: str, subtitle: str = "") -> None:
    sub = f'<span class="subsection-sub">{subtitle}</span>' if subtitle else ""
    st.markdown(
        f'<div class="subsection"><span class="subsection-title">{title}</span>{sub}</div>',
        unsafe_allow_html=True,
    )


def card(key: str):
    return st.container(border=False, key=f"card_{key}")


def card_title(text: str) -> None:
    st.markdown(f'<div class="card-title">{text}</div>', unsafe_allow_html=True)


def sidebar_brand(name: str, tagline: str, icon: str) -> None:
    st.sidebar.markdown(
        f"""
        <div class="sidebar-brand">
            <div class="sidebar-logo">{icon}</div>
            <div>
                <div class="sidebar-name">{name}</div>
                <div class="sidebar-tag">{tagline}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def footer(text: str) -> None:
    st.markdown(f'<div class="footer">{text}</div>', unsafe_allow_html=True)
