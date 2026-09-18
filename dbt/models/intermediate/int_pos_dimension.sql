-- ======================================================================
-- Dimension point de vente : un magasin = une ligne (pos_key).
--
-- Règle de résolution (exacte, vérifiable) : deux pos_id désignent le même
-- magasin si leurs noms sont identiques à la casse, aux accents et aux
-- espaces près. Sur le jeu de démarrage, cela regroupe 45 identifiants en
-- 41 magasins (4 magasins ont changé d'identifiant le 1er mai 2026).
--
-- Pas de fusion approximative : des noms simplement "proches" ne sont PAS
-- fusionnés ici, car deux magasins voisins peuvent porter des noms proches
-- ("Supermarché Yopougon Maroc" / "... Selmer" vendent tous deux sur toute la
-- période : ce sont deux magasins). Les cas ambigus sont listés dans
-- docs/data_quality.ipynb pour validation par Kômian.
-- ======================================================================

WITH per_id AS (

    SELECT
        pos_key,
        pos_id,
        MIN(pos_name_raw) AS pos_name_raw,
        MIN(commune) AS commune,
        MIN(sale_date) AS first_sale_date,
        MAX(sale_date) AS last_sale_date

    FROM {{ ref('stg_pos_sales_daily') }}

    GROUP BY pos_key, pos_id

)

SELECT
    pos_key,

    -- Identifiant et libellé du premier identifiant historique du magasin.
    ARG_MIN(pos_id, first_sale_date) AS canonical_pos_id,
    ARG_MIN(pos_name_raw, first_sale_date) AS canonical_pos_name,

    MIN(commune) AS commune,

    COUNT(*) AS pos_id_count,
    LIST(pos_id ORDER BY first_sale_date) AS pos_ids,
    COUNT(*) > 1 AS pos_id_changed,

    MIN(first_sale_date) AS first_sale_date,
    MAX(last_sale_date) AS last_sale_date

FROM per_id

GROUP BY pos_key
