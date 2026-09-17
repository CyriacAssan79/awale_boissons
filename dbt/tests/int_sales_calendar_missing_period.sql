WITH missing_days AS (

    SELECT sale_date
    FROM {{ ref('int_sales_calendar') }}
    WHERE is_missing_sales_day

)

SELECT *
FROM missing_days
WHERE sale_date NOT BETWEEN DATE '2026-04-13' AND DATE '2026-04-26'