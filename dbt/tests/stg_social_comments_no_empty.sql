SELECT *
FROM {{ ref('stg_social_comments') }}
WHERE is_empty_comment