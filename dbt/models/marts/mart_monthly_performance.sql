{{ config(materialized='table') }}

WITH marketing AS (

    SELECT
        month,

        SUM(campaign_spend_fcfa)
            AS campaign_spend_fcfa,

        SUM(planned_budget_fcfa)
            AS planned_budget_fcfa,

        SUM(
            COALESCE(invoiced_fcfa, 0)
        ) AS invoiced_budget_fcfa,

        SUM(
            COALESCE(campaign_vs_invoiced_variance_fcfa, 0)
        ) AS campaign_vs_invoiced_variance_fcfa,

        SUM(COALESCE(impressions, 0))
            AS impressions,

        SUM(COALESCE(clicks, 0))
            AS clicks

    FROM {{ ref('mart_marketing_channel_monthly') }}

    GROUP BY month

),

sales AS (

    SELECT
        month,

        net_units_sold,
        net_revenue_fcfa,

        gross_units,
        gross_revenue_fcfa,

        return_units,
        return_revenue_fcfa,

        active_pos,
        active_communes,

        observed_sales_days,
        calendar_days,
        missing_sales_days,

        avg_revenue_per_observed_day,
        return_rate_revenue

    FROM {{ ref('mart_sales_monthly') }}

)

SELECT
    s.month,

    m.campaign_spend_fcfa,
    m.planned_budget_fcfa,
    m.invoiced_budget_fcfa,
    m.campaign_vs_invoiced_variance_fcfa,

    m.impressions,
    m.clicks,

    CASE
        WHEN m.clicks > 0
        THEN m.campaign_spend_fcfa / m.clicks
        ELSE NULL
    END AS blended_cpc_fcfa,

    CASE
        WHEN m.impressions > 0
        THEN m.campaign_spend_fcfa
             / m.impressions * 1000
        ELSE NULL
    END AS blended_cpm_fcfa,

    s.net_units_sold,
    s.net_revenue_fcfa,

    s.gross_units,
    s.gross_revenue_fcfa,

    s.return_units,
    s.return_revenue_fcfa,

    s.active_pos,
    s.active_communes,

    s.observed_sales_days,
    s.calendar_days,
    s.missing_sales_days,

    s.avg_revenue_per_observed_day,
    s.return_rate_revenue

FROM sales s

LEFT JOIN marketing m
    ON s.month = m.month