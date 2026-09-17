{{ config(materialized='table') }}

WITH marketing AS (

    SELECT
        month,
        channel,
        campaign_spend_fcfa,
        planned_budget_fcfa,
        invoiced_fcfa,
        campaign_vs_invoiced_variance_fcfa,
        impressions,
        clicks
    FROM {{ ref('mart_marketing_channel_monthly') }}

),

sales AS (

    SELECT
        month,
        net_revenue_fcfa,
        net_units_sold,
        gross_revenue_fcfa,
        return_revenue_fcfa,
        missing_sales_days
    FROM {{ ref('mart_sales_monthly') }}

)

SELECT
    m.month,
    m.channel,

    m.campaign_spend_fcfa,
    m.planned_budget_fcfa,
    m.invoiced_fcfa,
    m.campaign_vs_invoiced_variance_fcfa,

    m.impressions,
    m.clicks,

    s.net_revenue_fcfa,
    s.net_units_sold,
    s.gross_revenue_fcfa,
    s.return_revenue_fcfa,
    s.missing_sales_days

FROM marketing m

LEFT JOIN sales s
    ON m.month = s.month