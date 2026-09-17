{{ config(materialized='table') }}

WITH channel_monthly AS (

    SELECT
        month,
        channel,

        campaign_spend_fcfa,
        planned_budget_fcfa,
        invoiced_fcfa,
        campaign_vs_invoiced_variance_fcfa,

        campaign_rows,
        impressions,
        clicks,

        campaign_count,
        campaigns_without_product,
        product_parse_failure_count,
        month_parse_failure_count

    FROM {{ ref('mart_marketing_channel_monthly') }}

),

channel_totals AS (

    SELECT
        channel,

        SUM(campaign_spend_fcfa) AS campaign_spend_fcfa,
        SUM(planned_budget_fcfa) AS planned_budget_fcfa,
        SUM(COALESCE(invoiced_fcfa, 0)) AS invoiced_fcfa,

        SUM(COALESCE(impressions, 0)) AS impressions,
        SUM(COALESCE(clicks, 0)) AS clicks,

        SUM(campaign_rows) AS campaign_rows,
        SUM(campaign_count) AS campaign_count,

        SUM(campaigns_without_product)
            AS campaigns_without_product,

        SUM(product_parse_failure_count)
            AS product_parse_failure_count,

        SUM(month_parse_failure_count)
            AS month_parse_failure_count,

        COUNT(DISTINCT month) AS active_months

    FROM channel_monthly

    GROUP BY channel

),

grand_total AS (

    SELECT
        SUM(campaign_spend_fcfa) AS total_campaign_spend_fcfa,
        SUM(planned_budget_fcfa) AS total_planned_budget_fcfa,
        SUM(COALESCE(invoiced_fcfa, 0)) AS total_invoiced_fcfa
    FROM channel_totals

)

SELECT
    c.channel,

    c.campaign_spend_fcfa,
    c.planned_budget_fcfa,
    c.invoiced_fcfa,

    c.campaign_spend_fcfa
        - COALESCE(c.invoiced_fcfa, 0)
        AS campaign_vs_invoiced_fcfa,

    CASE
        WHEN g.total_campaign_spend_fcfa > 0
        THEN c.campaign_spend_fcfa
             / g.total_campaign_spend_fcfa
        ELSE NULL
    END AS spend_share,

    CASE
        WHEN g.total_planned_budget_fcfa > 0
        THEN c.planned_budget_fcfa
             / g.total_planned_budget_fcfa
        ELSE NULL
    END AS planned_share,

    CASE
        WHEN c.planned_budget_fcfa > 0
        THEN c.campaign_spend_fcfa
             / c.planned_budget_fcfa
        ELSE NULL
    END AS spend_vs_plan_ratio,

    c.impressions,
    c.clicks,

    CASE
        WHEN c.clicks > 0
        THEN c.campaign_spend_fcfa / c.clicks
        ELSE NULL
    END AS cpc_fcfa,

    CASE
        WHEN c.impressions > 0
        THEN c.campaign_spend_fcfa
             / c.impressions * 1000
        ELSE NULL
    END AS cpm_fcfa,

    c.campaign_rows,
    c.campaign_count,
    c.active_months,

    c.campaigns_without_product,
    c.product_parse_failure_count,
    c.month_parse_failure_count,

    CASE
        WHEN c.campaigns_without_product = 0
         AND c.product_parse_failure_count = 0
         AND c.month_parse_failure_count = 0
        THEN 'good'

        WHEN c.product_parse_failure_count <= 2
         AND c.month_parse_failure_count <= 2
        THEN 'moderate'

        ELSE 'limited'
    END AS data_quality_status

FROM channel_totals c

CROSS JOIN grand_total g