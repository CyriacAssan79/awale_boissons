-- Cohérence des compteurs et des drapeaux de réachat :
--   is_repeat_customer            = au moins 2 commandes LIVRÉES
--   is_repeat_customer_any_status = au moins 2 commandes, tous statuts
SELECT *
FROM {{ ref('mart_whatsapp_customers') }}
WHERE order_count < 1
   OR delivered_order_count > order_count
   OR has_delivered_order <> (delivered_order_count > 0)
   OR is_repeat_customer <> (delivered_order_count > 1)
   OR is_repeat_customer_any_status <> (order_count > 1)
