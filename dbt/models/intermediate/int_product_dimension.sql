-- ======================================================================
-- Dimension produit : 1 ligne = 1 SKU des ventes POS.
--
-- Le SKU suit la convention  <produit>-<format>  :
--     BIS-1L   -> bissap, 1L        BIS-33  -> bissap, 33cl
--     GIN-1L   -> gingembre, 1L     GIN-33  -> gingembre, 33cl
--     BOU-1L   -> bouye, 1L
--
-- Règle : seuls les préfixes et formats CONNUS sont traduits. Un SKU inconnu
-- garde product / format à NULL (on n'invente jamais un produit ou un format) et
-- le test int_product_dimension_mapped échoue pour qu'on complète le mapping ici
-- au lieu de laisser un produit disparaître silencieusement du mix.
-- Aucun prix n'est écrit ici : le prix moyen se lit dans mart_product_mix_monthly.
-- ======================================================================

WITH skus AS (

    SELECT DISTINCT
        product_sku
    FROM {{ ref('stg_pos_sales_daily') }}
    WHERE product_sku IS NOT NULL

)

SELECT
    product_sku,

    CASE UPPER(SPLIT_PART(product_sku, '-', 1))
        WHEN 'BIS' THEN 'bissap'
        WHEN 'GIN' THEN 'gingembre'
        WHEN 'BOU' THEN 'bouye'
    END AS product,

    CASE UPPER(SPLIT_PART(product_sku, '-', 2))
        WHEN '1L' THEN '1L'
        WHEN '33' THEN '33cl'
        WHEN '33CL' THEN '33cl'
    END AS format,

    CASE UPPER(SPLIT_PART(product_sku, '-', 2))
        WHEN '1L' THEN 1.0
        WHEN '33' THEN 0.33
        WHEN '33CL' THEN 0.33
    END AS volume_litres

FROM skus
