SELECT *
FROM {{ ref('int_whatsapp_items') }}
WHERE product IS NOT NULL
  AND product NOT IN (
      'bissap',
      'gingembre',
      'bouye'
  )