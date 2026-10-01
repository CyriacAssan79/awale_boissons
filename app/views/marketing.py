import plotly.express as px
import streamlit as st

from common import load_query
from theme import BISSAP, card, card_title, section, show_chart


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
