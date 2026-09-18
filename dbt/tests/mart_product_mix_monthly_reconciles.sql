-- Le mix produit doit se réconcilier avec mart_sales_monthly : mêmes unités et
-- même chiffre d'affaires nets, mois par mois. Sinon un SKU a été perdu ou compté
-- deux fois par la jointure avec la dimension produit.
WITH mix AS (

    SELECT
        month,
        SUM(net_units) AS net_units,
        SUM(net_revenue_fcfa) AS net_revenue_fcfa,
        SUM(gross_revenue_fcfa) AS gross_revenue_fcfa
    FROM {{ ref('mart_product_mix_monthly') }}
    GROUP BY month

)

SELECT
    s.month,
    s.net_units_sold,
    m.net_units,
    s.net_revenue_fcfa,
    m.net_revenue_fcfa
FROM {{ ref('mart_sales_monthly') }} AS s
FULL OUTER JOIN mix AS m
    ON s.month = m.month
WHERE s.month IS NULL
   OR m.month IS NULL
   OR s.net_units_sold <> m.net_units
   OR s.net_revenue_fcfa <> m.net_revenue_fcfa
   OR s.gross_revenue_fcfa <> m.gross_revenue_fcfa
