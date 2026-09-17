SELECT *
FROM {{ ref('mart_decision_15m') }}
WHERE campaign_spend_fcfa < 0