SELECT *
FROM {{ ref('mart_sales_monthly') }}
WHERE net_revenue_fcfa < 0