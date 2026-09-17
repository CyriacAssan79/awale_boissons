SELECT *
FROM {{ ref('mart_decision_15m') }}
WHERE spend_share < 0
   OR spend_share > 1
   OR planned_share < 0
   OR planned_share > 1