{{ config(materialized='table') }}

WITH reconciliation AS (

    SELECT
        month,
        channel,
        campaign_spend_fcfa,
        campaign_rows,
        impressions,
        clicks,
        planned_budget_fcfa,
        invoiced_fcfa,
        campaign_vs_invoiced_variance_fcfa,
        source_coverage
    FROM {{ ref('int_media_reconciliation') }}

),

campaign_products AS (

    SELECT
        campaign_month AS month,
        channel AS channel,

        COUNT(*) AS campaign_count,

        COUNT_IF(product = 'bissap') AS bissap_campaigns,
        COUNT_IF(product = 'gingembre') AS gingembre_campaigns,
        COUNT_IF(product = 'bouye') AS bouye_campaigns,

        COUNT_IF(product IS NULL) AS campaigns_without_product,

        SUM(
            CASE
                WHEN product_parse_failed THEN 1
                ELSE 0
            END
        ) AS product_parse_failure_count,

        SUM(
            CASE
                WHEN campaign_month_parse_failed THEN 1
                ELSE 0
            END
        ) AS month_parse_failure_count

    FROM {{ ref('int_campaign_normalized') }}

    GROUP BY
        campaign_month,
        channel
)

SELECT
    r.month,
    r.channel,

    COALESCE(r.campaign_spend_fcfa, 0)
        AS campaign_spend_fcfa,

    COALESCE(r.planned_budget_fcfa, 0)
        AS planned_budget_fcfa,

    r.invoiced_fcfa,

    r.campaign_vs_invoiced_variance_fcfa,

    r.source_coverage,

    COALESCE(r.campaign_rows, 0)
        AS campaign_rows,

    r.impressions,
    r.clicks,

    CASE
        WHEN r.clicks > 0
        THEN r.campaign_spend_fcfa / r.clicks
        ELSE NULL
    END AS cpc_fcfa,

    CASE
        WHEN r.impressions > 0
        THEN r.campaign_spend_fcfa / r.impressions * 1000
        ELSE NULL
    END AS cpm_fcfa,

    COALESCE(cp.campaign_count, 0)
        AS campaign_count,

    COALESCE(cp.bissap_campaigns, 0)
        AS bissap_campaigns,

    COALESCE(cp.gingembre_campaigns, 0)
        AS gingembre_campaigns,

    COALESCE(cp.bouye_campaigns, 0)
        AS bouye_campaigns,

    COALESCE(cp.campaigns_without_product, 0)
        AS campaigns_without_product,

    COALESCE(cp.product_parse_failure_count, 0)
        AS product_parse_failure_count,

    COALESCE(cp.month_parse_failure_count, 0)
        AS month_parse_failure_count

FROM reconciliation r

LEFT JOIN campaign_products cp
    ON r.month = cp.month
   AND r.channel = cp.channel