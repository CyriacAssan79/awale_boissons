SELECT *
FROM {{ ref('mart_budget_allocation') }}
WHERE campaign_spend_fcfa < 0