-- Le calendrier doit couvrir des mois entiers et toutes les dates de ventes
-- observées. Aucune borne n'est écrite en dur : elles viennent des données.
WITH cal AS (

    SELECT
        MIN(sale_date) AS first_day,
        MAX(sale_date) AS last_day
    FROM {{ ref('int_sales_calendar') }}

)

SELECT
    'sales_date_outside_calendar' AS issue,
    s.sale_date AS detail
FROM {{ ref('stg_pos_sales_daily') }} AS s
CROSS JOIN cal
WHERE s.sale_date < cal.first_day
   OR s.sale_date > cal.last_day

UNION ALL

SELECT
    'calendar_does_not_start_on_month_start' AS issue,
    first_day AS detail
FROM cal
WHERE first_day <> DATE_TRUNC('month', first_day)::DATE

UNION ALL

SELECT
    'calendar_does_not_end_on_month_end' AS issue,
    last_day AS detail
FROM cal
WHERE last_day <>
    (DATE_TRUNC('month', last_day) + INTERVAL '1 month' - INTERVAL '1 day')::DATE
