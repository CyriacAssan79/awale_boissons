SELECT *
FROM {{ ref('int_sales_calendar') }}
WHERE sale_date < DATE '2026-01-01'
   OR sale_date > DATE '2026-06-30'