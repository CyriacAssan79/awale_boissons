SELECT *
FROM {{ ref('int_media_reconciliation') }}
WHERE
    source_coverage = 'both_available'
    AND invoiced_fcfa != 0
    AND campaign_to_invoiced_ratio IS NULL