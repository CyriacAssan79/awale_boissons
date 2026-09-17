SELECT *
FROM {{ ref('stg_whatsapp_orders') }}
WHERE status NOT IN (
    'delivered',
    'cancelled',
    'pending'
)