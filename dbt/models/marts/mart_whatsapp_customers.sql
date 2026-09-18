{{ config(materialized='table') }}

-- ======================================================================
-- Grain client sur le canal livraison WhatsApp, à partir du téléphone
-- normalisé (customer_phone dans stg_whatsapp_orders). Sert de base au
-- KPI "taux de réachat livraison" listé en Partie A (business_problem) :
-- part des clients identifiés ayant passé au moins deux commandes.
--
-- Limite : customer_phone reste une clé déclarative (le téléphone tel que
-- normalisé depuis les formats sources), pas une identité vérifiée —
-- deux personnes partageant un numéro seraient comptées comme un seul
-- client, et une personne changeant de numéro comme deux clients.
-- ======================================================================

WITH orders AS (

    SELECT
        customer_phone AS customer_key,
        order_date,
        status
    FROM {{ ref('stg_whatsapp_orders') }}
    WHERE customer_phone IS NOT NULL

),

per_customer AS (

    SELECT
        customer_key,

        COUNT(*) AS order_count,
        MIN(order_date) AS first_order_date,
        MAX(order_date) AS last_order_date,

        SUM(CASE WHEN status = 'delivered' THEN 1 ELSE 0 END)
            AS delivered_order_count

    FROM orders
    GROUP BY customer_key

)

SELECT
    customer_key,
    order_count,
    delivered_order_count,
    first_order_date,
    last_order_date,
    order_count > 1 AS is_repeat_customer

FROM per_customer
