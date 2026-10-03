import pandas as pd
import plotly.express as px
import streamlit as st

from common import integer, load_query, money
from theme import BISSAP, card, card_title, section, show_chart


allocation = load_query(
    """
    SELECT *
    FROM mart_budget_allocation
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

# Budget décidé (vars dbt) ou calculé : la colonne n'existe qu'après le dbt run
# qui a introduit le budget décidé.
decided = (
    "allocation_source" in recommendation.columns
    and (recommendation["allocation_source"] == "décidé").all()
)

with col1:
    st.metric("Budget total à tester", money(total_recommended))
    st.caption(
        "Répartition décidée pour un horizon de test de 90 jours, à partir du "
        "calcul de référence arrondi par tranches de 0,5 M FCFA."
        if decided
        else "Répartition proposée pour un horizon de test de 90 jours."
    )

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
            **(
                {
                    "Calcul de référence (FCFA)": recommendation["computed_budget_fcfa"]
                    .round(0)
                    .astype(int)
                    .map(integer)
                    .values
                }
                if decided
                else {}
            ),
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
