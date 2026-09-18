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
           CAMPAIGN MONTH (numéro de mois lu dans le nom de campagne)

           Seul le NUMÉRO du mois est lu dans le nom ; l'année est celle de
           date_start (voir CTE dated). Aucune année n'est écrite en dur.
           Les mois 1 à 6 conservent leurs motifs historiques ; les mois 7 à
           12 utilisent des bornes de mot pour éviter les faux positifs
           ("innovation", "decouverte", ...).
           ============================================================ */

        CASE

            WHEN campaign_name_search LIKE '%janvier%'
                OR campaign_name_search LIKE '%jan%'
                THEN 1

            WHEN campaign_name_search LIKE '%février%'
                OR campaign_name_search LIKE '%fevrier%'
                OR campaign_name_search LIKE '%fevr%'
                OR campaign_name_search LIKE '%fev%'
                THEN 2

            WHEN campaign_name_search LIKE '%mars%'
                THEN 3

            WHEN campaign_name_search LIKE '%avril%'
                OR campaign_name_search LIKE '%avr%'
                THEN 4

            WHEN campaign_name_search LIKE '%mai%'
                THEN 5

            WHEN campaign_name_search LIKE '%juin%'
                OR campaign_name_search LIKE '%jun%'
                THEN 6

            /* formats du type avril26 / mai26 / mars26 */
            WHEN REGEXP_MATCHES(
                campaign_name_search,
                '(^| )jan([0-9]{2})?($| )'
            )
                THEN 1

            WHEN REGEXP_MATCHES(
                campaign_name_search,
                '(^| )fevr?([0-9]{2})?($| )'
            )
                THEN 2

            WHEN REGEXP_MATCHES(
                campaign_name_search,
                '(^| )mar([0-9]{2})?($| )'
            )
                THEN 3

            WHEN REGEXP_MATCHES(
                campaign_name_search,
                '(^| )avr([0-9]{2})?($| )'
            )
                THEN 4

            WHEN REGEXP_MATCHES(
                campaign_name_search,
                '(^| )mai([0-9]{2})?($| )'
            )
                THEN 5

            WHEN REGEXP_MATCHES(
                campaign_name_search,
                '(^| )juin([0-9]{2})?($| )'
            )
                THEN 6

            /* mois 7 à 12 : mots entiers, avec ou sans suffixe d'année */
            WHEN REGEXP_MATCHES(
                campaign_name_search,
                '(^| )(juillet|juil|jul)([0-9]{2})?($| )'
            )
                THEN 7

            WHEN REGEXP_MATCHES(
                campaign_name_search,
                '(^| )(août|aout|aou)([0-9]{2})?($| )'
            )
                THEN 8

            WHEN REGEXP_MATCHES(
                campaign_name_search,
                '(^| )(septembre|sept|sep)([0-9]{2})?($| )'
            )
                THEN 9

            WHEN REGEXP_MATCHES(
                campaign_name_search,
                '(^| )(octobre|oct)([0-9]{2})?($| )'
            )
                THEN 10

            WHEN REGEXP_MATCHES(
                campaign_name_search,
                '(^| )(novembre|nov)([0-9]{2})?($| )'
            )
                THEN 11

            WHEN REGEXP_MATCHES(
                campaign_name_search,
                '(^| )(décembre|decembre|dec)([0-9]{2})?($| )'
            )
                THEN 12

            ELSE NULL

        END AS campaign_month_number

    FROM text_normalized

),

dated AS (

    SELECT
        *,

        CASE
            WHEN campaign_month_number IS NOT NULL
                THEN MAKE_DATE(
                    CAST(EXTRACT(YEAR FROM date_start) AS INTEGER),
                    campaign_month_number,
                    1
                )
        END AS campaign_month

    FROM parsed

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

FROM dated
