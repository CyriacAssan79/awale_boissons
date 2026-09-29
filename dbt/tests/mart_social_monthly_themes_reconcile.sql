-- Chaque commentaire non-spam doit être compté dans exactement un thème.
-- Un thème produit par le classifieur mais absent des colonnes du mart
-- (cas de product_question avant le 29/09/2026) ferait échouer ce test.
SELECT
    month,
    platform,
    non_spam_comments_count,
    taste_comments_count
    + price_comments_count
    + promotion_comments_count
    + availability_comments_count
    + packaging_comments_count
    + health_comments_count
    + delivery_comments_count
    + service_comments_count
    + product_question_comments_count
    + other_theme_comments_count AS themed_comments_count
FROM {{ ref('mart_social_monthly') }}
WHERE non_spam_comments_count <> (
    taste_comments_count
    + price_comments_count
    + promotion_comments_count
    + availability_comments_count
    + packaging_comments_count
    + health_comments_count
    + delivery_comments_count
    + service_comments_count
    + product_question_comments_count
    + other_theme_comments_count
)
