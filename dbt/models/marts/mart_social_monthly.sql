{{ config(materialized='table') }}

WITH base AS (

    SELECT
        DATE_TRUNC('month', published_at)::DATE AS month,
        platform,
        comment_id,
        like_count,
        language_model,
        sentiment_model,
        theme_model,
        product_model,
        is_spam_model,
        model_used,
        rules_complete
    FROM {{ ref('int_social_comments_enriched') }}

),

monthly AS (

    SELECT
        month,
        platform,

        COUNT(*) AS comments_count,

        COUNT(DISTINCT comment_id) AS unique_comments_count,

        SUM(COALESCE(like_count, 0)) AS likes_total,

        COUNT(*) FILTER (
            WHERE is_spam_model = true
        ) AS spam_comments_count,

        COUNT(*) FILTER (
            WHERE is_spam_model = false
        ) AS non_spam_comments_count,

        COUNT(*) FILTER (
            WHERE sentiment_model = 'positive'
            AND is_spam_model = false
        ) AS positive_comments_count,

        COUNT(*) FILTER (
            WHERE sentiment_model = 'negative'
            AND is_spam_model = false
        ) AS negative_comments_count,

        COUNT(*) FILTER (
            WHERE sentiment_model = 'neutral'
            AND is_spam_model = false
        ) AS neutral_comments_count,

        COUNT(*) FILTER (
            WHERE theme_model = 'taste'
            AND is_spam_model = false
        ) AS taste_comments_count,

        COUNT(*) FILTER (
            WHERE theme_model = 'price'
            AND is_spam_model = false
        ) AS price_comments_count,

        COUNT(*) FILTER (
            WHERE theme_model = 'promotion'
            AND is_spam_model = false
        ) AS promotion_comments_count,

        COUNT(*) FILTER (
            WHERE theme_model = 'availability'
            AND is_spam_model = false
        ) AS availability_comments_count,

        COUNT(*) FILTER (
            WHERE theme_model = 'packaging'
            AND is_spam_model = false
        ) AS packaging_comments_count,

        COUNT(*) FILTER (
            WHERE theme_model = 'health'
            AND is_spam_model = false
        ) AS health_comments_count,

        COUNT(*) FILTER (
            WHERE theme_model = 'delivery'
            AND is_spam_model = false
        ) AS delivery_comments_count,

        COUNT(*) FILTER (
            WHERE theme_model = 'service'
            AND is_spam_model = false
        ) AS service_comments_count,

        COUNT(*) FILTER (
            WHERE theme_model = 'other'
            AND is_spam_model = false
        ) AS other_theme_comments_count,

        COUNT(*) FILTER (
            WHERE product_model = 'bissap'
            AND is_spam_model = false
        ) AS bissap_comments_count,

        COUNT(*) FILTER (
            WHERE product_model = 'gingembre'
            AND is_spam_model = false
        ) AS gingembre_comments_count,

        COUNT(*) FILTER (
            WHERE product_model = 'bouye'
            AND is_spam_model = false
        ) AS bouye_comments_count,

        COUNT(*) FILTER (
            WHERE product_model = 'multiple'
            AND is_spam_model = false
        ) AS multiple_product_comments_count,

        COUNT(*) FILTER (
            WHERE product_model = 'unknown'
            AND is_spam_model = false
        ) AS unknown_product_comments_count,

        COUNT(*) FILTER (
            WHERE product_model = 'none'
            AND is_spam_model = false
        ) AS no_product_comments_count,

        COUNT(*) FILTER (
            WHERE model_used = true
        ) AS model_used_count,

        COUNT(*) FILTER (
            WHERE rules_complete = true
        ) AS rules_complete_count

    FROM base

    GROUP BY
        month,
        platform

)

SELECT
    *,
    
    ROUND(
        100.0 * positive_comments_count
        / NULLIF(non_spam_comments_count, 0),
        1
    ) AS positive_share_pct,

    ROUND(
        100.0 * negative_comments_count
        / NULLIF(non_spam_comments_count, 0),
        1
    ) AS negative_share_pct,

    ROUND(
        100.0 * neutral_comments_count
        / NULLIF(non_spam_comments_count, 0),
        1
    ) AS neutral_share_pct,

    ROUND(
        100.0 * spam_comments_count
        / NULLIF(comments_count, 0),
        1
    ) AS spam_share_pct,

    ROUND(
        100.0 * model_used_count
        / NULLIF(comments_count, 0),
        1
    ) AS model_used_share_pct,

    ROUND(
        100.0 * rules_complete_count
        / NULLIF(comments_count, 0),
        1
    ) AS rules_complete_share_pct

FROM monthly