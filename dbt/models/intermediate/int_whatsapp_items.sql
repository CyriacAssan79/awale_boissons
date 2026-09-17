WITH orders AS (

    SELECT
        whatsapp_row_id,
        order_ref,
        received_at,
        customer_phone,
        items_text,
        amount_fcfa,
        status,
        delivery_zone
    FROM {{ ref('stg_whatsapp_orders') }}

),

cleaned AS (

    SELECT
        *,
        LOWER(
            REGEXP_REPLACE(
                REGEXP_REPLACE(
                    items_text,
                    '\([^)]*\)',
                    '',
                    'g'
                ),
                '\s+',
                ' ',
                'g'
            )
        ) AS items_normalized

    FROM orders

),

segments AS (

    SELECT
        whatsapp_row_id,
        order_ref,
        received_at,
        customer_phone,
        items_text,
        amount_fcfa,
        status,
        delivery_zone,

        TRIM(segment) AS segment

    FROM cleaned,

    UNNEST(
        REGEXP_SPLIT_TO_ARRAY(
            REGEXP_REPLACE(
                items_normalized,
                '\s+et\s+',
                '+',
                'g'
            ),
            '\+'
        )
    ) AS t(segment)

),

parsed AS (

    SELECT

        whatsapp_row_id,
        order_ref,
        received_at,
        customer_phone,
        items_text,
        amount_fcfa,
        status,
        delivery_zone,
        segment,

        /*
            Détection du produit.

            Supporte :
            - bissap
            - gingembre
            - bouye
            - BIS-1L
            - BIS-33CL
        */
        CASE
            WHEN REGEXP_MATCHES(
                segment,
                'bissap|bis[- ]?1l|bis[- ]?33\s*cl'
            )
                THEN 'bissap'

            WHEN REGEXP_MATCHES(
                segment,
                'gingembre'
            )
                THEN 'gingembre'

            WHEN REGEXP_MATCHES(
                segment,
                'bouye'
            )
                THEN 'bouye'

            ELSE NULL
        END AS product,

        /*
            Détection du format.

            Supporte :
            - 1L
            - 1 L
            - 33cl
            - 33 cl
        */
        CASE
            WHEN REGEXP_MATCHES(
                segment,
                '1\s*l'
            )
                THEN '1L'

            WHEN REGEXP_MATCHES(
                segment,
                '33\s*cl'
            )
                THEN '33cl'

            ELSE NULL
        END AS format,

        /*
            Quantité.

            Supporte :
            - 2 bissap
            - 2 gingembre
            - 6x BIS-1L
            - 6 x BIS-1L
            - 6 bouye
        */
        CASE
            WHEN REGEXP_MATCHES(segment, 'x[0-9]+$')
                THEN TRY_CAST(
                    REGEXP_EXTRACT(segment, 'x([0-9]+)$', 1)
                    AS INTEGER
                )

            WHEN REGEXP_MATCHES(segment, '^\s*[0-9]+\s+')
                THEN TRY_CAST(
                    REGEXP_EXTRACT(segment, '^\s*([0-9]+)\s+', 1)
                    AS INTEGER
                )

            ELSE 1
        END AS quantity,

    FROM segments

)

SELECT

    whatsapp_row_id,
    order_ref,
    received_at,
    customer_phone,
    items_text,
    amount_fcfa,
    status,
    delivery_zone,
    segment,
    product,
    format,
    quantity,

    /*
        Statut de parsing détaillé.
    */
    CASE
        WHEN product IS NOT NULL
            AND format IS NOT NULL
            THEN 'parsed'

        WHEN product IS NOT NULL
            AND format IS NULL
            THEN 'missing_format'

        ELSE 'unknown_product'
    END AS parse_status,

    /*
        Échec technique du parsing uniquement.
        Un format manquant n'est pas considéré comme
        un échec du produit ou de la quantité.
    */
    CASE
        WHEN product IS NULL
            THEN TRUE
        ELSE FALSE
    END AS parse_failed

FROM parsed