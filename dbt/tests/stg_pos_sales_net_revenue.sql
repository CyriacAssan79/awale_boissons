SELECT *
FROM {{ ref('stg_pos_sales_daily') }}
WHERE net_revenue_fcfa != revenue_fcfa