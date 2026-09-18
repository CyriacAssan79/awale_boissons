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
    FROM {{ source('raw', 'raw_pos_sales_daily') }}

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

        /*
           Clé canonique du point de vente : nom sans accents, en minuscules,
           espaces normalisés. Le même magasin peut changer de pos_id et de
           casse d'un mois à l'autre (ex. POS014 "Kiosque Yopougon Ananeraie"
           puis POS103 "KIOSQUE YOPOUGON ANANERAIE" dès le 1er mai) : pos_id
           n'est donc PAS un identifiant stable, pos_key l'est. Normalisation
           exacte uniquement : aucune fusion approximative sans validation
           humaine (voir int_pos_dimension).
        */
        REGEXP_REPLACE(
            LOWER(STRIP_ACCENTS(TRIM(pos_name))),
            '\s+',
            ' ',
            'g'
        ) AS pos_key,

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

SELECT sale_date, pos_id, pos_name_raw, pos_name, pos_key, commune_raw, commune, channel_raw,
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