-- Chaque commentaire doit avoir sa prédiction IA, complète. La jointure est un
-- LEFT JOIN : un commentaire sans prédiction ressortirait sinon avec des NULL,
-- silencieusement. Ce test rend visible l'écart "volume source != volume prédit".
SELECT
    comment_id,
    language_model,
    sentiment_model,
    theme_model,
    product_model,
    is_spam_model
FROM {{ ref('int_social_comments_enriched') }}
WHERE language_model IS NULL
   OR sentiment_model IS NULL
   OR theme_model IS NULL
   OR product_model IS NULL
   OR is_spam_model IS NULL
