-- known_order_amount_fcfa ne doit contenir que des montants plausibles, et les
-- montants exclus doivent rester traçables (outlier_amount_fcfa).
WITH expected AS (

    SELECT
        DATE_TRUNC('month', received_at) AS month,
        SUM(COALESCE(amount_plausible_fcfa, 0)) AS plausible_total,
        SUM(CASE WHEN amount_outlier THEN amount_fcfa ELSE 0 END) AS outlier_total,
        COUNT_IF(amount_outlier) AS outlier_orders
    FROM {{ ref('int_whatsapp_order_quality') }}
    GROUP BY 1

)

SELECT
    m.month
FROM {{ ref('mart_whatsapp_monthly') }} AS m
JOIN expected AS e
    ON m.month = e.month
WHERE m.known_order_amount_fcfa <> e.plausible_total
   OR m.outlier_amount_fcfa <> e.outlier_total
   OR m.outlier_amount_orders <> e.outlier_orders
   OR m.delivered_known_amount_fcfa > m.known_order_amount_fcfa
