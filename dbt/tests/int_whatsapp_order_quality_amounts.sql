-- Les montants WhatsApp invraisemblables sont signalés et exclus des totaux,
-- jamais corrigés ni supprimés :
--   * un montant flaggé aberrant ne peut pas être dans amount_plausible_fcfa
--   * un montant plausible ne dépasse jamais le seuil paramétré
--   * amount_missing et amount_outlier s'excluent mutuellement
SELECT *
FROM {{ ref('int_whatsapp_order_quality') }}
WHERE (amount_outlier AND amount_plausible_fcfa IS NOT NULL)
   OR amount_plausible_fcfa > {{ var('whatsapp_max_plausible_amount_fcfa') }}
   OR (amount_missing AND amount_outlier)
   OR (amount_fcfa IS NOT NULL AND NOT amount_outlier AND amount_plausible_fcfa IS NULL)
