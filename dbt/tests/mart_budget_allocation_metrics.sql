SELECT *
FROM {{ ref('mart_budget_allocation') }}
WHERE clicks < 0
   OR impressions < 0