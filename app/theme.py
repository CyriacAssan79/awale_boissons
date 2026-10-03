"""Identité visuelle du dashboard : palette, CSS, template Plotly, composants.

Design system « Ivorian Terroir & Analytic Rigor » (maquettes Google Stitch) :
fond écru, cartes blanches à filet fin, bissap en couleur principale,
Epilogue (titres), Hanken Grotesk (texte), JetBrains Mono (chiffres).
"""

from __future__ import annotations

from html import escape

import pandas as pd
import plotly.graph_objects as go
import plotly.io as pio
import streamlit as st


# ---------------------------------------------------------------------
# PALETTE — boissons locales (bissap, gingembre, bouye)
# ---------------------------------------------------------------------

BISSAP = "#7A123A"
BISSAP_DARK = "#570025"
BISSAP_TINT = "#F7E8EE"
GINGEMBRE = "#D97706"
GINGEMBRE_DARK = "#B45309"
BOUYE = "#8C7A5B"
TERRACOTTA = "#FD8A42"
MAUVE = "#897175"
ROSE = "#FFB1C3"

CREME = "#FDFBF7"
SURFACE = "#FFFFFF"
SURFACE_MUTED = "#F8F6F0"
BORDER = "#E7E2D6"
GRID = "#F0EDE4"
INK = "#0F172A"
INK_2 = "#334155"
MUTED = "#64748B"

SUCCESS, SUCCESS_BG = "#15803D", "#DCFCE7"
WARNING, WARNING_BG = "#B45309", "#FEF3C7"
ERROR, ERROR_BG = "#DC2626", "#FEE2E2"
INFO, INFO_BG = "#1E40AF", "#DBEAFE"

COLORWAY = [BISSAP, GINGEMBRE, BOUYE, TERRACOTTA, MAUVE, ROSE]

PRODUCT_COLORS = {
    "bissap": BISSAP,
    "gingembre": GINGEMBRE,
    "bouye": BOUYE,
}

CHANNEL_COLORS = {
    "Meta": BISSAP,
    "TikTok": TERRACOTTA,
    "Radio": MAUVE,
    "Google": BISSAP_DARK,
    "Influenceurs": "#FDBA8C",
    "Activation terrain": BOUYE,
}

SENTIMENT_COLORS = {
    "Positif": SUCCESS,
    "Neutre": "#94A3B8",
    "Négatif": ERROR,
}

FONT_BODY = "'Hanken Grotesk', 'Segoe UI', Helvetica, Arial, sans-serif"
FONT_HEAD = "'Epilogue', 'Hanken Grotesk', 'Segoe UI', sans-serif"
FONT_MONO = "'JetBrains Mono', Consolas, 'Courier New', monospace"

FR_MONTHS = [
    "janv.", "févr.", "mars", "avr.", "mai", "juin",
    "juil.", "août", "sept.", "oct.", "nov.", "déc.",
]

# Logo (graines d'awalé et goutte) tiré des maquettes.
LOGO_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120" aria-hidden="true">
  <defs>
    <linearGradient id="awaleGlow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#931b46"/><stop offset="100%" stop-color="#5c0d29"/>
    </linearGradient>
    <linearGradient id="goldGlow" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#f59e0b"/><stop offset="100%" stop-color="#b45309"/>
    </linearGradient>
  </defs>
  <rect width="120" height="120" rx="28" fill="url(#awaleGlow)"/>
  <circle cx="42" cy="46" r="14" fill="#FDFBF7" opacity="0.95"/>
  <circle cx="78" cy="46" r="14" fill="#FDFBF7" opacity="0.95"/>
  <circle cx="42" cy="76" r="14" fill="url(#goldGlow)"/>
  <circle cx="78" cy="76" r="14" fill="url(#goldGlow)"/>
  <path d="M60 32 C60 32, 69 48, 69 57 C69 62, 65 66, 60 66 C55 66, 51 62, 51 57 C51 48, 60 32, 60 32 Z" fill="#FDFBF7"/>
  <circle cx="60" cy="85" r="5" fill="#FDFBF7" opacity="0.8"/>
</svg>
"""


def month_label(value) -> str:
    ts = pd.Timestamp(value)
    return f"{FR_MONTHS[ts.month - 1]} {ts.year}"


def icon(name: str, cls: str = "") -> str:
    """Icône Material Symbols (HTML), pour les blocs écrits en markdown."""
    return f'<span class="material-symbols-outlined {cls}" aria-hidden="true">{name}</span>'


# ---------------------------------------------------------------------
# PLOTLY
# ---------------------------------------------------------------------

def _register_plotly_template() -> None:
    axis_common = dict(
        automargin=True,
        linecolor=BORDER,
        tickcolor=BORDER,
        tickfont=dict(family=FONT_MONO, color=MUTED, size=11),
        title=dict(font=dict(color=MUTED, size=12)),
    )

    pio.templates["awale"] = go.layout.Template(
        layout=dict(
            font=dict(family=FONT_BODY, size=13, color=INK_2),
            colorway=COLORWAY,
            paper_bgcolor=SURFACE,
            plot_bgcolor=SURFACE,
            separators=", ",
            title=dict(
                font=dict(family=FONT_HEAD, size=17, color=INK),
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
                font=dict(family=FONT_BODY, size=13, color=INK),
            ),
            legend=dict(font=dict(color=INK_2)),
            bargap=0.35,
        )
    )
    pio.templates.default = "awale"


_register_plotly_template()


def show_chart(fig: go.Figure, height: int = 340, key: str | None = None) -> None:
    fig.update_layout(height=height)
    st.plotly_chart(
        fig,
        width="stretch",
        theme=None,
        config={"displayModeBar": False},
        key=key,
    )


# ---------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------

_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Epilogue:wght@600;700&family=Hanken+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@500;600&display=swap');
@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,300..600,0..1,0&display=block');

.material-symbols-outlined {{
    font-family: 'Material Symbols Outlined';
    font-weight: normal;
    font-style: normal;
    font-size: 1.25rem;
    line-height: 1;
    letter-spacing: normal;
    text-transform: none;
    display: inline-block;
    white-space: nowrap;
    direction: ltr;
    -webkit-font-smoothing: antialiased;
    font-variation-settings: 'FILL' 0, 'wght' 400, 'GRAD' 0, 'opsz' 24;
}}

/* ---- Canevas (desktop) ---- */
.block-container {{
    max-width: 1440px;
    padding: 2rem 2.5rem 4rem;
}}
[data-testid="stHeader"] {{
    background: {CREME};
    border-bottom: 1px solid {BORDER};
}}
h1, h2, h3 {{
    font-family: {FONT_HEAD};
    letter-spacing: -0.015em;
}}

/* ---- Bandeau d'accueil ---- */
.hero {{
    background: linear-gradient(125deg, {BISSAP} 0%, {BISSAP_DARK} 100%);
    border-radius: 8px;
    padding: 2.2rem 2.6rem 2rem;
    color: #fff;
}}
.hero-top {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: 1rem;
}}
.hero-eyebrow {{
    font-family: {FONT_MONO};
    font-size: .74rem;
    font-weight: 600;
    letter-spacing: .14em;
    text-transform: uppercase;
    color: rgba(255, 255, 255, .72);
}}
.hero-badge {{
    font-family: {FONT_MONO};
    font-size: .74rem;
    font-weight: 600;
    padding: .25rem .75rem;
    border-radius: 999px;
    background: rgba(255, 255, 255, .12);
    border: 1px solid rgba(255, 255, 255, .22);
    color: #fff;
}}
.hero-badge::before {{
    content: "";
    display: inline-block;
    width: .45rem;
    height: .45rem;
    margin-right: .45rem;
    border-radius: 50%;
    background: #79DB8D;
    vertical-align: middle;
}}
.hero-title {{
    font-family: {FONT_HEAD};
    font-size: 2.75rem;
    font-weight: 700;
    line-height: 1.15;
    letter-spacing: -0.02em;
    margin: .5rem 0 .7rem;
    color: #fff;
}}
.hero-text {{
    max-width: 60rem;
    margin: 0;
    font-size: 1.02rem;
    line-height: 1.6;
    color: rgba(255, 255, 255, .86);
}}
.hero-pills {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    gap: .75rem;
    margin-top: 1.6rem;
}}
.hero-pill {{
    display: flex;
    align-items: center;
    gap: .75rem;
    padding: .8rem 1rem;
    border-radius: 6px;
    background: rgba(255, 255, 255, .08);
    border: 1px solid rgba(255, 255, 255, .14);
}}
.hero-pill .material-symbols-outlined {{
    color: #79DB8D;
}}
.hero-pill-title {{
    font-weight: 600;
    font-size: .95rem;
}}
.hero-pill-sub {{
    font-family: {FONT_MONO};
    font-size: .72rem;
    color: rgba(255, 255, 255, .68);
}}

/* ---- En-têtes de section ---- */
.section-head {{
    display: flex;
    align-items: flex-start;
    gap: 1rem;
    margin: 1.2rem 0 1.4rem;
    padding-bottom: 1.1rem;
    border-bottom: 1px solid {BORDER};
}}
.section-num {{
    flex: 0 0 auto;
    margin-top: .35rem;
    padding: .2rem .55rem;
    border-radius: 4px;
    background: {BISSAP};
    color: #fff;
    font-family: {FONT_MONO};
    font-weight: 600;
    font-size: .74rem;
    letter-spacing: .08em;
}}
.section-title {{
    font-family: {FONT_HEAD};
    font-size: 1.85rem;
    font-weight: 700;
    line-height: 1.2;
    letter-spacing: -0.02em;
    color: {INK};
}}
.section-sub {{
    margin-top: .3rem;
    font-size: 1rem;
    color: {INK_2};
}}
.section-title-row {{
    display: flex;
    align-items: center;
    gap: .6rem;
}}
.section-help {{
    position: relative;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 1.6rem;
    height: 1.6rem;
    border-radius: 50%;
    background: {SURFACE_MUTED};
    border: 1px solid {BORDER};
    color: {MUTED};
    cursor: help;
    outline: none;
}}
.section-help .material-symbols-outlined {{
    font-size: 1.05rem;
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
    width: min(30rem, 80vw);
    padding: .9rem 1.1rem;
    background: {SURFACE};
    border: 1px solid #D5CEC2;
    border-radius: 8px;
    box-shadow: 0 4px 16px -2px rgba(122, 18, 58, .05), 0 2px 6px -1px rgba(15, 23, 42, .04);
    color: {INK};
    font-family: {FONT_BODY};
    font-size: .88rem;
    font-weight: 400;
    line-height: 1.5;
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
    border-radius: 8px;
    padding: 1rem 1.25rem;
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
    gap: .9rem;
    margin: 2.4rem 0 1rem;
    padding-bottom: .6rem;
    border-bottom: 1px solid {BORDER};
}}
.subsection-title {{
    font-family: {FONT_HEAD};
    font-size: 1.35rem;
    font-weight: 600;
    color: {INK};
}}
.subsection-sub {{
    font-size: .9rem;
    color: {MUTED};
}}
.card-title {{
    display: flex;
    align-items: center;
    gap: .55rem;
    font-family: {FONT_HEAD};
    font-size: 1.1rem;
    font-weight: 600;
    color: {INK};
    margin: .1rem 0 .7rem;
}}
.card-title::before {{
    content: "";
    width: .5rem;
    height: .5rem;
    border-radius: 50%;
    background: {BISSAP};
}}
.card-title-tag {{
    margin-left: auto;
    font-family: {FONT_MONO};
    font-size: .7rem;
    font-weight: 500;
    color: {MUTED};
    background: {SURFACE_MUTED};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: .15rem .5rem;
}}

/* ---- KPI ---- */
[data-testid="stMetric"] {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 1.1rem 1.25rem;
    height: 100%;
}}
[data-testid="stMetricLabel"] * {{
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
}}
[data-testid="stMetricLabel"] p {{
    font-family: {FONT_MONO};
    font-size: .72rem;
    font-weight: 600;
    letter-spacing: .06em;
    text-transform: uppercase;
    color: {MUTED};
}}
[data-testid="stMetricValue"] {{
    font-family: {FONT_MONO};
    font-weight: 600;
    color: {BISSAP};
    font-variant-numeric: tabular-nums;
}}
[data-testid="stMetricValue"] * {{
    font-size: 1.4rem;
    letter-spacing: -0.02em;
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
}}

/* ---- Bandeaux d'alerte : filet de 4 px à gauche ---- */
[data-testid="stAlertContainer"] {{
    border-radius: 6px;
    border-left: 4px solid {INFO};
    background: {INFO_BG};
    color: {INFO};
}}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentWarning"]) {{
    border-left-color: {WARNING};
    background: {WARNING_BG};
}}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentSuccess"]) {{
    border-left-color: {SUCCESS};
    background: {SUCCESS_BG};
}}
[data-testid="stAlertContainer"]:has([data-testid="stAlertContentError"]) {{
    border-left-color: {ERROR};
    background: {ERROR_BG};
}}
.banner {{
    display: flex;
    gap: .9rem;
    align-items: flex-start;
    padding: 1rem 1.2rem;
    border-radius: 6px;
    border-left: 4px solid;
    margin: .2rem 0 1rem;
}}
.banner-title {{
    font-weight: 600;
    font-size: 1rem;
    margin-bottom: .2rem;
}}
.banner-text {{
    font-size: .92rem;
    line-height: 1.5;
    color: {INK_2};
}}
.banner-tag {{
    margin-left: auto;
    flex: 0 0 auto;
    font-family: {FONT_MONO};
    font-size: .72rem;
    font-weight: 600;
    padding: .25rem .6rem;
    border-radius: 4px;
    background: {SURFACE};
}}
.banner-warning {{ background: {WARNING_BG}; border-color: {WARNING}; color: {WARNING}; }}
.banner-info {{ background: {INFO_BG}; border-color: {INFO}; color: {INFO}; }}
.banner-success {{ background: {SUCCESS_BG}; border-color: {SUCCESS}; color: {SUCCESS}; }}
.banner-error {{ background: {ERROR_BG}; border-color: {ERROR}; color: {ERROR}; }}

/* ---- Barres par catégorie (bar_list) ---- */
.bar-row {{
    padding: .7rem 0;
    border-bottom: 1px solid {GRID};
}}
.bar-row:last-child {{
    border-bottom: none;
}}
.bar-head {{
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    gap: 1rem;
    margin-bottom: .45rem;
}}
.bar-label {{
    font-weight: 500;
    color: {INK};
}}
.bar-value {{
    font-family: {FONT_MONO};
    font-weight: 600;
    font-size: 1.05rem;
    color: {INK};
    font-variant-numeric: tabular-nums;
}}
.bar-track {{
    height: 8px;
    border-radius: 999px;
    background: {GRID};
    overflow: hidden;
}}
.bar-fill {{
    height: 100%;
    border-radius: 999px;
}}
.bar-foot {{
    display: flex;
    justify-content: space-between;
    margin-top: .35rem;
    font-family: {FONT_MONO};
    font-size: .74rem;
    color: {MUTED};
}}

/* ---- Cartes de navigation (question métier → page) ---- */
[class*="st-key-qcard_"] {{
    position: relative;
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 1rem 1.2rem;
    gap: .2rem;
    transition: border-color .15s ease, background .15s ease;
}}
[class*="st-key-qcard_"]:hover {{
    border-color: {BISSAP};
    background: #FFFDFB;
}}
[class*="st-key-qcard_"] [data-testid="stElementContainer"],
[class*="st-key-qcard_"] [data-testid="stPageLink"],
[class*="st-key-qcard_"] [data-testid="stPageLink"] > div {{
    position: static;
}}
[class*="st-key-qcard_"] [data-testid="stPageLink-NavLink"] {{
    padding: 0;
    background: transparent !important;
}}
[class*="st-key-qcard_"] [data-testid="stPageLink-NavLink"]::after {{
    content: "";
    position: absolute;
    inset: 0;
    z-index: 1;
}}
[class*="st-key-qcard_"] [data-testid="stPageLink-NavLink"] p {{
    font-family: {FONT_HEAD};
    font-size: 1.08rem;
    font-weight: 600;
    color: {INK};
}}
[class*="st-key-qcard_"] [data-testid="stPageLink-NavLink"] span[data-testid="stIconMaterial"] {{
    color: {BISSAP};
}}
.qcard-tag {{
    display: inline-block;
    font-family: {FONT_MONO};
    font-size: .7rem;
    font-weight: 600;
    color: {BISSAP};
    background: {BISSAP_TINT};
    border-radius: 4px;
    padding: .1rem .45rem;
    margin-bottom: .3rem;
}}
.qcard-desc {{
    font-size: .9rem;
    line-height: 1.45;
    color: {MUTED};
}}
.st-key-qcard_ask {{
    background: {SURFACE_MUTED};
    border-left: 4px solid {BISSAP};
}}

/* ---- Tableaux statiques (st.table) ---- */
[data-testid="stTable"] table {{
    border: none;
    font-size: .9rem;
}}
[data-testid="stTable"] thead th,
[data-testid="stTable"] thead th * {{
    background: {SURFACE_MUTED};
    color: {MUTED};
    font-family: {FONT_MONO};
    font-weight: 600;
    font-size: .7rem !important;
    letter-spacing: .05em;
    text-transform: uppercase;
    border-color: {GRID};
}}
[data-testid="stTable"] td {{
    vertical-align: top;
    border-color: {GRID};
    padding: .7rem .8rem;
    color: {INK_2};
}}
[data-testid="stTable"] tbody th {{
    vertical-align: top;
    padding: .7rem .8rem;
    color: {INK};
    font-size: .9rem;
    font-weight: 600;
    text-transform: none;
    letter-spacing: 0;
    border-color: {GRID};
}}

/* ---- Boutons, interrupteurs, champs ---- */
[data-testid="stBaseButton-primary"] {{
    background: {BISSAP};
    border-color: {BISSAP};
    border-radius: 4px;
    font-weight: 500;
}}
[data-testid="stBaseButton-primary"]:hover {{
    background: #630E2F;
    border-color: #630E2F;
}}
[data-testid="stBaseButton-secondary"] {{
    border-radius: 4px;
    border-color: {BORDER};
    background: {SURFACE};
    color: {INK_2};
    text-align: left;
}}
[data-testid="stBaseButton-secondary"]:hover {{
    border-color: {BISSAP};
    color: {BISSAP};
}}
[data-testid="stDownloadButton"] button {{
    border-color: {GINGEMBRE_DARK};
    color: {GINGEMBRE_DARK};
}}
[data-testid="stExpander"] details {{
    border: 1px solid {BORDER};
    border-radius: 8px;
    background: {SURFACE};
}}
[data-testid="stExpander"] summary p {{
    font-weight: 600;
}}

/* ---- Rapport mensuel ---- */
.report-head {{
    background: {SURFACE_MUTED};
    border: 1px solid {BORDER};
    border-radius: 8px;
    padding: 1.1rem 1.4rem;
    margin: 1.2rem 0 .4rem;
}}
.report-eyebrow {{
    font-family: {FONT_MONO};
    font-size: .72rem;
    font-weight: 600;
    letter-spacing: .12em;
    text-transform: uppercase;
    color: {BISSAP};
}}
.report-title {{
    font-family: {FONT_HEAD};
    font-size: 1.9rem;
    font-weight: 700;
    line-height: 1.15;
    color: {INK};
    margin-top: .25rem;
}}
.report-meta {{
    display: flex;
    align-items: center;
    gap: .35rem;
    margin-top: .35rem;
    font-family: {FONT_MONO};
    font-size: .78rem;
    color: {MUTED};
}}
.report-meta .material-symbols-outlined {{
    font-size: 1rem;
}}
[class*="st-key-card_report_"] {{
    padding: 1.2rem 1.5rem 1rem;
    height: 100%;
}}
[class*="st-key-card_report_"] p,
[class*="st-key-card_report_"] li {{
    font-size: .98rem;
    line-height: 1.65;
    color: {INK_2};
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
    color: {INK};
}}
[class*="st-key-card_report_"] h3 {{
    font-size: 1rem;
    font-weight: 600;
    color: {INK};
    padding: .6rem 0 .1rem;
}}
.report-section-title {{
    display: flex;
    align-items: center;
    gap: .7rem;
    font-family: {FONT_HEAD};
    font-size: 1.25rem;
    font-weight: 600;
    color: {INK};
    margin: .1rem 0 .7rem;
}}
.report-icon {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 2.1rem;
    height: 2.1rem;
    border-radius: 6px;
    background: {BISSAP_TINT};
    color: {BISSAP};
    font-size: 1.2rem;
}}
.report-num {{
    font-family: {FONT_MONO};
    font-size: .78rem;
    color: {MUTED};
}}
.st-key-card_report_synthese,
.st-key-card_report_conclusion {{
    border-left: 4px solid {BISSAP} !important;
}}
.st-key-card_report_synthese p,
.st-key-card_report_conclusion p {{
    font-size: 1.06rem;
    line-height: 1.75;
    color: {INK};
}}
.st-key-card_report_conclusion .report-icon {{
    background: {BISSAP};
    color: #fff;
}}
.st-key-card_report_attention {{
    border-top: 3px solid {ERROR} !important;
}}
.st-key-card_report_attention .report-icon {{
    background: {ERROR_BG};
    color: {ERROR};
}}
.st-key-card_report_positifs {{
    border-top: 3px solid {SUCCESS} !important;
}}
.st-key-card_report_positifs .report-icon {{
    background: {SUCCESS_BG};
    color: {SUCCESS};
}}
.st-key-card_report_voix .report-icon,
.st-key-card_report_argent .report-icon {{
    background: {WARNING_BG};
    color: {WARNING};
}}
[class*="st-key-card_report_"] table {{
    width: 100%;
    border-collapse: collapse;
    font-size: .9rem;
    margin: .4rem 0 .6rem;
}}
[class*="st-key-card_report_"] th {{
    background: {SURFACE_MUTED};
    color: {MUTED};
    font-family: {FONT_MONO};
    font-size: .7rem;
    font-weight: 600;
    letter-spacing: .05em;
    text-transform: uppercase;
    border: none;
    border-bottom: 1px solid {BORDER};
    padding: .55rem .7rem;
}}
[class*="st-key-card_report_"] td {{
    border: none;
    border-bottom: 1px solid {GRID};
    padding: .55rem .7rem;
    color: {INK_2};
    font-variant-numeric: tabular-nums;
}}
[class*="st-key-card_report_"] tr:last-child td {{
    border-bottom: none;
}}

/* ---- Conversation (Ask the Data) ---- */
[class*="st-key-chat_user_"] [data-testid="stChatMessage"] {{
    flex-direction: row-reverse;
    width: fit-content;
    max-width: 70%;
    margin-left: auto;
    background: {SURFACE_MUTED};
    border: 1px solid {BORDER};
    border-radius: 8px 8px 2px 8px;
    padding: .8rem 1rem;
}}
[class*="st-key-chat_user_"] [data-testid="stChatMessage"] p {{
    text-align: right;
    color: {INK};
    font-weight: 500;
}}
[class*="st-key-chat_assistant_"] [data-testid="stChatMessage"] {{
    max-width: 85%;
    margin-right: auto;
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-left: 2px solid {BISSAP};
    border-radius: 2px 8px 8px 8px;
    padding: 1rem 1.2rem;
}}
[data-testid="stChatMessageAvatarUser"] {{
    background: {BISSAP};
    color: #fff;
}}
[data-testid="stChatMessageAvatarAssistant"] {{
    background: {BISSAP_TINT};
    color: {BISSAP};
}}
[data-testid="stChatInput"] {{
    border-radius: 8px;
    border-color: {BORDER};
}}
.st-key-ask_examples [data-testid="stBaseButton-secondary"] {{
    justify-content: space-between;
    min-height: 3rem;
}}

/* ---- Barre latérale ---- */
[data-testid="stSidebar"] {{
    border-right: 1px solid {BORDER};
}}
.sidebar-brand {{
    display: flex;
    align-items: center;
    gap: .75rem;
    padding: .2rem 0 1.1rem;
    margin-bottom: .4rem;
    border-bottom: 1px solid {BORDER};
}}
.sidebar-logo svg {{
    width: 2.8rem;
    height: 2.8rem;
    display: block;
}}
.sidebar-name {{
    font-family: {FONT_HEAD};
    font-size: 1.15rem;
    font-weight: 700;
    line-height: 1.15;
    color: {BISSAP};
}}
.sidebar-tag {{
    font-size: .78rem;
    color: {MUTED};
}}
.sidebar-nav-section {{
    margin: 1.1rem 0 .3rem;
    font-family: {FONT_MONO};
    font-size: .68rem;
    font-weight: 600;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: {MUTED};
}}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"] {{
    border-radius: 4px;
    border-left: 3px solid transparent;
}}
[data-testid="stSidebar"] [data-testid="stPageLink-NavLink"]:hover {{
    background: {SURFACE_MUTED};
}}
[data-testid="stSidebar"] h2 {{
    font-family: {FONT_MONO};
    font-size: .68rem;
    font-weight: 600;
    letter-spacing: .1em;
    text-transform: uppercase;
    color: {MUTED};
    padding-top: 1.4rem;
}}

/* ---- Pied de page ---- */
.footer {{
    margin-top: 3.5rem;
    padding-top: 1.4rem;
    border-top: 1px solid {BORDER};
    text-align: center;
    font-family: {FONT_MONO};
    font-size: .76rem;
    color: {MUTED};
}}
</style>
"""


def apply_theme() -> None:
    st.markdown(_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------
# COMPOSANTS
# ---------------------------------------------------------------------

def hero(
    eyebrow: str,
    title: str,
    text: str,
    pills: list[tuple[str, str, str]],
    badge: str = "",
) -> None:
    """`pills` : (icône Material, titre, sous-titre)."""
    pills_html = "".join(
        f'<div class="hero-pill">{icon(name)}<div>'
        f'<div class="hero-pill-title">{pill_title}</div>'
        f'<div class="hero-pill-sub">{sub}</div></div></div>'
        for name, pill_title, sub in pills
    )
    badge_html = f'<span class="hero-badge">{badge}</span>' if badge else ""

    st.markdown(
        f"""
        <div class="hero">
            <div class="hero-top"><div class="hero-eyebrow">{eyebrow}</div>{badge_html}</div>
            <div class="hero-title">{title}</div>
            <p class="hero-text">{text}</p>
            <div class="hero-pills">{pills_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def section(number: int, title: str, subtitle: str, help: str = "") -> None:
    """`help` : contenu HTML d'une infobulle affichée au survol d'une icône à côté du titre."""
    help_html = (
        f'<span class="section-help" tabindex="0" aria-label="Aide">{icon("info")}'
        f'<span class="section-help-tip" role="tooltip">{help}</span></span>'
        if help
        else ""
    )

    st.markdown(
        f"""
        <div class="section-head">
            <div class="section-num">AXE {number:02d}</div>
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


def card_title(text: str, tag: str = "") -> None:
    tag_html = f'<span class="card-title-tag">{tag}</span>' if tag else ""
    st.markdown(f'<div class="card-title">{text}{tag_html}</div>', unsafe_allow_html=True)


_BANNER_ICONS = {
    "warning": "warning",
    "info": "info",
    "success": "verified",
    "error": "error",
}


def banner(kind: str, title: str, text: str, tag: str = "") -> None:
    """Bandeau de qualité des données : warning, info, success ou error."""
    tag_html = f'<span class="banner-tag">{tag}</span>' if tag else ""
    st.markdown(
        f"""
        <div class="banner banner-{kind}">
            {icon(_BANNER_ICONS[kind])}
            <div>
                <div class="banner-title">{title}</div>
                <div class="banner-text">{text}</div>
            </div>
            {tag_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def bar_list(rows: list[dict]) -> None:
    """Liste de barres horizontales (une ligne par catégorie).

    Chaque ligne : label, value (texte affiché), ratio (0–1, largeur de la barre),
    color, et en option foot_left / foot_right sous la barre.
    """
    html = []

    for row in rows:
        ratio = 0.0 if pd.isna(row["ratio"]) else max(0.0, min(1.0, float(row["ratio"])))
        html.append(
            f"""
            <div class="bar-row">
                <div class="bar-head">
                    <span class="bar-label">{escape(str(row["label"]))}</span>
                    <span class="bar-value">{row["value"]}</span>
                </div>
                <div class="bar-track"><div class="bar-fill" style="width:{ratio * 100:.1f}%;background:{row["color"]}"></div></div>
                <div class="bar-foot"><span>{row.get("foot_left", "")}</span><span>{row.get("foot_right", "")}</span></div>
            </div>
            """
        )

    st.markdown("".join(html), unsafe_allow_html=True)


def question_card(key: str, page: str, question: str, tag: str, description: str, page_icon: str) -> None:
    """Carte cliquable vers une page : toute la carte suit le lien."""
    with st.container(key=f"qcard_{key}"):
        st.markdown(f'<span class="qcard-tag">{tag}</span>', unsafe_allow_html=True)
        st.page_link(page, label=question, icon=page_icon)
        st.markdown(f'<div class="qcard-desc">{description}</div>', unsafe_allow_html=True)


def sidebar_brand(name: str, tagline: str) -> None:
    st.sidebar.markdown(
        f"""
        <div class="sidebar-brand">
            <div class="sidebar-logo">{LOGO_SVG}</div>
            <div>
                <div class="sidebar-name">{name}</div>
                <div class="sidebar-tag">{tagline}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def sidebar_active_link(url_path: str) -> None:
    """Met en avant le lien de la page affichée (Streamlit ne le marque pas)."""
    st.markdown(
        f"""
        <style>
        [data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][href="{url_path}"] {{
            background: {BISSAP_TINT};
            border-left-color: {BISSAP};
        }}
        [data-testid="stSidebar"] a[data-testid="stPageLink-NavLink"][href="{url_path}"] * {{
            color: {BISSAP} !important;
            font-weight: 600;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def sidebar_nav_section(title: str) -> None:
    st.sidebar.markdown(f'<div class="sidebar-nav-section">{title}</div>', unsafe_allow_html=True)


def footer(text: str) -> None:
    st.markdown(f'<div class="footer">{text}</div>', unsafe_allow_html=True)
