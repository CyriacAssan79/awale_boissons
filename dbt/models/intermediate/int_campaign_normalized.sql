WITH base AS (

    SELECT
        month,
        platform AS channel,
        campaign_name,
        campaign_name_raw,
        date_start,
        date_end,
        spend_fcfa,
        impressions,
        clicks,
        objective_normalized
    FROM {{ ref('stg_campaign_spend') }}

),

text_normalized AS (

    SELECT
        *,

        LOWER(
            REGEXP_REPLACE(
                campaign_name,
                '[^a-zA-Z0-9À-ÿ]+',
                ' ',
                'g'
            )
        ) AS campaign_name_search

    FROM base

),

parsed AS (

    SELECT
        *,

        /* ============================================================
           PRODUCT
           ============================================================ */

        CASE
            WHEN campaign_name_search LIKE '%bissap%'
                THEN 'bissap'

            WHEN campaign_name_search LIKE '%gingembre%'
                THEN 'gingembre'

            WHEN campaign_name_search LIKE '%bouye%'
                THEN 'bouye'

            ELSE NULL
        END AS product,

        /* ============================================================
           CAMPAIGN MONTH
           ============================================================ */

        CASE

            WHEN campaign_name_search LIKE '%janvier%'
                OR campaign_name_search LIKE '%jan%'
                THEN DATE '2026-01-01'

            WHEN campaign_name_search LIKE '%février%'
                OR campaign_name_search LIKE '%fevrier%'
                OR campaign_name_search LIKE '%fevr%'
                OR campaign_name_search LIKE '%fev%'
                THEN DATE '2026-02-01'

            WHEN campaign_name_search LIKE '%mars%'
                THEN DATE '2026-03-01'

            WHEN campaign_name_search LIKE '%avril%'
                OR campaign_name_search LIKE '%avr%'
                THEN DATE '2026-04-01'

            WHEN campaign_name_search LIKE '%mai%'
                THEN DATE '2026-05-01'

            WHEN campaign_name_search LIKE '%juin%'
                OR campaign_name_search LIKE '%jun%'
                THEN DATE '2026-06-01'

            /* formats du type avril26 / mai26 / mars26 */
            WHEN REGEXP_MATCHES(
                campaign_name_search,
                '(^| )jan(26)?($| )'
            )
                THEN DATE '2026-01-01'

            WHEN REGEXP_MATCHES(
                campaign_name_search,
                '(^| )fevr?(26)?($| )'
            )
                THEN DATE '2026-02-01'

            WHEN REGEXP_MATCHES(
                campaign_name_search,
                '(^| )mar(26)?($| )'
            )
                THEN DATE '2026-03-01'

            WHEN REGEXP_MATCHES(
                campaign_name_search,
                '(^| )avr(26)?($| )'
            )
                THEN DATE '2026-04-01'

            WHEN REGEXP_MATCHES(
                campaign_name_search,
                '(^| )mai26($| )'
            )
                THEN DATE '2026-05-01'

            WHEN REGEXP_MATCHES(
                campaign_name_search,
                '(^| )juin26($| )'
            )
                THEN DATE '2026-06-01'

            ELSE NULL

        END AS campaign_month

    FROM text_normalized

)

SELECT

    month,

    channel,

    campaign_name,

    campaign_name_raw,

    date_start,

    date_end,

    product,

    campaign_month,

    objective_normalized AS objective,

    spend_fcfa,

    impressions,

    clicks,

    CASE
        WHEN product IS NOT NULL
            THEN 'parsed'
        ELSE 'not_found'
    END AS product_parse_status,

    CASE
        WHEN campaign_month IS NOT NULL
            THEN 'parsed'
        ELSE 'not_found'
    END AS campaign_month_parse_status,

    CASE
        WHEN product IS NULL
            THEN TRUE
        ELSE FALSE
    END AS product_parse_failed,

    CASE
        WHEN campaign_month IS NULL
            THEN TRUE
        ELSE FALSE
    END AS campaign_month_parse_failed

FROM parsed