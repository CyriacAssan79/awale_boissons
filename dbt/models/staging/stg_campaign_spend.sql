-- FONCTIONNEMENT DU SCRIPT
--               RAW
--                │
--                │ raw_campaign_spend_export
--                │
--                ▼
--              STAGING
--                │
--                │ stg_campaign_spend
--                │
--                ├── texte nettoyé
--                ├── dates typées
--                ├── devises identifiées
--                ├── montants numériques
--                ├── EUR → FCFA × 655
--                ├── objectifs normalisés
--                ├── plateformes normalisées
--                ├── mois
--                ├── NULL conservés
--                └── flags de qualité
----------------------

WITH source_data AS (

    SELECT
        platform,
        campaign_name,
        date_start,
        date_end,
        spend,
        impressions,
        clicks,
        objective,

        ROW_NUMBER() OVER (
            PARTITION BY
                platform,
                campaign_name,
                date_start,
                date_end,
                spend,
                impressions,
                clicks,
                objective
            ORDER BY platform
        ) AS exact_duplicate_rank

    FROM {{ source('raw', 'raw_campaign_spend_export') }}

),

deduplicated AS (

    SELECT
        platform,
        campaign_name,
        date_start,
        date_end,
        spend,
        impressions,
        clicks,
        objective

    FROM source_data

    WHERE exact_duplicate_rank = 1

),

cleaned_text AS (

    SELECT

        /* ============================================================
           RAW / TEXT
           ============================================================ */

        TRIM(platform) AS platform_raw,

        TRIM(campaign_name) AS campaign_name,

        TRIM(campaign_name) AS campaign_name_raw,

        TRIM(date_start) AS date_start_raw,

        TRIM(date_end) AS date_end_raw,

        TRIM(spend) AS spend_raw,

        TRIM(objective) AS objective_raw,

        impressions,

        clicks,

        /* ============================================================
           PLATFORM NORMALIZATION
           ============================================================ */

        CASE

            WHEN LOWER(TRIM(platform)) = 'meta'
                THEN 'Meta'

            WHEN LOWER(TRIM(platform)) = 'tiktok'
                THEN 'TikTok'

            WHEN LOWER(TRIM(platform)) IN (
                'google',
                'google ads'
            )
                THEN 'Google'

            WHEN LOWER(TRIM(platform)) IN (
                'influenceur',
                'influenceurs'
            )
                THEN 'Influenceurs'

            WHEN LOWER(TRIM(platform)) = 'radio'
                THEN 'Radio'

            ELSE TRIM(platform)

        END AS platform_normalized,

        /* ============================================================
           OBJECTIVE NORMALIZATION
           ============================================================ */

        CASE

            WHEN LOWER(TRIM(objective)) IN (
                'traffic',
                'trafic'
            )
                THEN 'traffic'

            WHEN LOWER(TRIM(objective)) = 'engagement'
                THEN 'engagement'

            WHEN LOWER(TRIM(objective)) IN (
                'notoriété',
                'notoriete',
                'awareness'
            )
                THEN 'awareness'

            WHEN LOWER(TRIM(objective)) IN (
                'conversions',
                'conv'
            )
                THEN 'conversions'

            ELSE LOWER(TRIM(objective))

        END AS objective_normalized

    FROM deduplicated

),

/* ====================================================================
   NORMALISATION DES DATES
   ==================================================================== */

normalized_dates AS (

    SELECT
        *,

        /* ============================================================
           DATE START
           ============================================================ */

        CASE

            /* YYYY-MM-DD */
            WHEN TRY_STRPTIME(
                date_start_raw,
                '%Y-%m-%d'
            ) IS NOT NULL

                THEN TRY_STRPTIME(
                    date_start_raw,
                    '%Y-%m-%d'
                )::DATE

            /* DD/MM/YYYY */
            WHEN TRY_STRPTIME(
                date_start_raw,
                '%d/%m/%Y'
            ) IS NOT NULL

                THEN TRY_STRPTIME(
                    date_start_raw,
                    '%d/%m/%Y'
                )::DATE

            /* 1 janvier 2026 */
            WHEN LOWER(date_start_raw)
                ~ '^[0-9]{1,2} janvier [0-9]{4}$'

                THEN MAKE_DATE(
                    CAST(
                        REGEXP_EXTRACT(
                            date_start_raw,
                            '([0-9]{4})$',
                            1
                        ) AS INTEGER
                    ),
                    1,
                    CAST(
                        REGEXP_EXTRACT(
                            date_start_raw,
                            '^([0-9]{1,2})',
                            1
                        ) AS INTEGER
                    )
                )

            /* février */
            WHEN LOWER(date_start_raw)
                ~ '^[0-9]{1,2} février [0-9]{4}$'

                THEN MAKE_DATE(
                    CAST(
                        REGEXP_EXTRACT(
                            date_start_raw,
                            '([0-9]{4})$',
                            1
                        ) AS INTEGER
                    ),
                    2,
                    CAST(
                        REGEXP_EXTRACT(
                            date_start_raw,
                            '^([0-9]{1,2})',
                            1
                        ) AS INTEGER
                    )
                )

            /* mars */
            WHEN LOWER(date_start_raw)
                ~ '^[0-9]{1,2} mars [0-9]{4}$'

                THEN MAKE_DATE(
                    CAST(
                        REGEXP_EXTRACT(
                            date_start_raw,
                            '([0-9]{4})$',
                            1
                        ) AS INTEGER
                    ),
                    3,
                    CAST(
                        REGEXP_EXTRACT(
                            date_start_raw,
                            '^([0-9]{1,2})',
                            1
                        ) AS INTEGER
                    )
                )

            /* avril */
            WHEN LOWER(date_start_raw)
                ~ '^[0-9]{1,2} avril [0-9]{4}$'

                THEN MAKE_DATE(
                    CAST(
                        REGEXP_EXTRACT(
                            date_start_raw,
                            '([0-9]{4})$',
                            1
                        ) AS INTEGER
                    ),
                    4,
                    CAST(
                        REGEXP_EXTRACT(
                            date_start_raw,
                            '^([0-9]{1,2})',
                            1
                        ) AS INTEGER
                    )
                )

            /* mai */
            WHEN LOWER(date_start_raw)
                ~ '^[0-9]{1,2} mai [0-9]{4}$'

                THEN MAKE_DATE(
                    CAST(
                        REGEXP_EXTRACT(
                            date_start_raw,
                            '([0-9]{4})$',
                            1
                        ) AS INTEGER
                    ),
                    5,
                    CAST(
                        REGEXP_EXTRACT(
                            date_start_raw,
                            '^([0-9]{1,2})',
                            1
                        ) AS INTEGER
                    )
                )

            /* juin */
            WHEN LOWER(date_start_raw)
                ~ '^[0-9]{1,2} juin [0-9]{4}$'

                THEN MAKE_DATE(
                    CAST(
                        REGEXP_EXTRACT(
                            date_start_raw,
                            '([0-9]{4})$',
                            1
                        ) AS INTEGER
                    ),
                    6,
                    CAST(
                        REGEXP_EXTRACT(
                            date_start_raw,
                            '^([0-9]{1,2})',
                            1
                        ) AS INTEGER
                    )
                )

            /* juillet */
            WHEN LOWER(date_start_raw)
                ~ '^[0-9]{1,2} juillet [0-9]{4}$'

                THEN MAKE_DATE(
                    CAST(REGEXP_EXTRACT(date_start_raw, '([0-9]{4})$', 1) AS INTEGER),
                    7,
                    CAST(REGEXP_EXTRACT(date_start_raw, '^([0-9]{1,2})', 1) AS INTEGER)
                )

            /* août */
            WHEN LOWER(date_start_raw)
                ~ '^[0-9]{1,2} août [0-9]{4}$'

                THEN MAKE_DATE(
                    CAST(REGEXP_EXTRACT(date_start_raw, '([0-9]{4})$', 1) AS INTEGER),
                    8,
                    CAST(REGEXP_EXTRACT(date_start_raw, '^([0-9]{1,2})', 1) AS INTEGER)
                )

            /* septembre */
            WHEN LOWER(date_start_raw)
                ~ '^[0-9]{1,2} septembre [0-9]{4}$'

                THEN MAKE_DATE(
                    CAST(REGEXP_EXTRACT(date_start_raw, '([0-9]{4})$', 1) AS INTEGER),
                    9,
                    CAST(REGEXP_EXTRACT(date_start_raw, '^([0-9]{1,2})', 1) AS INTEGER)
                )

            /* octobre */
            WHEN LOWER(date_start_raw)
                ~ '^[0-9]{1,2} octobre [0-9]{4}$'

                THEN MAKE_DATE(
                    CAST(REGEXP_EXTRACT(date_start_raw, '([0-9]{4})$', 1) AS INTEGER),
                    10,
                    CAST(REGEXP_EXTRACT(date_start_raw, '^([0-9]{1,2})', 1) AS INTEGER)
                )

            /* novembre */
            WHEN LOWER(date_start_raw)
                ~ '^[0-9]{1,2} novembre [0-9]{4}$'

                THEN MAKE_DATE(
                    CAST(REGEXP_EXTRACT(date_start_raw, '([0-9]{4})$', 1) AS INTEGER),
                    11,
                    CAST(REGEXP_EXTRACT(date_start_raw, '^([0-9]{1,2})', 1) AS INTEGER)
                )

            /* décembre */
            WHEN LOWER(date_start_raw)
                ~ '^[0-9]{1,2} décembre [0-9]{4}$'

                THEN MAKE_DATE(
                    CAST(REGEXP_EXTRACT(date_start_raw, '([0-9]{4})$', 1) AS INTEGER),
                    12,
                    CAST(REGEXP_EXTRACT(date_start_raw, '^([0-9]{1,2})', 1) AS INTEGER)
                )

            ELSE NULL

        END AS date_start,

        /* ============================================================
           DATE END
           ============================================================ */

        CASE

            /* YYYY-MM-DD */
            WHEN TRY_STRPTIME(
                date_end_raw,
                '%Y-%m-%d'
            ) IS NOT NULL

                THEN TRY_STRPTIME(
                    date_end_raw,
                    '%Y-%m-%d'
                )::DATE

            /* DD/MM/YYYY */
            WHEN TRY_STRPTIME(
                date_end_raw,
                '%d/%m/%Y'
            ) IS NOT NULL

                THEN TRY_STRPTIME(
                    date_end_raw,
                    '%d/%m/%Y'
                )::DATE

            /* janvier */
            WHEN LOWER(date_end_raw)
                ~ '^[0-9]{1,2} janvier [0-9]{4}$'

                THEN MAKE_DATE(
                    CAST(REGEXP_EXTRACT(date_end_raw, '([0-9]{4})$', 1) AS INTEGER),
                    1,
                    CAST(REGEXP_EXTRACT(date_end_raw, '^([0-9]{1,2})', 1) AS INTEGER)
                )

            /* février */
            WHEN LOWER(date_end_raw)
                ~ '^[0-9]{1,2} février [0-9]{4}$'

                THEN MAKE_DATE(
                    CAST(REGEXP_EXTRACT(date_end_raw, '([0-9]{4})$', 1) AS INTEGER),
                    2,
                    CAST(REGEXP_EXTRACT(date_end_raw, '^([0-9]{1,2})', 1) AS INTEGER)
                )

            /* mars */
            WHEN LOWER(date_end_raw)
                ~ '^[0-9]{1,2} mars [0-9]{4}$'

                THEN MAKE_DATE(
                    CAST(REGEXP_EXTRACT(date_end_raw, '([0-9]{4})$', 1) AS INTEGER),
                    3,
                    CAST(REGEXP_EXTRACT(date_end_raw, '^([0-9]{1,2})', 1) AS INTEGER)
                )

            /* avril */
            WHEN LOWER(date_end_raw)
                ~ '^[0-9]{1,2} avril [0-9]{4}$'

                THEN MAKE_DATE(
                    CAST(REGEXP_EXTRACT(date_end_raw, '([0-9]{4})$', 1) AS INTEGER),
                    4,
                    CAST(REGEXP_EXTRACT(date_end_raw, '^([0-9]{1,2})', 1) AS INTEGER)
                )

            /* mai */
            WHEN LOWER(date_end_raw)
                ~ '^[0-9]{1,2} mai [0-9]{4}$'

                THEN MAKE_DATE(
                    CAST(REGEXP_EXTRACT(date_end_raw, '([0-9]{4})$', 1) AS INTEGER),
                    5,
                    CAST(REGEXP_EXTRACT(date_end_raw, '^([0-9]{1,2})', 1) AS INTEGER)
                )

            /* juin */
            WHEN LOWER(date_end_raw)
                ~ '^[0-9]{1,2} juin [0-9]{4}$'

                THEN MAKE_DATE(
                    CAST(REGEXP_EXTRACT(date_end_raw, '([0-9]{4})$', 1) AS INTEGER),
                    6,
                    CAST(REGEXP_EXTRACT(date_end_raw, '^([0-9]{1,2})', 1) AS INTEGER)
                )

            /* juillet */
            WHEN LOWER(date_end_raw)
                ~ '^[0-9]{1,2} juillet [0-9]{4}$'

                THEN MAKE_DATE(
                    CAST(REGEXP_EXTRACT(date_end_raw, '([0-9]{4})$', 1) AS INTEGER),
                    7,
                    CAST(REGEXP_EXTRACT(date_end_raw, '^([0-9]{1,2})', 1) AS INTEGER)
                )

            /* août */
            WHEN LOWER(date_end_raw)
                ~ '^[0-9]{1,2} août [0-9]{4}$'

                THEN MAKE_DATE(
                    CAST(REGEXP_EXTRACT(date_end_raw, '([0-9]{4})$', 1) AS INTEGER),
                    8,
                    CAST(REGEXP_EXTRACT(date_end_raw, '^([0-9]{1,2})', 1) AS INTEGER)
                )

            /* septembre */
            WHEN LOWER(date_end_raw)
                ~ '^[0-9]{1,2} septembre [0-9]{4}$'

                THEN MAKE_DATE(
                    CAST(REGEXP_EXTRACT(date_end_raw, '([0-9]{4})$', 1) AS INTEGER),
                    9,
                    CAST(REGEXP_EXTRACT(date_end_raw, '^([0-9]{1,2})', 1) AS INTEGER)
                )

            /* octobre */
            WHEN LOWER(date_end_raw)
                ~ '^[0-9]{1,2} octobre [0-9]{4}$'

                THEN MAKE_DATE(
                    CAST(REGEXP_EXTRACT(date_end_raw, '([0-9]{4})$', 1) AS INTEGER),
                    10,
                    CAST(REGEXP_EXTRACT(date_end_raw, '^([0-9]{1,2})', 1) AS INTEGER)
                )

            /* novembre */
            WHEN LOWER(date_end_raw)
                ~ '^[0-9]{1,2} novembre [0-9]{4}$'

                THEN MAKE_DATE(
                    CAST(REGEXP_EXTRACT(date_end_raw, '([0-9]{4})$', 1) AS INTEGER),
                    11,
                    CAST(REGEXP_EXTRACT(date_end_raw, '^([0-9]{1,2})', 1) AS INTEGER)
                )

            /* décembre */
            WHEN LOWER(date_end_raw)
                ~ '^[0-9]{1,2} décembre [0-9]{4}$'

                THEN MAKE_DATE(
                    CAST(REGEXP_EXTRACT(date_end_raw, '([0-9]{4})$', 1) AS INTEGER),
                    12,
                    CAST(REGEXP_EXTRACT(date_end_raw, '^([0-9]{1,2})', 1) AS INTEGER)
                )

            ELSE NULL

        END AS date_end

    FROM cleaned_text

),

parsed_spend AS (

    SELECT
        *,

        /* ============================================================
           CURRENCY
           ============================================================ */

        CASE
            WHEN UPPER(spend_raw) LIKE '%EUR%'
                THEN 'EUR'

            ELSE 'FCFA'
        END AS spend_currency,

        /* ============================================================
           NUMERIC AMOUNT
           ============================================================ */

        TRY_CAST(
            REPLACE(
                REGEXP_REPLACE(
                    REPLACE(
                        REPLACE(
                            UPPER(spend_raw),
                            'FCFA',
                            ''
                        ),
                        'EUR',
                        ''
                    ),
                    '[^0-9,.-]',
                    '',
                    'g'
                ),
                ',',
                '.'
            ) AS DOUBLE
        ) AS spend_amount

    FROM normalized_dates

)

SELECT

    /* ================================================================
       IDENTIFICATION
       ================================================================ */

    platform_normalized AS platform,

    platform_raw,

    campaign_name,

    campaign_name_raw,

    /* ================================================================
       DATES
       ================================================================ */

    date_start,

    date_end,

    date_start_raw,

    date_end_raw,

    DATE_TRUNC(
        'month',
        date_start
    )::DATE AS month,

    /* ================================================================
       SPEND
       ================================================================ */

    spend_raw,

    spend_currency,

    spend_amount,

    CASE
        WHEN spend_currency = 'EUR'
            THEN 655.0
        ELSE 1.0
    END AS fx_rate_to_fcfa,

    ROUND(
        CASE
            WHEN spend_currency = 'EUR'
                THEN spend_amount * 655.0
            ELSE spend_amount
        END,
        2
    ) AS spend_fcfa,

    /* ================================================================
       DIGITAL PERFORMANCE
       ================================================================ */

    impressions,

    clicks,

    /* ================================================================
       OBJECTIVE
       ================================================================ */

    objective_raw,

    objective_normalized,

    /* ================================================================
       DATA QUALITY FLAGS
       ================================================================ */

    date_start IS NULL AS date_start_parse_failed,

    date_end IS NULL AS date_end_parse_failed,

    spend_amount IS NULL AS spend_parse_failed,

    CASE
        WHEN date_start IS NOT NULL
         AND date_end IS NOT NULL
         AND date_start > date_end
            THEN TRUE
        ELSE FALSE
    END AS invalid_date_range,

    spend_currency = 'EUR' AS converted_from_eur,

    impressions IS NULL AS impressions_missing,

    clicks IS NULL AS clicks_missing

FROM parsed_spend