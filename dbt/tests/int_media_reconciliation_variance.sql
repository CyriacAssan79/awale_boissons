SELECT *
FROM {{ ref('int_media_reconciliation') }}
WHERE
    source_coverage = 'both_available'
    AND campaign_vs_invoiced_variance_fcfa IS NULL