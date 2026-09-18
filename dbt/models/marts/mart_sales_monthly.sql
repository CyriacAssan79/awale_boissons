{{ config(materialized='table') }}

WITH sales AS (

    SELECT
        sale_date,
        pos_id,
        pos_key,
        pos_name,
        commune,
        channel,
        units_sold,
        revenue_fcfa,
        gross_units,
        return_units,
        gross_revenue_fcfa,
        return_revenue_fcfa,
        net_revenue_fcfa
    FROM {{ ref('stg_pos_sales_daily') }}

),

calendar AS (

    SELECT
        sale_date,
        has_sales_data,
        is_missing_sales_day
    FROM {{ ref('int_sales_calendar') }}

),

monthly_sales AS (

    SELECT
        DATE_TRUNC('month', s.sale_date) AS month,

        SUM(s.units_sold) AS net_units_sold,
        SUM(s.revenue_fcfa) AS net_revenue_fcfa,

        SUM(s.gross_units) AS gross_units,
        SUM(s.gross_revenue_fcfa) AS gross_revenue_fcfa,

        SUM(s.return_units) AS return_units,
        SUM(s.return_revenue_fcfa) AS return_revenue_fcfa,

        -- Points de vente distincts : compté sur la clé canonique, pas sur
        -- pos_id (un magasin qui change d'identifiant compterait pour deux).
        COUNT(DISTINCT s.pos_key) AS active_pos,
        COUNT(DISTINCT s.pos_name) AS active_pos_names,
        COUNT(DISTINCT s.commune) AS active_communes,

        COUNT(DISTINCT s.sale_date) AS observed_sales_days

    FROM sales s

    GROUP BY
        DATE_TRUNC('month', s.sale_date)

),

calendar_summary AS (

    SELECT
        DATE_TRUNC('month', sale_date) AS month,

        COUNT(*) AS calendar_days,

        SUM(
            CASE
                WHEN has_sales_data THEN 1
                ELSE 0
            END
        ) AS days_with_sales_data,

        SUM(
            CASE
                WHEN is_missing_sales_day THEN 1
                ELSE 0
            END
        ) AS missing_sales_days

    FROM calendar

    GROUP BY
        DATE_TRUNC('month', sale_date)

)

SELECT
    m.month,

    m.net_units_sold,
    m.net_revenue_fcfa,

    m.gross_units,
    m.gross_revenue_fcfa,

    m.return_units,
    m.return_revenue_fcfa,

    m.active_pos,
    m.active_pos_names,
    m.active_communes,

    m.observed_sales_days,

    c.calendar_days,
    c.days_with_sales_data,
    c.missing_sales_days,

    CASE
        WHEN c.days_with_sales_data > 0
        THEN m.net_revenue_fcfa / c.days_with_sales_data
        ELSE NULL
    END AS avg_revenue_per_observed_day,

    CASE
        WHEN m.gross_revenue_fcfa <> 0
        THEN ABS(m.return_revenue_fcfa)
             / m.gross_revenue_fcfa
        ELSE NULL
    END AS return_rate_revenue

FROM monthly_sales m

LEFT JOIN calendar_summary c
    ON m.month = c.month