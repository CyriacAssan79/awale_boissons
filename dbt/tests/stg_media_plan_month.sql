SELECT *
FROM {{ ref('stg_media_plan') }}
WHERE month_date IS NULL