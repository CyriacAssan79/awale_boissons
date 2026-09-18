-- Chaque canal doit recevoir un budget positif (le socle d'instrumentation
-- garantit au moins 1 M FCFA, même pour les canaux les moins mesurés).
SELECT *
FROM {{ ref('mart_budget_recommendation_15m') }}
WHERE proposed_budget_fcfa IS NULL
   OR proposed_budget_fcfa <= 0
