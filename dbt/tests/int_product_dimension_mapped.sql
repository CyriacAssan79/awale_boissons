-- Tout SKU vendu doit être traduit en produit ET en format. Un SKU inconnu
-- (nouveau produit, faute de saisie) doit être ajouté dans int_product_dimension :
-- sinon il sortirait du mix produit sans que personne ne le voie.
SELECT
    product_sku,
    product,
    format
FROM {{ ref('int_product_dimension') }}
WHERE product IS NULL
   OR format IS NULL
   OR volume_litres IS NULL
