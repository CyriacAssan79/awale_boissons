import streamlit as st

from common import load_query, money, pct
from theme import BISSAP, CHANNEL_COLORS, bar_list, card, card_title, section


allocation = load_query(
    """
    SELECT *
    FROM mart_budget_allocation
    ORDER BY campaign_spend_fcfa DESC
    """
)


section(
    1,
    "Où va l'argent ?",
    "Dépenses de campagne observées par canal, comparées au plan.",
)

st.caption("Dépenses cumulées sur toute la période : le filtre de période ne s'applique pas ici.")


# ---------------------------------------------------------------------
# KPIs
# ---------------------------------------------------------------------

total_spend = allocation["campaign_spend_fcfa"].sum()
total_planned = allocation["planned_budget_fcfa"].sum()
total_invoiced = allocation["invoiced_fcfa"].sum()

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Dépenses campagne (export)", money(total_spend))

with col2:
    st.metric("Budget planifié (plan média)", money(total_planned))

with col3:
    st.metric(
        "Dépense / plan",
        pct(total_spend / total_planned) if total_planned else "—",
    )

with col4:
    st.metric(
        "Facturé (plan média)",
        money(total_invoiced),
        help="Montants facturés du plan média. L'écart avec l'export campagne est à réconcilier.",
    )

st.write("")


# ---------------------------------------------------------------------
# DÉPENSES PAR CANAL + TABLEAU
# ---------------------------------------------------------------------

col_bars, col_table = st.columns([5, 7])

with col_bars:
    with card("spend_chart"):
        card_title("Dépenses campagne par canal", tag="Export campagne")

        max_spend = allocation["campaign_spend_fcfa"].max() or 1

        rows = []
        for _, row in allocation.iterrows():
            foot_right = f"{pct(row['spend_share'])} du total"

            # Canal à zéro dans l'export mais facturé au plan média : écart visible.
            if row["campaign_spend_fcfa"] == 0 and row["invoiced_fcfa"] > 0:
                foot_right = f"facturé : {money(row['invoiced_fcfa'])}"

            rows.append(
                {
                    "label": row["channel"],
                    "value": money(row["campaign_spend_fcfa"]),
                    "ratio": row["campaign_spend_fcfa"] / max_spend,
                    "color": CHANNEL_COLORS.get(row["channel"], BISSAP),
                    "foot_left": f"plan : {pct(row['planned_share'])}",
                    "foot_right": foot_right,
                }
            )

        bar_list(rows)

with col_table:
    with card("spend_table"):
        card_title("Dépenses vs plan", tag=f"{len(allocation)} canaux")

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
            row_height=48,
            column_config={
                "channel": "Canal",
                "campaign_spend_fcfa": st.column_config.NumberColumn(
                    "Dépense FCFA",
                    format="localized",
                    width="small",
                ),
                "spend_share": st.column_config.ProgressColumn(
                    "Part dépense (%)",
                    format="%.1f",
                    min_value=0,
                    max_value=100,
                    width="small",
                ),
                "planned_share": st.column_config.ProgressColumn(
                    "Part plan (%)",
                    format="%.1f",
                    min_value=0,
                    max_value=100,
                    width="small",
                ),
                "spend_vs_plan_ratio": st.column_config.NumberColumn(
                    "Dépense / plan (%)",
                    format="%.1f",
                    width="small",
                ),
                "data_quality_status": "Qualité",
            },
        )

        st.caption(
            "Une association entre dépenses et ventes ne démontre pas une relation de "
            "cause à effet. Les canaux saisis à la main (radio, influenceurs, activation "
            "terrain) sont sous-représentés dans l'export campagne."
        )
