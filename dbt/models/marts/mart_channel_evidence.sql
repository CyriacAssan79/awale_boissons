{{ config(materialized='table') }}

WITH monthly AS (

    SELECT
        month,
        channel,

        campaign_spend_fcfa,
        planned_budget_fcfa,
        invoiced_fcfa,

        impressions,
        clicks,

        campaign_rows,
        campaign_count,

        campaigns_without_product,
        product_parse_failure_count,
        month_parse_failure_count

    FROM {{ ref('mart_marketing_channel_monthly') }}

),

-- Le rang est calculé sur les mois du jeu de données (tous canaux confondus) :
-- "mois le plus récent" désigne donc le même mois pour tous les canaux, même
-- si un canal n'a pas de ligne ce mois-là (son latest_month_spend reste alors
-- NULL, et non zéro : une absence de ligne n'est pas une dépense nulle prouvée).
ranked AS (

    SELECT
        *,
        DENSE_RANK() OVER (ORDER BY month DESC) AS month_rank

    FROM monthly

),

period AS (

    SELECT COUNT(DISTINCT month) AS months_in_period
    FROM monthly

),

aggregated AS (

    SELECT
        channel,

        SUM(campaign_spend_fcfa)
            AS campaign_spend_fcfa,

        SUM(planned_budget_fcfa)
            AS planned_budget_fcfa,

        SUM(COALESCE(invoiced_fcfa, 0))
            AS invoiced_fcfa,

        SUM(COALESCE(impressions, 0))
            AS impressions,

        SUM(COALESCE(clicks, 0))
            AS clicks,

        SUM(campaign_rows) AS campaign_rows,
        SUM(campaign_count) AS campaign_count,

        COUNT(DISTINCT month) AS active_months,

        COUNT_IF(impressions IS NULL)
            AS months_missing_impressions,

        COUNT_IF(clicks IS NULL)
            AS months_missing_clicks,

        SUM(campaigns_without_product)
            AS campaigns_without_product,

        SUM(product_parse_failure_count)
            AS product_parse_failure_count,

        SUM(month_parse_failure_count)
            AS month_parse_failure_count,

        MAX(
            CASE
                WHEN month_rank = 1
                THEN campaign_spend_fcfa
            END
        ) AS latest_month_spend_fcfa,

        MAX(
            CASE
                WHEN month_rank = 2
                THEN campaign_spend_fcfa
            END
        ) AS previous_month_spend_fcfa,

        SUM(
            CASE
                WHEN month_rank <= 3
                THEN campaign_spend_fcfa
                ELSE 0
            END
        ) AS recent_3m_spend_fcfa,

        -- Les 3 mois précédant les 3 plus récents (rangs 4 à 6) : jamais
        -- l'historique entier, même quand le jeu de données s'allonge.
        SUM(
            CASE
                WHEN month_rank BETWEEN 4 AND 6
                THEN campaign_spend_fcfa
                ELSE 0
            END
        ) AS earlier_3m_spend_fcfa

    FROM ranked

    GROUP BY channel

)

SELECT
    a.channel,

    a.campaign_spend_fcfa,
    a.planned_budget_fcfa,
    a.invoiced_fcfa,

    CASE
        WHEN a.planned_budget_fcfa > 0
        THEN a.campaign_spend_fcfa
             / a.planned_budget_fcfa
        ELSE NULL
    END AS spend_vs_plan_ratio,

    CASE
        WHEN a.campaign_spend_fcfa > 0
        THEN a.campaign_spend_fcfa
             / NULLIF(
                 (
                     SELECT SUM(campaign_spend_fcfa)
                     FROM aggregated
                 ),
                 0
             )
        ELSE NULL
    END AS spend_share,

    a.impressions,
    a.clicks,

    CASE
        WHEN a.clicks > 0
        THEN a.campaign_spend_fcfa / a.clicks
        ELSE NULL
    END AS cpc_fcfa,

    CASE
        WHEN a.impressions > 0
        THEN a.campaign_spend_fcfa
             / a.impressions * 1000
        ELSE NULL
    END AS cpm_fcfa,

    a.campaign_rows,
    a.campaign_count,
    a.active_months,

    a.months_missing_impressions,
    a.months_missing_clicks,

    a.campaigns_without_product,
    a.product_parse_failure_count,
    a.month_parse_failure_count,

    a.latest_month_spend_fcfa,
    a.previous_month_spend_fcfa,

    CASE
        WHEN a.previous_month_spend_fcfa > 0
        THEN (
            a.latest_month_spend_fcfa
            / a.previous_month_spend_fcfa
        ) - 1
        ELSE NULL
    END AS latest_month_spend_change,

    a.recent_3m_spend_fcfa,
    a.earlier_3m_spend_fcfa,

    CASE
        WHEN a.earlier_3m_spend_fcfa > 0
        THEN (
            a.recent_3m_spend_fcfa
            / a.earlier_3m_spend_fcfa
        ) - 1
        ELSE NULL
    END AS recent_vs_earlier_spend_change,

    CASE
        WHEN a.active_months = (SELECT months_in_period FROM period)
            THEN 'full_period'
        ELSE 'partial_period'
    END AS period_coverage,

    CASE
        WHEN a.months_missing_impressions = 0
        AND a.months_missing_clicks = 0
        AND a.product_parse_failure_count = 0
        AND a.month_parse_failure_count = 0
        THEN 'good'

        WHEN a.months_missing_impressions <= 1
        AND a.months_missing_clicks <= 1
        AND a.product_parse_failure_count <= 2
        AND a.month_parse_failure_count <= 2
        THEN 'moderate'

        ELSE 'limited'
    END AS data_quality_status

FROM aggregated a