{{ config(materialized='table') }}

WITH orders AS (

    SELECT
        whatsapp_row_id,
        received_at,
        amount_fcfa,
        amount_missing,
        status,
        item_line_count,
        parsed_item_lines,
        unresolved_item_lines,
        missing_format_lines,
        quantity_total,
        order_parse_status
    FROM {{ ref('int_whatsapp_order_quality') }}

),

items AS (

    SELECT
        whatsapp_row_id,
        product,
        format,
        quantity
    FROM {{ ref('int_whatsapp_items') }}

),

item_summary AS (

    SELECT
        whatsapp_row_id,

        SUM(
            CASE WHEN product = 'bissap'
                 THEN quantity ELSE 0 END
        ) AS bissap_units,

        SUM(
            CASE WHEN product = 'gingembre'
                 THEN quantity ELSE 0 END
        ) AS gingembre_units,

        SUM(
            CASE WHEN product = 'bouye'
                 THEN quantity ELSE 0 END
        ) AS bouye_units,

        SUM(
            CASE WHEN format = '1L'
                 THEN quantity ELSE 0 END
        ) AS format_1l_units,

        SUM(
            CASE WHEN format = '33cl'
                 THEN quantity ELSE 0 END
        ) AS format_33cl_units

    FROM items
    GROUP BY whatsapp_row_id

)

SELECT
    DATE_TRUNC('month', o.received_at) AS month,

    COUNT(*) AS orders,

    COUNT_IF(status = 'delivered') AS delivered_orders,
    COUNT_IF(status = 'cancelled') AS cancelled_orders,
    COUNT_IF(status = 'pending') AS pending_orders,

    COUNT_IF(amount_missing) AS amount_missing_orders,

    COUNT_IF(order_parse_status = 'fully_parsed')
        AS fully_parsed_orders,

    COUNT_IF(order_parse_status = 'missing_format_only')
        AS missing_format_orders,

    COUNT_IF(order_parse_status = 'unresolved')
        AS unresolved_orders,

    SUM(quantity_total) AS total_units,

    SUM(COALESCE(i.bissap_units, 0)) AS bissap_units,
    SUM(COALESCE(i.gingembre_units, 0)) AS gingembre_units,
    SUM(COALESCE(i.bouye_units, 0)) AS bouye_units,

    SUM(COALESCE(i.format_1l_units, 0)) AS format_1l_units,
    SUM(COALESCE(i.format_33cl_units, 0)) AS format_33cl_units,

    SUM(CASE
        WHEN amount_fcfa IS NOT NULL
        THEN amount_fcfa
        ELSE 0
    END) AS known_order_amount_fcfa

FROM orders o

LEFT JOIN item_summary i
    ON o.whatsapp_row_id = i.whatsapp_row_id

GROUP BY 1