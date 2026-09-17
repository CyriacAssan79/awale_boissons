SELECT *
FROM {{ ref('stg_pos_sales_daily') }}
WHERE gross_units < 0