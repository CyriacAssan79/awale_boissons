SELECT *
FROM {{ ref('mart_channel_evidence') }}
WHERE impressions < 0
   OR clicks < 0