{{ config(materialized='table') }}

-- ======================================================================
-- Grain client sur le canal livraison WhatsApp, à partir du téléphone
-- normalisé (customer_phone dans stg_whatsapp_orders). Sert de base au
-- KPI "taux de réachat livraison" listé en Partie A (business_problem) :
--
--   taux de réachat = clients avec >= 2 commandes LIVRÉES
--                     / clients avec >= 1 commande LIVRÉE
--
-- Une commande annulée ou en cours n'est pas un achat : is_repeat_customer
-- ne compte donc que les commandes livrées. L'ancienne définition (toutes
-- commandes, tous statuts) reste disponible dans is_repeat_customer_any_status
-- pour comparaison ; elle surestime le réachat.
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

    delivered_order_count > 0 AS has_delivered_order,
    delivered_order_count > 1 AS is_repeat_customer,
    order_count > 1 AS is_repeat_customer_any_status

FROM per_customer
