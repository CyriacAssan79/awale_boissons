SELECT *
FROM {{ ref('stg_social_comments') }}
WHERE like_count < 0