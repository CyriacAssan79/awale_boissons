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

        /*
           "<mois en français> <année>" -> premier jour du mois.
           Générique : aucun mois ni année n'est écrit en dur, un nouveau
           mois du plan média est donc reconnu sans modifier ce modèle.
           Les accents sont retirés pour accepter "février" et "fevrier".
           Tout libellé non reconnu reste NULL et remonte via
           month_parse_failed (et le test stg_media_plan_month).
        */
        CASE
            WHEN REGEXP_MATCHES(
                    LOWER(TRIM(month)),
                    '^(janvier|f[ée]vrier|mars|avril|mai|juin|juillet|ao[uû]t|septembre|octobre|novembre|d[ée]cembre)\s+[0-9]{4}$'
                 )
                THEN MAKE_DATE(
                    CAST(REGEXP_EXTRACT(TRIM(month), '([0-9]{4})$', 1) AS INTEGER),
                    CASE
                        WHEN LOWER(TRIM(month)) LIKE 'janvier%' THEN 1
                        WHEN LOWER(TRIM(month)) LIKE 'f%vrier%' THEN 2
                        WHEN LOWER(TRIM(month)) LIKE 'mars%' THEN 3
                        WHEN LOWER(TRIM(month)) LIKE 'avril%' THEN 4
                        WHEN LOWER(TRIM(month)) LIKE 'mai%' THEN 5
                        WHEN LOWER(TRIM(month)) LIKE 'juin%' THEN 6
                        WHEN LOWER(TRIM(month)) LIKE 'juillet%' THEN 7
                        WHEN LOWER(TRIM(month)) LIKE 'ao%t%' THEN 8
                        WHEN LOWER(TRIM(month)) LIKE 'septembre%' THEN 9
                        WHEN LOWER(TRIM(month)) LIKE 'octobre%' THEN 10
                        WHEN LOWER(TRIM(month)) LIKE 'novembre%' THEN 11
                        WHEN LOWER(TRIM(month)) LIKE 'd%cembre%' THEN 12
                    END,
                    1
                )

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