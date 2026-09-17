WITH source_data AS (

    SELECT
        plan_id,
        month,
        channel,
        planned_budget_fcfa,
        invoiced_fcfa,
        objective,
        owner,
        notes

    FROM {{ source('raw', 'raw_media_plan') }}

),

cleaned AS (

    SELECT

        /* ============================================================
           IDENTIFICATION
           ============================================================ */

        TRIM(plan_id) AS plan_id,

        /* ============================================================
           MONTH
           ============================================================ */

        TRIM(month) AS month_raw,

        CASE
            WHEN LOWER(TRIM(month)) = 'janvier 2026'
                THEN DATE '2026-01-01'

            WHEN LOWER(TRIM(month)) IN (
                'février 2026',
                'fevrier 2026'
            )
                THEN DATE '2026-02-01'

            WHEN LOWER(TRIM(month)) = 'mars 2026'
                THEN DATE '2026-03-01'

            WHEN LOWER(TRIM(month)) = 'avril 2026'
                THEN DATE '2026-04-01'

            WHEN LOWER(TRIM(month)) = 'mai 2026'
                THEN DATE '2026-05-01'

            WHEN LOWER(TRIM(month)) = 'juin 2026'
                THEN DATE '2026-06-01'

            ELSE NULL
        END AS month_date,

        /* ============================================================
           CHANNEL
           ============================================================ */

        TRIM(channel) AS channel_raw,

        CASE
            WHEN LOWER(TRIM(channel)) IN (
                'fb/ig',
                'meta',
                'facebook',
                'instagram'
            )
                THEN 'Meta'

            WHEN LOWER(TRIM(channel)) = 'tiktok'
                THEN 'TikTok'

            WHEN LOWER(TRIM(channel)) IN (
                'google',
                'google ads'
            )
                THEN 'Google'

            WHEN LOWER(TRIM(channel)) IN (
                'influenceur',
                'influenceurs'
            )
                THEN 'Influenceurs'

            WHEN LOWER(TRIM(channel)) = 'radio'
                THEN 'Radio'

            WHEN LOWER(TRIM(channel)) = 'activation terrain'
                THEN 'Activation terrain'

            ELSE TRIM(channel)
        END AS channel,

        /* ============================================================
           BUDGETS
           ============================================================ */

        planned_budget_fcfa,
        invoiced_fcfa,

        /* ============================================================
           TEXT
           ============================================================ */

        NULLIF(TRIM(objective), '') AS objective,

        NULLIF(TRIM(owner), '') AS owner,

        NULLIF(TRIM(notes), '') AS notes

    FROM source_data

)

SELECT

    plan_id,

    month_raw,
    month_date,

    channel_raw,
    channel,

    planned_budget_fcfa,
    invoiced_fcfa,

    /*
       Variance calculable uniquement lorsque la facture existe.
       NULL reste NULL : on ne transforme pas une facture absente
       en 0.
    */
    CASE
        WHEN invoiced_fcfa IS NOT NULL
            THEN invoiced_fcfa - planned_budget_fcfa
        ELSE NULL
    END AS variance_fcfa,

    /*
       Permet de mesurer la couverture de la facturation.
    */
    CASE
        WHEN invoiced_fcfa IS NOT NULL
            THEN 1
        ELSE 0
    END AS invoiced_available,

    invoiced_fcfa IS NULL AS invoiced_missing,

    objective,
    owner,
    notes,

    /* ================================================================
       QUALITY FLAGS
       ================================================================ */

    month_date IS NULL AS month_parse_failed,

    planned_budget_fcfa IS NULL AS planned_budget_missing,

    planned_budget_fcfa < 0 AS invalid_planned_budget

FROM cleaned