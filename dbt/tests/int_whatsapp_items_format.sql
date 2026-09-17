SELECT *
FROM {{ ref('int_whatsapp_items') }}
WHERE format IS NOT NULL
  AND format NOT IN (
      '1L',
      '33cl'
  )