SELECT *
FROM {{ ref('stg_media_plan') }}
WHERE planned_budget_fcfa < 0