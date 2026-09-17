SELECT *
FROM {{ ref('mart_channel_evidence') }}
WHERE spend_share < 0
   OR spend_share > 1