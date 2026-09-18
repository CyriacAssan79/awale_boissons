-- Cohérence entre le calendrier et les ventes : un jour signalé manquant ne
-- doit avoir aucune ligne de vente, et un jour non manquant en a au moins une.
-- (Remplace l'ancien test qui n'acceptait que la panne du 13 au 26 avril 2026 :
-- une panne future légitime doit être signalée, pas faire échouer le run.)
WITH pos_rows AS (

    SELECT
        sale_date,
        COUNT(*) AS n_rows
    FROM {{ ref('stg_pos_sales_daily') }}
    GROUP BY sale_date

)

SELECT
    c.sale_date,
    c.is_missing_sales_day,
    COALESCE(p.n_rows, 0) AS pos_rows
FROM {{ ref('int_sales_calendar') }} AS c
LEFT JOIN pos_rows AS p
    ON c.sale_date = p.sale_date
WHERE (c.is_missing_sales_day AND COALESCE(p.n_rows, 0) > 0)
   OR (NOT c.is_missing_sales_day AND COALESCE(p.n_rows, 0) = 0)
