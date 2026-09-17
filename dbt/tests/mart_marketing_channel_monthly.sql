SELECT *
FROM {{ ref('mart_marketing_channel_monthly') }}
WHERE campaign_spend_fcfa < 0