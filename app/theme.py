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

/* ---- En-tête ---- */
[data-testid="stHeader"] {{
    background: {CREME};
    border-bottom: 1px solid {BORDER};
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
.section-title-row {{
    display: flex;
    align-items: center;
    gap: .5rem;
}}
.section-help {{
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.3rem;
    height: 1.3rem;
    border-radius: 50%;
    border: 1.5px solid {MUTED};
    color: {MUTED};
    font-size: .8rem;
    font-weight: 700;
    cursor: help;
    outline: none;
}}
.section-help:hover,
.section-help:focus {{
    border-color: {BISSAP};
    color: {BISSAP};
}}
.section-help-tip {{
    visibility: hidden;
    opacity: 0;
    position: absolute;
    top: calc(100% + .6rem);
    left: 0;
    z-index: 1000;
    width: min(28rem, 80vw);
    padding: .85rem 1rem;
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
    box-shadow: 0 8px 24px rgba(43, 29, 24, .12);
    color: {INK};
    font-size: .85rem;
    font-weight: 400;
    line-height: 1.45;
    text-align: left;
    transition: opacity .15s ease;
}}
.section-help:hover .section-help-tip,
.section-help:focus .section-help-tip {{
    visibility: visible;
    opacity: 1;
}}
.section-help-tip ul {{
    margin: 0;
    padding-left: 1.1rem;
}}
.section-help-tip li {{
    margin: 0 0 .35rem;
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

/* ---- Rapport mensuel ---- */
.report-head {{
    margin: 1.6rem 0 1rem;
}}
.report-eyebrow {{
    font-size: .74rem;
    font-weight: 700;
    letter-spacing: .16em;
    text-transform: uppercase;
    color: {BISSAP};
}}
.report-title {{
    font-size: 2rem;
    font-weight: 800;
    line-height: 1.15;
    color: {INK};
    margin-top: .2rem;
}}
.report-meta {{
    margin-top: .3rem;
    font-size: .85rem;
    color: {MUTED};
}}
[class*="st-key-card_report_"] {{
    padding: 1.1rem 1.5rem 1rem;
    height: 100%;
}}
[class*="st-key-card_report_"] p,
[class*="st-key-card_report_"] li {{
    font-size: .98rem;
    line-height: 1.65;
    color: {INK};
}}
[class*="st-key-card_report_"] li {{
    margin-bottom: .15rem;
}}
[class*="st-key-card_report_"] em {{
    color: {MUTED};
    font-size: .9rem;
}}
[class*="st-key-card_report_"] strong {{
    font-weight: 700;
}}
[class*="st-key-card_report_"] h3 {{
    font-size: 1rem;
    font-weight: 700;
    color: {INK};
    padding: .6rem 0 .1rem;
}}
.report-section-title {{
    display: flex;
    align-items: center;
    gap: .55rem;
    font-size: 1.15rem;
    font-weight: 800;
    color: {INK};
    margin: .1rem 0 .55rem;
}}
.report-section-title span {{
    font-size: 1.25rem;
}}
/* Synthèse et conclusion : mises en avant */
.st-key-card_report_synthese,
.st-key-card_report_conclusion {{
    background: linear-gradient(135deg, #FFFFFF 0%, {CREME} 100%);
    border-left: 5px solid {BISSAP} !important;
}}
.st-key-card_report_synthese p,
.st-key-card_report_conclusion p {{
    font-size: 1.08rem;
    line-height: 1.75;
}}
.st-key-card_report_attention {{
    border-top: 4px solid {TERRACOTTA} !important;
}}
.st-key-card_report_positifs {{
    border-top: 4px solid {GINGEMBRE} !important;
}}
[class*="st-key-card_report_"] table {{
    width: 100%;
    border-collapse: collapse;
    font-size: .9rem;
    margin: .4rem 0 .6rem;
}}
[class*="st-key-card_report_"] th {{
    background: {CREME};
    color: {MUTED};
    font-size: .74rem;
    font-weight: 700;
    letter-spacing: .04em;
    text-transform: uppercase;
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: .55rem .7rem;
}}
[class*="st-key-card_report_"] td {{
    border: none;
    border-bottom: 1px solid {GRID};
    padding: .55rem .7rem;
    color: {INK};
}}
[class*="st-key-card_report_"] tr:last-child td {{
    border-bottom: none;
}}

/* ---- Conversation (Ask the Data) ---- */
[class*="st-key-chat_user_"] [data-testid="stChatMessage"] {{
    flex-direction: row-reverse;
    width: fit-content;
    max-width: 75%;
    margin-left: auto;
    background: rgba(156, 31, 63, .08);
    border-radius: 16px 16px 4px 16px;
}}
[class*="st-key-chat_user_"] [data-testid="stChatMessage"] p {{
    text-align: right;
}}
[class*="st-key-chat_assistant_"] [data-testid="stChatMessage"] {{
    max-width: 85%;
    margin-right: auto;
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 16px 16px 16px 4px;
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
.sidebar-nav-section {{
    margin: 1rem 0 .25rem;
    font-size: .72rem;
    font-weight: 700;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: {MUTED};
}}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {{
    border-radius: 10px;
}}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"] {{
    background: rgba(156, 31, 63, .1);
}}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"][aria-current="page"] span {{
    color: {BISSAP};
    font-weight: 700;
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


def section(number: int, title: str, subtitle: str, help: str = "") -> None:
    """`help` : contenu HTML d'une infobulle affichée au survol d'un « ? » à côté du titre."""
    help_html = (
        f'<span class="section-help" tabindex="0" aria-label="Aide">?'
        f'<span class="section-help-tip" role="tooltip">{help}</span></span>'
        if help
        else ""
    )

    st.markdown(
        f"""
        <div class="section-head">
            <div class="section-num">{number}</div>
            <div>
                <div class="section-title-row"><span class="section-title">{title}</span>{help_html}</div>
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


def sidebar_nav_section(title: str) -> None:
    st.sidebar.markdown(f'<div class="sidebar-nav-section">{title}</div>', unsafe_allow_html=True)


def footer(text: str) -> None:
    st.markdown(f'<div class="footer">{text}</div>', unsafe_allow_html=True)
