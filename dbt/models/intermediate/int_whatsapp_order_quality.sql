WITH items AS (

    SELECT
        whatsapp_row_id,
        order_ref,
        received_at,
        amount_fcfa,
        status,
        quantity,
        parse_status,
        product,
        format
    FROM {{ ref('int_whatsapp_items') }}

),

order_quality AS (

    SELECT
        whatsapp_row_id,
        MAX(order_ref) AS order_ref,
        MAX(received_at) AS received_at,
        MAX(amount_fcfa) AS amount_fcfa,
        MAX(status) AS status,

        MAX(amount_fcfa) IS NULL AS amount_missing,

        /*
            Montant invraisemblable (voir var whatsapp_max_plausible_amount_fcfa).
            Le montant brut est conservé dans amount_fcfa ; il n'est ni corrigé
            ni supprimé, seulement exclu des totaux via amount_plausible_fcfa.
        */
        COALESCE(
            MAX(amount_fcfa) > {{ var('whatsapp_max_plausible_amount_fcfa') }},
            FALSE
        ) AS amount_outlier,

        CASE
            WHEN MAX(amount_fcfa)
                 <= {{ var('whatsapp_max_plausible_amount_fcfa') }}
                THEN MAX(amount_fcfa)
        END AS amount_plausible_fcfa,

        COUNT(*) AS item_line_count,

        SUM(
            CASE WHEN parse_status = 'parsed'
                 THEN 1 ELSE 0 END
        ) AS parsed_item_lines,

        SUM(
            CASE WHEN parse_status = 'unknown_product'
                 THEN 1 ELSE 0 END
        ) AS unresolved_item_lines,

        SUM(
            CASE WHEN parse_status = 'missing_format'
                 THEN 1 ELSE 0 END
        ) AS missing_format_lines,

        BOOL_OR(product IS NULL) AS has_unknown_product,

        BOOL_OR(
            product IS NOT NULL
            AND format IS NULL
        ) AS has_missing_format,

        SUM(COALESCE(quantity, 0)) AS quantity_total

    FROM items

    GROUP BY whatsapp_row_id

)

SELECT
    *,
    CASE
        WHEN parsed_item_lines = item_line_count
            THEN 'fully_parsed'

        WHEN parsed_item_lines > 0
             AND unresolved_item_lines > 0
            THEN 'partially_parsed'

        WHEN missing_format_lines = item_line_count
            THEN 'missing_format_only'

        ELSE 'unresolved'
    END AS order_parse_status

FROM order_quality