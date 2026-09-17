SELECT *
FROM {{ ref('int_campaign_normalized') }}
WHERE campaign_month IS NOT NULL
  AND campaign_month NOT BETWEEN
      DATE '2026-01-01'
      AND DATE '2026-06-01'