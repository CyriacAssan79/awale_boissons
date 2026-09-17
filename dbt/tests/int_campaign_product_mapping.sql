SELECT *
FROM {{ ref('int_campaign_normalized') }}
WHERE product IS NOT NULL
  AND product NOT IN (
      'bissap',
      'gingembre',
      'bouye'
  )