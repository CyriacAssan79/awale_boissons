-- Chaque canal du budget décidé (var test_budget_allocation_fcfa) doit
-- exister dans la recommandation : un nom mal orthographié (« Tiktok »)
-- serait sinon ignoré sans bruit.
{% set decided = var('test_budget_allocation_fcfa', {}) %}

{% if decided %}
SELECT t.channel
FROM (
    VALUES
    {% for channel in decided %}
        ('{{ channel }}'){% if not loop.last %},{% endif %}
    {% endfor %}
) AS t(channel)
LEFT JOIN {{ ref('mart_budget_recommendation_15m') }} AS r
    ON t.channel = r.channel
WHERE r.channel IS NULL
{% else %}
SELECT 1 WHERE FALSE
{% endif %}
