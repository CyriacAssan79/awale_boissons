-- La quantité extraite doit égaler le multiplicateur écrit dans le texte :
--   "6x BIS-1L" / "6 x bis-1l" -> 6   |   "2 bissap 1L" -> 2
-- (bug corrigé : "Nx SKU" était compté 1.)
SELECT
    whatsapp_row_id,
    segment,
    quantity
FROM {{ ref('int_whatsapp_items') }}
WHERE (
        REGEXP_MATCHES(segment, '^\s*[0-9]+\s*x\s*[a-z]')
        AND quantity <> CAST(REGEXP_EXTRACT(segment, '^\s*([0-9]+)\s*x', 1) AS INTEGER)
      )
   OR (
        REGEXP_MATCHES(segment, '^\s*[0-9]+\s+(bissap|gingembre|bouye)')
        AND quantity <> CAST(REGEXP_EXTRACT(segment, '^\s*([0-9]+)\s+', 1) AS INTEGER)
      )
