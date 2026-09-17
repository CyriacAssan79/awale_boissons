SELECT *
FROM {{ ref('mart_whatsapp_monthly') }}
WHERE orders <= 0