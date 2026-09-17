WITH campaign_spend AS (

    SELECT
        month,
        platform AS channel,

        SUM(spend_fcfa) AS campaign_spend_fcfa,

        COUNT(*) AS campaign_rows,

        SUM(impressions) AS impressions,

        SUM(clicks) AS clicks,

        1 AS campaign_source_present

    FROM {{ ref('stg_campaign_spend') }}

    GROUP BY
        month,
        platform

),

media_plan AS (

    SELECT
        month_date AS month,
        channel,

        SUM(planned_budget_fcfa) AS planned_budget_fcfa,

        SUM(invoiced_fcfa) AS invoiced_fcfa,

        SUM(invoiced_available) AS invoiced_rows,

        COUNT(*) AS media_plan_rows,

        1 AS media_plan_source_present

    FROM {{ ref('stg_media_plan') }}

    GROUP BY
        month_date,
        channel

),

reconciled AS (

    SELECT

        COALESCE(
            campaign_spend.month,
            media_plan.month
        ) AS month,

        COALESCE(
            campaign_spend.channel,
            media_plan.channel
        ) AS channel,

        /* ============================================================
           SOURCE 1 — CAMPAIGN EXPORT
           ============================================================ */

        campaign_spend.campaign_spend_fcfa,

        campaign_spend.campaign_rows,

        campaign_spend.impressions,

        campaign_spend.clicks,

        /* ============================================================
           SOURCE 2 — MEDIA PLAN
           ============================================================ */

        media_plan.planned_budget_fcfa,

        media_plan.invoiced_fcfa,

        media_plan.invoiced_rows,

        media_plan.media_plan_rows,

        /* ============================================================
           COVERAGE
           ============================================================ */

        CASE

            WHEN campaign_spend.campaign_source_present = 1
            AND media_plan.media_plan_source_present = 1
            AND media_plan.invoiced_fcfa IS NOT NULL
                THEN 'both_available'

            WHEN campaign_spend.campaign_source_present = 1
            AND media_plan.media_plan_source_present = 1
            AND media_plan.invoiced_fcfa IS NULL
                THEN 'both_sources_invoice_missing'

            WHEN campaign_spend.campaign_source_present = 1
            AND media_plan.media_plan_source_present IS NULL
                THEN 'campaign_only'

            WHEN campaign_spend.campaign_source_present IS NULL
            AND media_plan.media_plan_source_present = 1
            AND media_plan.invoiced_fcfa IS NOT NULL
                THEN 'media_plan_only'

            WHEN campaign_spend.campaign_source_present IS NULL
            AND media_plan.media_plan_source_present = 1
            AND media_plan.invoiced_fcfa IS NULL
                THEN 'media_plan_only_invoice_missing'

            ELSE 'neither_available'

        END AS source_coverage,

        /* ============================================================
           DIFFERENCE
           ============================================================ */

        CASE
            WHEN campaign_spend.campaign_spend_fcfa IS NOT NULL
             AND media_plan.invoiced_fcfa IS NOT NULL
                THEN
                    campaign_spend.campaign_spend_fcfa
                    - media_plan.invoiced_fcfa

            ELSE NULL

        END AS campaign_vs_invoiced_variance_fcfa,

        /* ============================================================
           RATIO
           ============================================================ */

        CASE
            WHEN media_plan.invoiced_fcfa IS NOT NULL
             AND media_plan.invoiced_fcfa != 0
             AND campaign_spend.campaign_spend_fcfa IS NOT NULL

                THEN
                    campaign_spend.campaign_spend_fcfa
                    / media_plan.invoiced_fcfa

            ELSE NULL

        END AS campaign_to_invoiced_ratio

    FROM campaign_spend

    FULL OUTER JOIN media_plan  --Ici avec un INNER JOIN, celà supprimerait les cas où un canal n'existe que dans une source, d'où l'utilisation d'un FULL OUTER JOIN pour conserver toutes les lignes de chaque source

        ON campaign_spend.month = media_plan.month
        AND campaign_spend.channel = media_plan.channel

)

SELECT *

FROM reconciled