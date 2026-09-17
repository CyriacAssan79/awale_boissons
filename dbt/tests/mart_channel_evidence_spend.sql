SELECT *
FROM {{ ref('mart_channel_evidence') }}
WHERE campaign_spend_fcfa < 0