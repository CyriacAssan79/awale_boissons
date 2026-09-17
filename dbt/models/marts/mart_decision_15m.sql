{{ config(materialized='table') }}

WITH evidence AS (

    SELECT
        channel,

        campaign_spend_fcfa,
        planned_budget_fcfa,
        invoiced_fcfa,

        spend_share,

        CASE
            WHEN SUM(planned_budget_fcfa) OVER () > 0
            THEN planned_budget_fcfa
                 / SUM(planned_budget_fcfa) OVER ()
            ELSE NULL
        END AS planned_share,

        spend_vs_plan_ratio,

        impressions,
        clicks,

        cpc_fcfa,
        cpm_fcfa,

        campaign_rows,
        campaign_count,
        active_months,

        months_missing_impressions,
        months_missing_clicks,

        campaigns_without_product,
        product_parse_failure_count,
        month_parse_failure_count,

        latest_month_spend_fcfa,
        previous_month_spend_fcfa,
        latest_month_spend_change,

        recent_3m_spend_fcfa,
        recent_vs_earlier_spend_change,

        period_coverage,
        data_quality_status

    FROM {{ ref('mart_channel_evidence') }}

),

monthly AS (

    SELECT
        SUM(net_revenue_fcfa) AS total_net_revenue_fcfa,
        SUM(net_units_sold) AS total_net_units_sold,

        SUM(missing_sales_days) AS total_missing_sales_days,

        AVG(
            CASE
                WHEN campaign_spend_fcfa > 0
                THEN net_revenue_fcfa
                     / campaign_spend_fcfa
            END
        ) AS avg_monthly_revenue_spend_ratio

    FROM {{ ref('mart_monthly_performance') }}

),

allocation AS (

    SELECT
        channel,
        campaign_spend_fcfa,

        CASE
            WHEN campaign_spend_fcfa > 0
            THEN campaign_spend_fcfa
                 / SUM(campaign_spend_fcfa) OVER ()
            ELSE 0
        END AS observed_spend_share

    FROM {{ ref('mart_budget_allocation') }}

)

SELECT
    e.channel,

    e.campaign_spend_fcfa,
    e.planned_budget_fcfa,
    e.invoiced_fcfa,

    e.spend_share,
    e.planned_share,
    e.spend_vs_plan_ratio,

    e.impressions,
    e.clicks,
    e.cpc_fcfa,
    e.cpm_fcfa,

    e.campaign_rows,
    e.campaign_count,
    e.active_months,

    e.months_missing_impressions,
    e.months_missing_clicks,

    e.campaigns_without_product,
    e.product_parse_failure_count,
    e.month_parse_failure_count,

    e.latest_month_spend_fcfa,
    e.previous_month_spend_fcfa,
    e.latest_month_spend_change,

    e.recent_3m_spend_fcfa,
    e.recent_vs_earlier_spend_change,

    e.period_coverage,
    e.data_quality_status,

    a.observed_spend_share,

    m.total_net_revenue_fcfa,
    m.total_net_units_sold,
    m.total_missing_sales_days,
    m.avg_monthly_revenue_spend_ratio,

    CASE
        WHEN e.data_quality_status = 'good'
            THEN 'high'

        WHEN e.data_quality_status = 'moderate'
            THEN 'medium'

        ELSE 'limited'
    END AS evidence_quality,

    CASE
        WHEN e.clicks > 0
         AND e.impressions > 0
         AND e.data_quality_status <> 'limited'
            THEN 'digital_metrics_available'

        WHEN e.data_quality_status = 'limited'
            THEN 'limited_measurement'

        ELSE 'non_digital_or_partial_metrics'
    END AS measurement_profile

FROM evidence e

LEFT JOIN allocation a
    ON e.channel = a.channel

CROSS JOIN monthly m