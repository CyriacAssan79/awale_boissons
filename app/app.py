from __future__ import annotations

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st

from theme import (
    BISSAP,
    BOUYE,
    SENTIMENT_COLORS,
    apply_theme,
    card,
    card_title,
    footer,
    hero,
    month_label,
    section,
    show_chart,
    sidebar_brand,
)


DB_PATH = "data/awale.duckdb"


st.set_page_config(
    page_title="Awalé Boissons — Marketing Decision Cockpit",
    page_icon="🥤",
    layout="wide",
)

apply_theme()


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


# ---------------------------------------------------------------------
# DATA
# ---------------------------------------------------------------------

monthly = load_query(
    """
    SELECT *
    FROM mart_monthly_performance
    ORDER BY month
    """
)

decision = load_query(
    """
    SELECT *
    FROM mart_decision_budget
    ORDER BY month
    """
)

allocation = load_query(
    """
    SELECT *
    FROM mart_budget_allocation
    ORDER BY campaign_spend_fcfa DESC
    """
)

channel_evidence = load_query(
    """
    SELECT *
    FROM mart_channel_evidence
    ORDER BY campaign_spend_fcfa DESC
    """
)

recommendation = load_query(
    """
    SELECT *
    FROM mart_budget_recommendation_15m
    ORDER BY proposed_budget_fcfa DESC
    """
)

whatsapp = load_query(
    """
    SELECT *
    FROM mart_whatsapp_monthly
    ORDER BY month
    """
)

social_available = table_exists("mart_social_monthly")


if social_available:
    social = load_query(
        """
        SELECT *
        FROM mart_social_monthly
        ORDER BY month
        """
    )
else:
    social = pd.DataFrame()


# ---------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------

sidebar_brand("Awalé Boissons", "Marketing Decision Cockpit", "🥤")

st.sidebar.header("Filtres")

months = monthly["month"].dropna().sort_values().unique()

selected_months = st.sidebar.multiselect(
    "Période",
    options=months,
    default=list(months),
    format_func=month_label,
)

# Sans sélection, tout le jeu de données est affiché (ventes comme social).
active_months = selected_months or list(months)

monthly_filtered = monthly[monthly["month"].isin(active_months)].copy()

st.sidebar.caption(
    "Données observées uniquement. Le filtre s'applique aux ventes "
    "et aux commentaires clients."
)


# ---------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------

hero(
    eyebrow="Awalé Boissons",
    title="Marketing Decision Cockpit",
    text=(
        "Vue décisionnelle mensuelle — données observées, qualité des données "
        "et signaux disponibles. Les résultats ne constituent pas une "
        "attribution causale des ventes aux canaux."
    ),
    pills=["Données observées", "Qualité des données", "Sans attribution causale"],
)


# ---------------------------------------------------------------------
# GLOBAL KPIs
# ---------------------------------------------------------------------

total_spend = monthly_filtered["campaign_spend_fcfa"].sum()
total_revenue = monthly_filtered["net_revenue_fcfa"].sum()
total_units = monthly_filtered["net_units_sold"].sum()

missing_days = monthly_filtered["missing_sales_days"].sum()

st.write("")

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Dépenses marketing", money(total_spend))

with col2:
    st.metric("CA net observé", money(total_revenue))

with col3:
    st.metric("Unités vendues", integer(total_units))

with col4:
    st.metric("Jours de ventes manquants", integer(missing_days))


if missing_days > 0:
    st.warning(
        "Attention : la période sélectionnée contient des jours sans données "
        "de ventes. Les comparaisons doivent tenir compte de cette couverture."
    )


# =====================================================================
# BLOC 1 — WHERE MONEY WENT
# =====================================================================

section(
    1,
    "Où va l'argent ?",
    "Dépenses de campagne observées par canal, comparées au plan.",
)

with card("spend_chart"):
    fig = px.bar(
        allocation,
        x="campaign_spend_fcfa",
        y="channel",
        orientation="h",
        title="Dépenses campagne par canal",
        labels={
            "channel": "",
            "campaign_spend_fcfa": "Dépenses (FCFA)",
        },
        text="campaign_spend_fcfa",
        color_discrete_sequence=[BISSAP],
    )

    fig.update_traces(
        texttemplate="%{text:,.0f}",
        textposition="outside",
        cliponaxis=False,
        marker_cornerradius=6,
    )
    fig.update_layout(showlegend=False)
    fig.update_yaxes(autorange="reversed", showgrid=False, title=None)
    fig.update_xaxes(
        showgrid=True,
        gridcolor="#F0E7DA",
        tickformat=".2s",
        title=None,
        range=[0, allocation["campaign_spend_fcfa"].max() * 1.15],
    )

    show_chart(fig, height=340)

with card("spend_table"):
    card_title("Dépenses vs plan")

    display_allocation = allocation[
        [
            "channel",
            "campaign_spend_fcfa",
            "spend_share",
            "planned_share",
            "spend_vs_plan_ratio",
            "data_quality_status",
        ]
    ].copy()

    display_allocation["campaign_spend_fcfa"] = (
        display_allocation["campaign_spend_fcfa"].round(0).astype(int)
    )

    for column in ["spend_share", "planned_share", "spend_vs_plan_ratio"]:
        display_allocation[column] = (display_allocation[column] * 100).round(1)

    st.dataframe(
        display_allocation,
        hide_index=True,
        width="stretch",
        column_config={
            "channel": "Canal",
            "campaign_spend_fcfa": st.column_config.NumberColumn(
                "Dépense FCFA",
                format="localized",
            ),
            "spend_share": st.column_config.ProgressColumn(
                "Part dépense (%)",
                format="%.1f",
                min_value=0,
                max_value=100,
            ),
            "planned_share": st.column_config.ProgressColumn(
                "Part plan (%)",
                format="%.1f",
                min_value=0,
                max_value=100,
            ),
            "spend_vs_plan_ratio": st.column_config.NumberColumn(
                "Spend / plan (%)",
                format="%.1f",
            ),
            "data_quality_status": "Qualité",
        },
    )


# =====================================================================
# BLOC 2 — SALES
# =====================================================================

section(
    2,
    "Que se passe-t-il côté ventes ?",
    "Chiffre d'affaires net, unités vendues et couverture des données de ventes.",
)

sales_chart = monthly_filtered[["month", "net_revenue_fcfa"]].copy()
sales_chart["month_label"] = sales_chart["month"].map(month_label)

with card("sales_chart"):
    fig_sales = px.line(
        sales_chart,
        x="month_label",
        y="net_revenue_fcfa",
        markers=True,
        title="Évolution du CA net observé",
        labels={
            "month_label": "",
            "net_revenue_fcfa": "CA net (FCFA)",
        },
    )

    fig_sales.update_traces(
        line=dict(color=BISSAP, width=3),
        marker=dict(size=10, color=BISSAP, line=dict(color="#fff", width=2)),
        fill="tozeroy",
        fillcolor="rgba(156, 31, 63, 0.10)",
    )
    fig_sales.update_xaxes(type="category")
    fig_sales.update_yaxes(tickformat=".2s", title=None)

    show_chart(fig_sales, height=340)

col1, col2 = st.columns(2)

with col1:
    with card("sales_table"):
        card_title("Ventes par mois")

        sales_table = monthly_filtered[
            ["month", "net_revenue_fcfa", "net_units_sold", "missing_sales_days"]
        ].copy()
        sales_table["month"] = sales_table["month"].map(month_label)
        sales_table["net_revenue_fcfa"] = sales_table["net_revenue_fcfa"].round(0)
        sales_table["net_units_sold"] = sales_table["net_units_sold"].round(0)

        st.dataframe(
            sales_table,
            hide_index=True,
            width="stretch",
            column_config={
                "month": "Mois",
                "net_revenue_fcfa": st.column_config.NumberColumn(
                    "CA net (FCFA)",
                    format="localized",
                ),
                "net_units_sold": st.column_config.NumberColumn(
                    "Unités vendues",
                    format="localized",
                ),
                "missing_sales_days": st.column_config.NumberColumn(
                    "Jours manquants",
                    format="%d",
                ),
            },
        )

with col2:
    with card("sales_coverage"):
        card_title("Couverture des données ventes")

        coverage = monthly_filtered[
            ["month", "calendar_days", "observed_sales_days", "missing_sales_days"]
        ].copy()

        coverage["coverage_pct"] = (
            coverage["observed_sales_days"] / coverage["calendar_days"] * 100
        ).round(1)
        coverage["month"] = coverage["month"].map(month_label)

        st.dataframe(
            coverage,
            hide_index=True,
            width="stretch",
            column_config={
                "month": "Mois",
                "calendar_days": st.column_config.NumberColumn(
                    "Calendaires",
                    format="%d",
                    width="small",
                ),
                "observed_sales_days": st.column_config.NumberColumn(
                    "Observés",
                    format="%d",
                    width="small",
                ),
                "missing_sales_days": st.column_config.NumberColumn(
                    "Manquants",
                    format="%d",
                    width="small",
                ),
                "coverage_pct": st.column_config.ProgressColumn(
                    "Couverture (%)",
                    format="%.1f",
                    min_value=0,
                    max_value=100,
                    width="medium",
                ),
            },
        )


# =====================================================================
# BLOC 3 — CUSTOMER VOICE
# =====================================================================

section(
    3,
    "Que disent les clients ?",
    "Sentiment, thèmes et produits mentionnés dans les commentaires.",
)

if social_available and not social.empty:

    social_filtered = social[social["month"].isin(active_months)].copy()

    # -----------------------------------------------------------------
    # KPIs
    # -----------------------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Commentaires", integer(social_filtered["comments_count"].sum()))

    with col2:
        st.metric("Positifs", integer(social_filtered["positive_comments_count"].sum()))

    with col3:
        st.metric("Négatifs", integer(social_filtered["negative_comments_count"].sum()))

    with col4:
        st.metric("Spam détecté", integer(social_filtered["spam_comments_count"].sum()))

    st.write("")

    # -----------------------------------------------------------------
    # Sentiment + thèmes
    # -----------------------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:
        with card("sentiment"):
            sentiment = totals(
                social_filtered,
                {
                    "positive_comments_count": "Positif",
                    "neutral_comments_count": "Neutre",
                    "negative_comments_count": "Négatif",
                },
                "sentiment",
            )

            fig_sentiment = px.bar(
                sentiment,
                x="sentiment",
                y="comments",
                color="sentiment",
                color_discrete_map=SENTIMENT_COLORS,
                title="Sentiment des commentaires",
                labels={"sentiment": "", "comments": "Commentaires"},
                text="comments",
            )

            fig_sentiment.update_traces(
                textposition="outside",
                cliponaxis=False,
                marker_cornerradius=6,
            )
            fig_sentiment.update_layout(showlegend=False)
            fig_sentiment.update_yaxes(title=None)

            show_chart(fig_sentiment, height=340)

    with col2:
        with card("themes"):
            themes = totals(
                social_filtered,
                {
                    "taste_comments_count": "Goût",
                    "price_comments_count": "Prix",
                    "promotion_comments_count": "Promotion",
                    "availability_comments_count": "Disponibilité",
                    "packaging_comments_count": "Emballage",
                    "health_comments_count": "Santé",
                    "delivery_comments_count": "Livraison",
                    "service_comments_count": "Service",
                    "other_theme_comments_count": "Autre",
                },
                "theme",
            ).sort_values("comments", ascending=False)

            fig_themes = px.bar(
                themes,
                x="comments",
                y="theme",
                orientation="h",
                title="Thèmes mentionnés",
                labels={"theme": "", "comments": "Commentaires"},
                text="comments",
                color_discrete_sequence=[BOUYE],
            )

            fig_themes.update_traces(
                textposition="outside",
                cliponaxis=False,
                marker_cornerradius=6,
            )
            fig_themes.update_layout(showlegend=False)
            fig_themes.update_yaxes(
                autorange="reversed",
                showgrid=False,
                title=None,
            )
            fig_themes.update_xaxes(showgrid=True, gridcolor="#F0E7DA", title=None)

            show_chart(fig_themes, height=340)

    # -----------------------------------------------------------------
    # Produits + qualité IA
    # -----------------------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:
        with card("products"):
            card_title("Produits mentionnés")

            products = totals(
                social_filtered,
                {
                    "bissap_comments_count": "Bissap",
                    "gingembre_comments_count": "Gingembre",
                    "bouye_comments_count": "Bouye",
                    "multiple_product_comments_count": "Plusieurs produits",
                    "unknown_product_comments_count": "Produit inconnu",
                    "no_product_comments_count": "Aucun produit",
                },
                "product",
            ).sort_values("comments", ascending=False)

            st.dataframe(
                products,
                hide_index=True,
                width="stretch",
                column_config={
                    "product": "Produit",
                    "comments": st.column_config.ProgressColumn(
                        "Commentaires",
                        format="%d",
                        min_value=0,
                        max_value=max(1, int(products["comments"].max())),
                    ),
                },
            )

    with col2:
        with card("ai_quality"):
            card_title("Qualité de l'inférence IA")

            quality = pd.DataFrame(
                {
                    "Indicateur": [
                        "Commentaires analysés",
                        "Modèle local utilisé",
                        "Règles seules suffisantes",
                    ],
                    "Volume": [
                        social_filtered["comments_count"].sum(),
                        social_filtered["model_used_count"].sum(),
                        social_filtered["rules_complete_count"].sum(),
                    ],
                }
            )

            st.dataframe(
                quality,
                hide_index=True,
                width="stretch",
                column_config={
                    "Volume": st.column_config.NumberColumn(format="localized"),
                },
            )

            st.caption(
                "Le benchmark humain de 50 commentaires sert à évaluer "
                "le classifieur ; il ne constitue pas un jeu d'entraînement."
            )

else:

    st.warning(
        "La mart Customer Voice n'est pas disponible. "
        "Exécuter dbt pour construire mart_social_monthly."
    )


# =====================================================================
# BLOC 4 — WHAT TO DO NEXT
# =====================================================================

section(
    4,
    "Que faire ensuite ?",
    "Proposition de répartition pour tester 15 M FCFA — signaux descriptifs, pas un ROI causal.",
)

st.info(
    "Cette section présente des signaux descriptifs et des hypothèses "
    "de pilotage. Elle ne calcule pas de ROI causal par canal."
)

recommendation_view = recommendation[
    [
        "channel",
        "proposed_budget_fcfa",
        "proposed_share",
        "allocation_rationale",
        "test_condition",
    ]
].copy()

recommendation_view["proposed_budget_fcfa"] = (
    recommendation_view["proposed_budget_fcfa"].round(0).astype(int)
)
recommendation_view["proposed_share"] = (
    recommendation_view["proposed_share"] * 100
).round(1)

total_recommended = recommendation_view["proposed_budget_fcfa"].sum()

col1, col2 = st.columns([1, 2.2])

with col1:
    st.metric("Budget total à tester", money(total_recommended))
    st.caption("Répartition proposée pour un horizon de test de 90 jours.")

with col2:
    with card("recommendation_chart"):
        fig_recommendation = px.bar(
            recommendation_view,
            x="channel",
            y="proposed_budget_fcfa",
            title="Répartition proposée des 15 M FCFA",
            labels={"channel": "", "proposed_budget_fcfa": "Budget proposé (FCFA)"},
            text="proposed_budget_fcfa",
            color_discrete_sequence=[BISSAP],
        )

        fig_recommendation.update_traces(
            texttemplate="%{text:,.0f}",
            textposition="outside",
            cliponaxis=False,
            marker_cornerradius=6,
        )
        fig_recommendation.update_layout(showlegend=False)
        fig_recommendation.update_yaxes(tickformat=".2s", title=None)

        show_chart(fig_recommendation, height=360)

with card("recommendation_table"):
    card_title("Détail par canal")

    # st.table retourne à la ligne : les justifications restent lisibles en entier.
    recommendation_table = pd.DataFrame(
        {
            "Canal": recommendation_view["channel"],
            "Budget proposé (FCFA)": recommendation_view["proposed_budget_fcfa"].map(integer),
            "Part (%)": recommendation_view["proposed_share"].map("{:.1f}".format),
            "Pourquoi tester ce canal": recommendation_view["allocation_rationale"],
            "Condition de test": recommendation_view["test_condition"],
        }
    ).set_index("Canal")

    st.table(recommendation_table)

with st.expander("Voir le contexte historique et la qualité de mesure"):
    historical_cols = [
        "channel",
        "campaign_spend_fcfa",
        "spend_share",
        "planned_share",
        "spend_vs_plan_ratio",
        "cpc_fcfa",
        "cpm_fcfa",
        "data_quality_status",
    ]

    historical_view = allocation[
        [c for c in historical_cols if c in allocation.columns]
    ].copy()

    for c in ["spend_share", "planned_share", "spend_vs_plan_ratio"]:
        if c in historical_view.columns:
            historical_view[c] = (historical_view[c] * 100).round(1)

    st.dataframe(
        historical_view,
        hide_index=True,
        width="stretch",
        column_config={
            "channel": "Canal",
            "campaign_spend_fcfa": st.column_config.NumberColumn(
                "Dépense historique (FCFA)",
                format="localized",
            ),
            "spend_share": st.column_config.NumberColumn(
                "Part dépense (%)",
                format="%.1f",
            ),
            "planned_share": st.column_config.NumberColumn(
                "Part plan (%)",
                format="%.1f",
            ),
            "spend_vs_plan_ratio": st.column_config.NumberColumn(
                "Dépense / plan (%)",
                format="%.1f",
            ),
            "cpc_fcfa": st.column_config.NumberColumn(
                "CPC (FCFA)",
                format="%.0f",
            ),
            "cpm_fcfa": st.column_config.NumberColumn(
                "CPM (FCFA)",
                format="%.0f",
            ),
            "data_quality_status": "Qualité",
        },
    )

st.write("")

with card("test_plan"):
    card_title("Cadre de test pour les prochains 15 M FCFA")

    test_plan = pd.DataFrame(
        {
            "Élément": [
                "Budget à tester",
                "Horizon",
                "Mesure ventes",
                "Mesure Customer Voice",
                "Qualité des données",
                "Attribution",
            ],
            "Cadre": [
                "15 000 000 FCFA",
                "90 jours",
                "CA net + unités + couverture",
                "sentiment + thèmes + produits",
                "écarts + données manquantes",
                "Pas d'attribution causale directe",
            ],
        }
    )

    st.dataframe(test_plan, hide_index=True, width="stretch")

if total_recommended != 15_000_000:
    st.error(
        f"Contrôle budget : la proposition totalise {money(total_recommended)} "
        "au lieu de 15 000 000 FCFA."
    )
else:
    st.success("Contrôle budget : la proposition totalise exactement 15 000 000 FCFA.")


# =====================================================================
# FOOTER
# =====================================================================

footer(
    "Awalé Boissons — Challenge Kômian | "
    "Pipeline DuckDB + dbt | Dashboard décisionnel"
)
