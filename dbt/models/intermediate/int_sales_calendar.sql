-- ======================================================================
-- Calendrier des ventes : un jour = une ligne, du 1er jour du premier mois
-- observé au DERNIER jour du dernier mois observé dans stg_pos_sales_daily.
--
-- La borne est déduite des données, jamais écrite en dur : un nouveau mois
-- de ventes étend automatiquement le calendrier. Le calendrier va jusqu'à la
-- fin du mois pour qu'un mois partiellement livré (ex. 7 jours reçus sur 31)
-- apparaisse avec ses jours manquants, au lieu de passer pour un mois
-- complet.
-- ======================================================================

WITH bounds AS (

    SELECT
        DATE_TRUNC('month', MIN(sale_date))::DATE AS first_day,

        (
            DATE_TRUNC('month', MAX(sale_date))
            + INTERVAL '1 month'
            - INTERVAL '1 day'
        )::DATE AS last_day

    FROM {{ ref('stg_pos_sales_daily') }}

),

calendar AS (

    SELECT
        CAST(day AS DATE) AS sale_date

    FROM bounds,

    generate_series(
        bounds.first_day,
        bounds.last_day,
        INTERVAL '1 day'
    ) AS t(day)

),

sales_dates AS (

    SELECT DISTINCT
        sale_date

    FROM {{ ref('stg_pos_sales_daily') }}

),

calendar_status AS (

    SELECT

        c.sale_date,

        DATE_TRUNC(
            'month',
            c.sale_date
        )::DATE AS month,

        DATE_TRUNC(
            'week',
            c.sale_date
        )::DATE AS week_start,

        CASE
            WHEN s.sale_date IS NOT NULL
                THEN TRUE
            ELSE FALSE
        END AS has_sales_data

    FROM calendar c

    LEFT JOIN sales_dates s
        ON c.sale_date = s.sale_date

)

SELECT

    sale_date,

    month,

    week_start,

    has_sales_data,

    NOT has_sales_data AS is_missing_sales_day

FROM calendar_status
