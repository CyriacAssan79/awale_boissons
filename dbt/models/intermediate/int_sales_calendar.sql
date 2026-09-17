WITH calendar AS (

    SELECT
        CAST(day AS DATE) AS sale_date

    FROM generate_series(
        DATE '2026-01-01',
        DATE '2026-06-30',
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