SELECT *
FROM {{ ref('int_whatsapp_items') }}
WHERE quantity <= 0