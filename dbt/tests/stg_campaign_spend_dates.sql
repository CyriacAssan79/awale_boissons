SELECT
    date_start_raw,
    date_end_raw,
    date_start,
    date_end,
    campaign_name,
    platform
FROM stg_campaign_spend
WHERE date_start IS NULL
   OR date_end IS NULL