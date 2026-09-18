-- order_count doit toujours être positif et cohérent avec le flag de réachat.
SELECT *
FROM {{ ref('mart_whatsapp_customers') }}
WHERE order_count < 1
   OR (is_repeat_customer AND order_count < 2)
   OR (NOT is_repeat_customer AND order_count <> 1)
