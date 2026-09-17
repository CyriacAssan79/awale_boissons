SELECT *
FROM {{ ref('mart_channel_performance_monthly') }}
WHERE campaign_spend_fcfa < 0