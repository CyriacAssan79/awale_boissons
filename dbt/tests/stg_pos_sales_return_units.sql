SELECT *
FROM {{ ref('stg_pos_sales_daily') }}
WHERE return_units > 0