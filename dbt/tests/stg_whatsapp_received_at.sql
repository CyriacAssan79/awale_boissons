SELECT *
FROM {{ ref('stg_whatsapp_orders') }}
WHERE received_at IS NULL