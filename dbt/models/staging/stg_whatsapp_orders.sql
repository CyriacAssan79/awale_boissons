WITH source_data AS (

    SELECT
        order_ref,
        received_at,
        customer_phone,
        items_text,
        amount_fcfa,
        delivery_zone,
        status
    FROM {{ source('raw', 'raw_whatsapp_orders') }}

),

with_metadata AS (

    SELECT
        *,
        COUNT(*) OVER (
            PARTITION BY order_ref
        ) AS order_ref_occurrences,

        ROW_NUMBER() OVER () AS whatsapp_row_id

    FROM source_data

),

cleaned AS (

    SELECT

        /* ============================================================
           TECHNICAL ID
           ============================================================ */

        whatsapp_row_id,

        /* ============================================================
           ORDER
           ============================================================ */

        TRIM(order_ref) AS order_ref,

        order_ref_occurrences > 1 AS order_ref_repeated,

        /* ============================================================
           DATE
           ============================================================ */

        TRIM(received_at) AS received_at_raw,

        COALESCE(

            TRY_STRPTIME(
                TRIM(received_at),
                '%Y-%m-%d %H:%M'
            ),

            TRY_STRPTIME(
                TRIM(received_at),
                '%d/%m/%Y %H:%M'
            ),

            TRY_STRPTIME(
                TRIM(received_at),
                '%Y-%m-%d'
            ),

            TRY_STRPTIME(
                TRIM(received_at),
                '%d/%m/%Y'
            )

        ) AS received_at,

        /* ============================================================
           PHONE
           ============================================================ */

        TRIM(customer_phone) AS customer_phone_raw,

        /* On retire espaces et caractères non numériques */
        REGEXP_REPLACE(
            TRIM(customer_phone),
            '[^0-9]',
            '',
            'g'
        ) AS phone_digits,

        /* ============================================================
           ITEMS
           ============================================================ */

        NULLIF(
            TRIM(items_text),
            ''
        ) AS items_text,

        /* ============================================================
           AMOUNT
           ============================================================ */

        amount_fcfa,

        /* ============================================================
           DELIVERY ZONE
           ============================================================ */

        TRIM(delivery_zone) AS delivery_zone_raw,

        LOWER(
            TRIM(delivery_zone)
        ) AS delivery_zone_normalized_raw,

        /* ============================================================
           STATUS
           ============================================================ */

        TRIM(status) AS status_raw

    FROM with_metadata

)

SELECT

    /* ================================================================
       ID
       ================================================================ */

    whatsapp_row_id,

    order_ref,

    order_ref_repeated,

    /* ================================================================
       DATE
       ================================================================ */

    received_at_raw,

    received_at,

    CAST(received_at AS DATE) AS order_date,

    DATE_TRUNC(
        'month',
        received_at
    )::DATE AS month,

    /* ================================================================
       PHONE
       ================================================================ */

    customer_phone_raw,

    CASE

        WHEN LENGTH(phone_digits) = 10
            THEN '+225' || phone_digits

        WHEN LENGTH(phone_digits) = 13
             AND LEFT(phone_digits, 3) = '225'
            THEN '+' || phone_digits

        ELSE NULL

    END AS customer_phone,

    /* ================================================================
       ORDER ITEMS
       ================================================================ */

    items_text,

    /* ================================================================
       AMOUNT
       ================================================================ */

    amount_fcfa,

    amount_fcfa IS NULL AS amount_missing,

    /* ================================================================
       DELIVERY ZONE
       ================================================================ */

    delivery_zone_raw,

    delivery_zone_normalized_raw AS delivery_zone,

    /* ================================================================
       STATUS
       ================================================================ */

    status_raw,

    CASE

        WHEN LOWER(TRIM(status_raw)) IN (
            'livré',
            'livree',
            'livrée',
            'livre'
        )
            THEN 'delivered'

        WHEN LOWER(TRIM(status_raw)) IN (
            'annulé',
            'annule',
            'annulée',
            'annulee'
        )
            THEN 'cancelled'

        WHEN LOWER(TRIM(status_raw)) IN (
            'en cours'
        )
            THEN 'pending'

        ELSE LOWER(TRIM(status_raw))

    END AS status,

    /* ================================================================
       QUALITY FLAGS
       ================================================================ */

    received_at IS NULL AS received_at_parse_failed,

    (
        CASE
            WHEN LENGTH(phone_digits) = 10
                THEN '+225' || phone_digits

            WHEN LENGTH(phone_digits) = 13
                 AND LEFT(phone_digits, 3) = '225'
                THEN '+' || phone_digits

            ELSE NULL
        END IS NULL
    ) AS phone_parse_failed

FROM cleaned