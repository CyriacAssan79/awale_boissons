-- Le budget de test proposé doit toujours totaliser exactement le budget
-- paramétré (var total_test_budget_fcfa), quel que soit le résultat du calcul
-- d'allocation.
SELECT
    SUM(proposed_budget_fcfa) AS total_proposed_fcfa
FROM {{ ref('mart_budget_recommendation_15m') }}
HAVING ABS(SUM(proposed_budget_fcfa) - {{ var('total_test_budget_fcfa') }}) > 1
