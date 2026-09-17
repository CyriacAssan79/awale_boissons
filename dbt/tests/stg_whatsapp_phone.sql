SELECT *
FROM {{ ref('stg_whatsapp_orders') }}
WHERE customer_phone IS NULL