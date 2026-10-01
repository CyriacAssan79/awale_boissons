import re
from datetime import datetime
from pathlib import Path

import pandas as pd
import streamlit as st

from common import DB_PATH, load_monthly
from theme import card, month_label, section


REPORTS_DIR = Path("outputs/reports")

FR_MONTHS_FULL = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]

# Clé de carte (style CSS) et icône de chaque section du rapport.
SECTIONS = {
    "Synthèse": ("synthese", "1."),
    "Points d'attention": ("attention", "2."),
    "Points positifs": ("positifs", "3."),
    "Ventes": ("ventes", "4."),
    "Voix du client": ("voix", "5."),
    "Où va l'argent ?": ("argent", "6."),
    "Produits": ("produits", "7."),
    "Commandes WhatsApp": ("whatsapp", "8."),
    "WhatsApp": ("whatsapp", "9."),
    "Conclusion": ("conclusion", "10."),
}

# Disposition : une ligne = une liste de sections affichées côte à côte.
LAYOUT = [
    ["Synthèse"],
    ["Points d'attention", "Points positifs"],
    ["Ventes", "Voix du client"],
    ["Où va l'argent ?"],
    ["Produits", "Commandes WhatsApp"],
    ["Conclusion"],
]


@st.cache_resource(show_spinner=False)
def get_report_model():
    """Charge le modèle de rédaction une seule fois par processus Streamlit."""
    from ai.reporting.generate_report import DEFAULT_MODEL, load_model

    return load_model(DEFAULT_MODEL)


def saved_report_path(month: pd.Timestamp) -> Path:
    return REPORTS_DIR / f"rapport_{month.year}_{month.month:02d}.md"


def full_month_label(month: pd.Timestamp) -> str:
    return f"{FR_MONTHS_FULL[month.month - 1]} {month.year}"


def split_sections(report: str) -> dict[str, str]:
    """Découpe le rapport Markdown en {titre de section: contenu}."""
    sections: dict[str, list[str]] = {}
    current = None

    for line in report.splitlines():
        if line.startswith("# "):
            continue

        # Les anciens rapports numérotaient les titres (« ## 2. Ventes »).
        heading = re.match(r"^##\s+(?:\d+\.\s*)?(.+?)\s*$", line)

        if heading:
            current = heading.group(1)
            sections[current] = []
        elif current is not None:
            sections[current].append(line)

    return {title: "\n".join(lines).strip() for title, lines in sections.items()}


def report_card(title: str, body: str) -> None:
    key, icon = SECTIONS.get(title, (re.sub(r"\W+", "_", title.lower()), "📄"))

    with card(f"report_{key}"):
        st.markdown(
            f'<div class="report-section-title"><span>{icon}</span>{title}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(body)


def show_report(report: str, month: pd.Timestamp, path: Path) -> None:
    saved_at = datetime.fromtimestamp(path.stat().st_mtime)

    head, action = st.columns([3, 1], vertical_alignment="bottom")

    with head:
        st.markdown(
            f"""
            <div class="report-head">
                <div class="report-eyebrow">Rapport mensuel</div>
                <div class="report-title">Bilan de {full_month_label(month)}</div>
                <div class="report-meta">Rapport du {saved_at:%d/%m/%Y à %H:%M}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with action:
        st.download_button(
            "Télécharger",
            data=report,
            file_name=path.name,
            mime="text/markdown",
            icon=":material/download:",
            width="stretch",
        )

    sections = split_sections(report)
    placed = set()

    for row in LAYOUT:
        present = [title for title in row if title in sections]

        # Les anciens rapports titraient la section « WhatsApp ».
        if "Commandes WhatsApp" in row and "WhatsApp" in sections:
            present.append("WhatsApp")

        if not present:
            continue

        columns = st.columns(len(present)) if len(present) > 1 else [st.container()]

        for column, title in zip(columns, present):
            with column:
                report_card(title, sections[title])
            placed.add(title)

    for title, body in sections.items():
        if title not in placed:
            report_card(title, body)


section(
    5,
    "Rapport mensuel",
    "Le bilan du mois en un coup d'œil : ventes, dépenses, avis clients et commandes WhatsApp.",
)


# ---------------------------------------------------------------------
# PARAMÈTRES
# ---------------------------------------------------------------------

months = [
    pd.Timestamp(m)
    for m in load_monthly()["month"].dropna().sort_values().unique()
]

col1, col2, col3 = st.columns([1.2, 1.6, 1], vertical_alignment="bottom")

with col1:
    selected_month = st.selectbox(
        "Mois",
        options=months[::-1],
        format_func=lambda m: full_month_label(m).capitalize(),
    )

with col2:
    use_writer = st.toggle(
        "Synthèse rédigée automatiquement",
        value=True,
        help=(
            "Désactivé : la synthèse et la conclusion reprennent directement "
            "les constats du mois. Le rapport est alors prêt immédiatement."
        ),
    )

report_path = saved_report_path(selected_month)
state_key = f"report_{selected_month:%Y_%m}"

with col3:
    generate = st.button(
        "Mettre à jour le rapport" if report_path.exists() else "Créer le rapport",
        type="primary",
        icon=":material/auto_awesome:",
        width="stretch",
    )


# ---------------------------------------------------------------------
# GÉNÉRATION
# ---------------------------------------------------------------------

if generate:
    with st.status("Préparation du rapport…", expanded=True) as status:
        writer = None

        st.write("Rassemblement des chiffres du mois…")

        # Import différé : torch et transformers ralentiraient l'affichage
        # de la page alors qu'ils ne servent qu'à la génération.
        from ai.reporting.generate_report import generate_monthly_report, save_report

        if use_writer:
            st.write("Préparation de la rédaction (plus long la première fois)…")
            writer = get_report_model()
            st.write("Rédaction de la synthèse et de la conclusion…")

        try:
            result = generate_monthly_report(
                year=selected_month.year,
                month=selected_month.month,
                db_path=DB_PATH,
                model_bundle=writer,
            )
        except ValueError:
            status.update(label="Rapport indisponible", state="error")
            st.error(
                f"Les données de {full_month_label(selected_month)} ne sont pas "
                "encore disponibles."
            )
            st.stop()

        save_report(result.report, selected_month.year, selected_month.month)
        st.session_state[state_key] = result

        status.update(label="Rapport prêt", state="complete", expanded=False)


# ---------------------------------------------------------------------
# AFFICHAGE
# ---------------------------------------------------------------------

result = st.session_state.get(state_key)

if result is not None and result.llm_used and not result.llm_valid:
    st.info(
        "La synthèse rédigée automatiquement n'a pas passé nos vérifications : "
        "elle a été remplacée par un résumé direct des constats du mois."
    )

if report_path.exists():
    show_report(report_path.read_text(encoding="utf-8"), selected_month, report_path)

else:
    st.info(
        f"Aucun rapport pour {full_month_label(selected_month)}. "
        "Cliquez sur « Créer le rapport » pour le préparer."
    )


with st.expander("Comment ce rapport est préparé"):
    st.markdown(
        """
- **Tous les chiffres proviennent directement des données** de ventes, de
  campagnes, de commentaires clients et de commandes WhatsApp.
- **La synthèse et la conclusion sont rédigées automatiquement** à partir de
  constats simples (hausse ou baisse, avis majoritaires…). Elles ne contiennent
  aucun chiffre et sont vérifiées avant d'être affichées.
- **Le rapport décrit ce qui s'est passé** : il n'affirme pas qu'un canal a
  provoqué une hausse ou une baisse des ventes.
- La première rédaction peut prendre quelques minutes.
"""
    )
