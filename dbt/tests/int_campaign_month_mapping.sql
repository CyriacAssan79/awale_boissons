-- Le mois lu dans le nom de campagne doit correspondre au mois de date_start.
-- Un écart signale une faute de saisie dans le nom ou dans la date.
SELECT
    campaign_name,
    month,
    campaign_month
FROM {{ ref('int_campaign_normalized') }}
WHERE campaign_month IS NOT NULL
  AND campaign_month <> month
