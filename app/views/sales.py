import plotly.express as px
import streamlit as st

from common import load_monthly, period_filter, safe_query
from theme import BISSAP, PRODUCT_COLORS, card, card_title, month_label, section, show_chart, subsection


active_months = period_filter()

monthly = load_monthly()
monthly_filtered = monthly[monthly["month"].isin(active_months)].copy()

product_mix = safe_query(
    """
    SELECT *
    FROM mart_product_mix_monthly
    ORDER BY month, product_sku
    """
)


section(
    2,
    "Que se passe-t-il côté ventes ?",
    "Chiffre d'affaires net, unités vendues, mix produit et couverture des données de ventes.",
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


subsection("Mix produit", "Ventes des points de vente (hors commandes WhatsApp)")

if product_mix is None or product_mix.empty:

    st.info(
        "Le mix produit n'est pas encore disponible dans la base. "
        "Exécuter python run_pipeline.py pour construire mart_product_mix_monthly."
    )

else:

    mix = product_mix[product_mix["month"].isin(active_months)].copy()
    mix["month_label"] = mix["month"].map(month_label)


    with card("product_mix_chart"):
        by_month = (
            mix.groupby(["month", "month_label", "product"], as_index=False)[
                "net_revenue_fcfa"
            ].sum()
        )

        fig_mix = px.bar(
            by_month,
            x="month_label",
            y="net_revenue_fcfa",
            color="product",
            color_discrete_map=PRODUCT_COLORS,
            title="CA net par produit et par mois",
            labels={
                "month_label": "",
                "net_revenue_fcfa": "CA net (FCFA)",
                "product": "Produit",
            },
        )

        fig_mix.update_traces(marker_cornerradius=4)
        fig_mix.update_xaxes(type="category")
        fig_mix.update_yaxes(tickformat=".2s", title=None)
        fig_mix.update_layout(legend_title_text="")

        show_chart(fig_mix, height=340)

    with card("product_mix_table"):
        card_title("Par produit et format — période sélectionnée")

        sku = (
            mix.groupby(["product", "format"], as_index=False)
            .agg(
                net_units=("net_units", "sum"),
                net_revenue_fcfa=("net_revenue_fcfa", "sum"),
                net_litres=("net_litres", "sum"),
            )
            .sort_values("net_revenue_fcfa", ascending=False)
        )

        total_revenue_mix = sku["net_revenue_fcfa"].sum()

        sku["share"] = (
            (sku["net_revenue_fcfa"] / total_revenue_mix * 100).round(1)
            if total_revenue_mix
            else 0.0
        )
        sku["per_litre"] = (
            sku["net_revenue_fcfa"] / sku["net_litres"]
        ).round(0)
        sku["net_units"] = sku["net_units"].round(0)
        sku["net_revenue_fcfa"] = sku["net_revenue_fcfa"].round(0)

        st.dataframe(
            sku[["product", "format", "net_units", "net_revenue_fcfa", "share", "per_litre"]],
            hide_index=True,
            width="stretch",
            column_config={
                "product": "Produit",
                "format": st.column_config.TextColumn("Format", width="small"),
                "net_units": st.column_config.NumberColumn(
                    "Unités", format="localized", width="small"
                ),
                "net_revenue_fcfa": st.column_config.NumberColumn(
                    "CA net (FCFA)", format="localized"
                ),
                "share": st.column_config.ProgressColumn(
                    "Part du CA (%)", format="%.1f", min_value=0, max_value=100
                ),
                "per_litre": st.column_config.NumberColumn(
                    "FCFA / litre", format="localized", width="small"
                ),
            },
        )

    if (mix["month_missing_sales_days"].fillna(0) > 0).any():
        st.caption(
            "Les mois avec des jours de ventes manquants sont incomplets : leurs volumes "
            "ne se comparent pas à ceux d'un mois complet."
        )

