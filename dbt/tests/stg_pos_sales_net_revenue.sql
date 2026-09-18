-- Réconciliation : CA net = ventes brutes + retours (les retours sont négatifs),
-- et de même pour les unités.
SELECT *
FROM {{ ref('stg_pos_sales_daily') }}
WHERE net_revenue_fcfa <> gross_revenue_fcfa + return_revenue_fcfa
   OR units_sold <> gross_units + return_units
