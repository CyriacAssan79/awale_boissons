SELECT *
FROM {{ ref('stg_media_plan') }}
WHERE
    invoiced_fcfa IS NOT NULL
    AND variance_fcfa != invoiced_fcfa - planned_budget_fcfa