WITH source_data AS (

    SELECT
        comment_id,
        platform,
        post_id,
        published_at,
        author_handle,
        comment_text,
        like_count,
        reply_to_id
    FROM {{ source('raw', 'raw_social_comments') }}

),

with_duplicate_info AS (

    SELECT
        *,
        COUNT(*) OVER (
            PARTITION BY
                comment_id,
                platform,
                post_id,
                published_at,
                author_handle,
                comment_text,
                like_count,
                reply_to_id
        ) AS exact_duplicate_count,

        ROW_NUMBER() OVER (
            PARTITION BY
                comment_id,
                platform,
                post_id,
                published_at,
                author_handle,
                comment_text,
                like_count,
                reply_to_id
            ORDER BY comment_id
        ) AS duplicate_row_number

    FROM source_data

),

deduplicated AS (

    SELECT *
    FROM with_duplicate_info
    WHERE duplicate_row_number = 1

)

SELECT

    /* ============================================================
       IDENTIFIERS
       ============================================================ */

    TRIM(comment_id) AS comment_id,

    TRIM(post_id) AS post_id,

    TRIM(author_handle) AS author_handle,

    /* ============================================================
       PLATFORM
       ============================================================ */

    TRIM(platform) AS platform_raw,

    CASE
        WHEN LOWER(TRIM(platform)) = 'instagram'
            THEN 'Instagram'

        WHEN LOWER(TRIM(platform)) = 'facebook'
            THEN 'Facebook'

        WHEN LOWER(TRIM(platform)) = 'tiktok'
            THEN 'TikTok'

        ELSE TRIM(platform)

    END AS platform,

    /* ============================================================
       DATE
       ============================================================ */

    published_at,

    CAST(published_at AS DATE) AS published_date,

    DATE_TRUNC(
        'month',
        published_at
    )::DATE AS month,

    /* ============================================================
       TEXT
       ============================================================ */

    TRIM(comment_text) AS comment_text,

    LENGTH(TRIM(comment_text)) AS comment_length,

    /* ============================================================
       ENGAGEMENT
       ============================================================ */

    like_count,

    /* ============================================================
       REPLY
       ============================================================ */

    reply_to_id,

    reply_to_id IS NOT NULL AS is_reply,

    /* ============================================================
       DUPLICATE / QUALITY
       ============================================================ */

    exact_duplicate_count > 1 AS was_exact_duplicate,

    TRIM(comment_text) = '' AS is_empty_comment

FROM deduplicated