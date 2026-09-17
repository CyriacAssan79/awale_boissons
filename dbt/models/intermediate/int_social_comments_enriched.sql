{{ config(materialized='table') }}

WITH comments AS (

    SELECT
        comment_id,
        platform,
        published_at,
        author_handle,
        comment_text,
        like_count,
        reply_to_id
    FROM {{ ref('stg_social_comments') }}

),

predictions AS (

    SELECT
        comment_id,
        language_model,
        sentiment_model,
        theme_model,
        product_model,
        is_spam_model,
        model_used,
        rules_complete
    FROM {{ source('raw', 'raw_social_comments_predictions_v2') }}

)

SELECT
    c.comment_id,
    c.platform,
    c.published_at,
    c.author_handle,
    c.comment_text,
    c.like_count,
    c.reply_to_id,

    p.language_model,
    p.sentiment_model,
    p.theme_model,
    p.product_model,
    p.is_spam_model,

    p.model_used,
    p.rules_complete

FROM comments AS c

LEFT JOIN predictions AS p
    ON c.comment_id = p.comment_id