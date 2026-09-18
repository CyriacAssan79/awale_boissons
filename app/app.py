from __future__ import annotations

import duckdb
import pandas as pd
import plotly.express as px
import streamlit as st


DB_PATH = "data/awale.duckdb"


st.set_page_config(
    page_title="Awalé Boissons — Marketing Decision Cockpit",
    page_icon="🥤",
    layout="wide",
)


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
# HEADER
# ---------------------------------------------------------------------

st.title("🥤 Awalé Boissons")
st.subheader("Marketing Decision Cockpit")

st.caption(
    "Vue décisionnelle mensuelle — données observées, qualité des données "
    "et signaux disponibles. Les résultats ne constituent pas une "
    "attribution causale des ventes aux canaux."
)


# ---------------------------------------------------------------------
# SIDEBAR
# ---------------------------------------------------------------------

st.sidebar.header("Filtres")

months = monthly["month"].dropna().sort_values().unique()

selected_months = st.sidebar.multiselect(
    "Période",
    options=months,
    default=list(months),
)

if selected_months:

    monthly_filtered = monthly[
        monthly["month"].isin(selected_months)
    ].copy()

else:

    monthly_filtered = monthly.copy()


# ---------------------------------------------------------------------
# GLOBAL KPIs
# ---------------------------------------------------------------------

latest = monthly_filtered.iloc[-1]

total_spend = monthly_filtered["campaign_spend_fcfa"].sum()
total_revenue = monthly_filtered["net_revenue_fcfa"].sum()
total_units = monthly_filtered["net_units_sold"].sum()

missing_days = monthly_filtered["missing_sales_days"].sum()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        "Dépenses marketing",
        money(total_spend),
    )

with col2:
    st.metric(
        "CA net observé",
        money(total_revenue),
    )

with col3:
    st.metric(
        "Unités vendues",
        f"{total_units:,.0f}".replace(",", " "),
    )

with col4:
    st.metric(
        "Jours de ventes manquants",
        f"{missing_days:,.0f}".replace(",", " "),
    )


if missing_days > 0:
    st.warning(
        "Attention : la période sélectionnée contient des jours sans données "
        "de ventes. Les comparaisons doivent tenir compte de cette couverture."
    )


# =====================================================================
# BLOC 1 — WHERE MONEY WENT
# =====================================================================

st.divider()
st.header("1. Où va l'argent ?")

col1, col2 = st.columns([1.4, 1])

with col1:

    spend_chart = allocation.copy()

    fig = px.bar(
        spend_chart,
        x="channel",
        y="campaign_spend_fcfa",
        title="Dépenses campagne par canal",
        labels={
            "channel": "Canal",
            "campaign_spend_fcfa": "Dépenses (FCFA)",
        },
    )

    fig.update_layout(
        xaxis_tickangle=-30,
        showlegend=False,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

with col2:

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
        display_allocation["campaign_spend_fcfa"]
        .round(0)
        .astype(int)
    )

    display_allocation["spend_share"] = (
        display_allocation["spend_share"] * 100
    ).round(1)

    display_allocation["planned_share"] = (
        display_allocation["planned_share"] * 100
    ).round(1)

    display_allocation["spend_vs_plan_ratio"] = (
        display_allocation["spend_vs_plan_ratio"] * 100
    ).round(1)

    st.dataframe(
        display_allocation,
        hide_index=True,
        use_container_width=True,
        column_config={
            "channel": "Canal",
            "campaign_spend_fcfa": st.column_config.NumberColumn(
                "Dépense FCFA",
                format="%.0f",
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
                "Spend / plan (%)",
                format="%.1f",
            ),
            "data_quality_status": "Qualité",
        },
    )


# =====================================================================
# BLOC 2 — SALES
# =====================================================================

st.divider()
st.header("2. Que se passe-t-il côté ventes ?")

sales_chart = monthly_filtered[
    [
        "month",
        "net_revenue_fcfa",
    ]
].copy()

fig_sales = px.line(
    sales_chart,
    x="month",
    y="net_revenue_fcfa",
    markers=True,
    title="Évolution du CA net observé",
    labels={
        "month": "Mois",
        "net_revenue_fcfa": "CA net (FCFA)",
    },
)

st.plotly_chart(
    fig_sales,
    use_container_width=True,
)

col1, col2 = st.columns(2)

with col1:

    sales_table = monthly_filtered[
        [
            "month",
            "net_revenue_fcfa",
            "net_units_sold",
            "missing_sales_days",
        ]
    ].copy()

    st.dataframe(
        sales_table,
        hide_index=True,
        use_container_width=True,
    )

with col2:

    st.markdown("**Couverture des données ventes**")

    coverage = monthly_filtered[
        [
            "month",
            "calendar_days",
            "observed_sales_days",
            "missing_sales_days",
        ]
    ].copy()

    coverage["coverage_pct"] = (
        coverage["observed_sales_days"]
        / coverage["calendar_days"]
        * 100
    ).round(1)

    st.dataframe(
        coverage,
        hide_index=True,
        use_container_width=True,
    )


# =====================================================================
# BLOC 3 — CUSTOMER VOICE
# =====================================================================

st.divider()
st.header("3. Que disent les clients ?")

if social_available and not social.empty:

    social_filtered = social[
        social["month"].isin(selected_months)
    ].copy()

    # -----------------------------------------------------------------
    # KPIs
    # -----------------------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        comments = social_filtered["comments_count"].sum()
        st.metric(
            "Commentaires",
            f"{comments:,.0f}".replace(",", " "),
        )

    with col2:
        positive = social_filtered["positive_comments_count"].sum()
        st.metric(
            "Positifs",
            f"{positive:,.0f}".replace(",", " "),
        )

    with col3:
        negative = social_filtered["negative_comments_count"].sum()
        st.metric(
            "Négatifs",
            f"{negative:,.0f}".replace(",", " "),
        )

    with col4:
        spam = social_filtered["spam_comments_count"].sum()
        st.metric(
            "Spam détecté",
            f"{spam:,.0f}".replace(",", " "),
        )

    # -----------------------------------------------------------------
    # Sentiment + thèmes
    # -----------------------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:

        sentiment_mapping = {
            "positive_comments_count": "positive",
            "negative_comments_count": "negative",
            "neutral_comments_count": "neutral",
        }

        sentiment = pd.DataFrame(
            {
                "sentiment": [
                    sentiment_mapping[c]
                    for c in sentiment_mapping
                    if c in social_filtered.columns
                ],
                "comments": [
                    social_filtered[c].sum()
                    for c in sentiment_mapping
                    if c in social_filtered.columns
                ],
            }
        )

        fig_sentiment = px.bar(
            sentiment,
            x="sentiment",
            y="comments",
            title="Sentiment des commentaires",
            labels={
                "sentiment": "Sentiment",
                "comments": "Commentaires",
            },
        )

        st.plotly_chart(
            fig_sentiment,
            use_container_width=True,
        )

    with col2:

        theme_mapping = {
            "taste_comments_count": "taste",
            "price_comments_count": "price",
            "promotion_comments_count": "promotion",
            "availability_comments_count": "availability",
            "packaging_comments_count": "packaging",
            "health_comments_count": "health",
            "delivery_comments_count": "delivery",
            "service_comments_count": "service",
            "other_theme_comments_count": "other",
        }

        themes = pd.DataFrame(
            {
                "theme": [
                    theme_mapping[c]
                    for c in theme_mapping
                    if c in social_filtered.columns
                ],
                "comments": [
                    social_filtered[c].sum()
                    for c in theme_mapping
                    if c in social_filtered.columns
                ],
            }
        ).sort_values("comments", ascending=False)

        fig_themes = px.bar(
            themes,
            x="comments",
            y="theme",
            orientation="h",
            title="Thèmes mentionnés",
            labels={
                "theme": "Thème",
                "comments": "Commentaires",
            },
        )

        st.plotly_chart(
            fig_themes,
            use_container_width=True,
        )

    # -----------------------------------------------------------------
    # Produits + qualité IA
    # -----------------------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:

        product_mapping = {
            "bissap_comments_count": "bissap",
            "gingembre_comments_count": "gingembre",
            "bouye_comments_count": "bouye",
            "multiple_product_comments_count": "multiple",
            "unknown_product_comments_count": "unknown",
            "no_product_comments_count": "none",
        }

        products = pd.DataFrame(
            {
                "product": [
                    product_mapping[c]
                    for c in product_mapping
                    if c in social_filtered.columns
                ],
                "comments": [
                    social_filtered[c].sum()
                    for c in product_mapping
                    if c in social_filtered.columns
                ],
            }
        ).sort_values("comments", ascending=False)

        st.markdown("**Produits mentionnés**")

        st.dataframe(
            products,
            hide_index=True,
            use_container_width=True,
        )

    with col2:

        st.markdown("**Qualité de l'inférence IA**")

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
            use_container_width=True,
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

st.divider()
st.header("4. Que faire ensuite ?")

st.info(
    "Cette section présente des signaux descriptifs et des hypothèses "
    "de pilotage. Elle ne calcule pas de ROI causal par canal."
)

st.markdown("**Proposition de répartition — 15 M FCFA**")

recommendation_view = recommendation[[
    "channel", "proposed_budget_fcfa", "proposed_share",
    "allocation_rationale", "test_condition",
]].copy()
recommendation_view["proposed_budget_fcfa"] = recommendation_view["proposed_budget_fcfa"].round(0).astype(int)
recommendation_view["proposed_share"] = (recommendation_view["proposed_share"] * 100).round(1)
total_recommended = recommendation_view["proposed_budget_fcfa"].sum()

col1, col2 = st.columns([1.05, 1.95])
with col1:
    st.metric("Budget total à tester", money(total_recommended))
    st.caption("Répartition proposée pour un horizon de test de 90 jours.")
with col2:
    fig_recommendation = px.bar(
        recommendation_view, x="channel", y="proposed_budget_fcfa",
        title="Répartition proposée des 15 M FCFA",
        labels={"channel": "Canal", "proposed_budget_fcfa": "Budget proposé (FCFA)"},
        text="proposed_budget_fcfa",
    )
    fig_recommendation.update_layout(xaxis_tickangle=-30, showlegend=False)
    fig_recommendation.update_traces(texttemplate="%{text:,.0f}", textposition="outside")
    st.plotly_chart(fig_recommendation, use_container_width=True)

st.dataframe(
    recommendation_view, hide_index=True, use_container_width=True,
    column_config={
        "channel": "Canal",
        "proposed_budget_fcfa": st.column_config.NumberColumn("Budget proposé (FCFA)", format="%.0f"),
        "proposed_share": st.column_config.NumberColumn("Part proposée (%)", format="%.1f"),
        "allocation_rationale": "Pourquoi tester ce canal",
        "test_condition": "Condition de test",
    },
)

with st.expander("Voir le contexte historique et la qualité de mesure"):
    historical_cols = [
        "channel", "campaign_spend_fcfa", "spend_share", "planned_share",
        "spend_vs_plan_ratio", "cpc_fcfa", "cpm_fcfa", "data_quality_status",
    ]
    historical_view = allocation[[c for c in historical_cols if c in allocation.columns]].copy()
    for c in ["spend_share", "planned_share", "spend_vs_plan_ratio"]:
        if c in historical_view.columns:
            historical_view[c] = (historical_view[c] * 100).round(1)
    st.dataframe(historical_view, hide_index=True, use_container_width=True, column_config={
        "channel": "Canal",
        "campaign_spend_fcfa": st.column_config.NumberColumn("Dépense historique (FCFA)", format="%.0f"),
        "spend_share": st.column_config.NumberColumn("Part dépense (%)", format="%.1f"),
        "planned_share": st.column_config.NumberColumn("Part plan (%)", format="%.1f"),
        "spend_vs_plan_ratio": st.column_config.NumberColumn("Dépense / plan (%)", format="%.1f"),
        "cpc_fcfa": st.column_config.NumberColumn("CPC (FCFA)", format="%.0f"),
        "cpm_fcfa": st.column_config.NumberColumn("CPM (FCFA)", format="%.0f"),
        "data_quality_status": "Qualité",
    })

st.subheader("Cadre de test pour les prochains 15 M FCFA")

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

st.table(test_plan)

if total_recommended != 15_000_000:
    st.error(f"Contrôle budget : la proposition totalise {money(total_recommended)} au lieu de 15 000 000 FCFA.")
else:
    st.success("Contrôle budget : la proposition totalise exactement 15 000 000 FCFA.")


# =====================================================================
# FOOTER
# =====================================================================

st.divider()

st.caption(
    "Awalé Boissons — Challenge Kômian | "
    "Pipeline DuckDB + dbt | Dashboard décisionnel"
)