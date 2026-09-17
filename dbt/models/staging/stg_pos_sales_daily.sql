WITH source_data AS (

    SELECT
        sale_date,
        pos_id,
        pos_name,
        commune,
        channel,
        product_sku,
        units_sold,
        revenue_fcfa
    FROM "awale"."main"."raw_pos_sales_daily"

),

cleaned AS (

    SELECT

        /* ============================================================
           DATE
           ============================================================ */

        CAST(sale_date AS DATE) AS sale_date,

        /* ============================================================
           POS
           ============================================================ */

        TRIM(pos_id) AS pos_id,

        TRIM(pos_name) AS pos_name_raw,

        TRIM(pos_name) AS pos_name,

        /* ============================================================
           COMMUNE
           ============================================================ */

        TRIM(commune) AS commune_raw,

        CASE
            WHEN LOWER(TRIM(commune)) = 'cocody'
                THEN 'Cocody'

            WHEN LOWER(TRIM(commune)) = 'yopougon'
                THEN 'Yopougon'

            WHEN LOWER(TRIM(commune)) = 'marcory'
                THEN 'Marcory'

            WHEN LOWER(TRIM(commune)) = 'treichville'
                THEN 'Treichville'

            WHEN LOWER(TRIM(commune)) = 'port-bouet'
                THEN 'Port-Bouet'

            ELSE TRIM(commune)
        END AS commune,

        /* ============================================================
           CHANNEL
           ============================================================ */

        TRIM(channel) AS channel_raw,

        CASE
            WHEN LOWER(TRIM(channel)) = 'retail'
                THEN 'retail'

            WHEN LOWER(TRIM(channel)) = 'delivery'
                THEN 'delivery'

            WHEN LOWER(TRIM(channel)) = 'ecommerce'
                THEN 'ecommerce'

            ELSE LOWER(TRIM(channel))
        END AS channel,

        /* ============================================================
           PRODUCT
           ============================================================ */

        TRIM(product_sku) AS product_sku,

        /* ============================================================
           ORIGINAL METRICS
           ============================================================ */

        units_sold,

        revenue_fcfa

    FROM source_data

)

SELECT sale_date, pos_id, pos_name_raw, pos_name, commune_raw, commune, channel_raw,
    channel, product_sku, units_sold, revenue_fcfa,

    /* ================================================================
       RETURN FLAGS
       ================================================================ */

    (units_sold < 0 OR revenue_fcfa < 0 ) AS is_return,

    /* ================================================================
       GROSS SALES
       ================================================================ */

    CASE
        WHEN units_sold > 0
            THEN units_sold
        ELSE 0
    END AS gross_units,

    CASE
        WHEN units_sold < 0
            THEN units_sold
        ELSE 0
    END AS return_units,

    CASE
        WHEN revenue_fcfa > 0
            THEN revenue_fcfa
        ELSE 0
    END AS gross_revenue_fcfa,

    CASE
        WHEN revenue_fcfa < 0
            THEN revenue_fcfa
        ELSE 0
    END AS return_revenue_fcfa,

    /* ================================================================
       NET
       ================================================================ */

    COALESCE(revenue_fcfa, 0) AS net_revenue_fcfa

FROM cleaned