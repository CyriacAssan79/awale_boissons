{{ config(materialized='table') }}

-- ======================================================================
-- Mix produit des ventes POS : 1 ligne = 1 mois x 1 SKU.
--
-- Répond à : produits les plus vendus en volume, en chiffre d'affaires, et
-- évolution mensuelle par produit. Ventes brutes, retours et net restent
-- séparés. Se réconcilie avec mart_sales_monthly (voir le test
-- mart_product_mix_monthly_reconciles).
--
-- Lecture : les mois où month_missing_sales_days > 0 sont incomplets (jours de
-- ventes absents) ; leurs volumes ne se comparent pas à ceux d'un mois complet.
-- Le POS ne couvre pas les commandes WhatsApp (voir mart_whatsapp_monthly).
-- ======================================================================

WITH sales AS (

    SELECT
        DATE_TRUNC('month', sale_date)::DATE AS month,
        product_sku,

        SUM(gross_units) AS gross_units,
        SUM(return_units) AS return_units,
        SUM(units_sold) AS net_units,

        SUM(gross_revenue_fcfa) AS gross_revenue_fcfa,
        SUM(return_revenue_fcfa) AS return_revenue_fcfa,
        SUM(net_revenue_fcfa) AS net_revenue_fcfa

    FROM {{ ref('stg_pos_sales_daily') }}

    GROUP BY 1, 2

),

coverage AS (

    SELECT
        month,
        missing_sales_days
    FROM {{ ref('mart_sales_monthly') }}

)

SELECT
    s.month,

    d.product,
    d.format,
    s.product_sku,
    d.volume_litres,

    s.gross_units,
    s.return_units,
    s.net_units,

    s.gross_revenue_fcfa,
    s.return_revenue_fcfa,
    s.net_revenue_fcfa,

    -- Part du chiffre d'affaires net du mois (tous SKU confondus).
    s.net_revenue_fcfa
        / NULLIF(SUM(s.net_revenue_fcfa) OVER (PARTITION BY s.month), 0)
        AS revenue_share_of_month,

    s.net_units * d.volume_litres AS net_litres,

    -- Prix moyen observé par unité et par litre (net des retours).
    s.net_revenue_fcfa / NULLIF(s.net_units, 0) AS avg_net_price_per_unit_fcfa,

    s.net_revenue_fcfa
        / NULLIF(s.net_units * d.volume_litres, 0)
        AS net_revenue_per_litre_fcfa,

    c.missing_sales_days AS month_missing_sales_days

FROM sales AS s

LEFT JOIN {{ ref('int_product_dimension') }} AS d
    ON s.product_sku = d.product_sku

LEFT JOIN coverage AS c
    ON s.month = c.month
