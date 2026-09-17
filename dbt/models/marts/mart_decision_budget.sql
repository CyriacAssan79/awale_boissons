{{ config(materialized='table') }}

WITH monthly AS (

    SELECT *
    FROM {{ ref('mart_monthly_performance') }}

),

channels AS (

    SELECT
        month,

        channel,

        campaign_spend_fcfa,
        planned_budget_fcfa,

        CASE
            WHEN planned_budget_fcfa > 0
            THEN campaign_spend_fcfa
                 / planned_budget_fcfa
            ELSE NULL
        END AS spend_vs_plan_ratio

    FROM {{ ref('mart_marketing_channel_monthly') }}

),

channel_monthly AS (

    SELECT
        month,

        SUM(
            CASE
                WHEN campaign_spend_fcfa > 0
                THEN campaign_spend_fcfa
                ELSE 0
            END
        ) AS total_channel_spend_fcfa,

        COUNT(DISTINCT channel) AS active_channels

    FROM channels

    GROUP BY month

)

SELECT
    m.month,

    m.campaign_spend_fcfa,
    m.planned_budget_fcfa,
    m.invoiced_budget_fcfa,
    m.campaign_vs_invoiced_variance_fcfa,

    m.net_revenue_fcfa,
    m.net_units_sold,

    m.impressions,
    m.clicks,

    m.blended_cpc_fcfa,
    m.blended_cpm_fcfa,

    m.missing_sales_days,

    c.active_channels,

    CASE
        WHEN m.planned_budget_fcfa > 0
        THEN m.campaign_spend_fcfa
             / m.planned_budget_fcfa
        ELSE NULL
    END AS overall_spend_vs_plan_ratio,

    CASE
        WHEN m.campaign_spend_fcfa > 0
        THEN m.net_revenue_fcfa
             / m.campaign_spend_fcfa
        ELSE NULL
    END AS revenue_to_campaign_spend_ratio

FROM monthly m

LEFT JOIN channel_monthly c
    ON m.month = c.month