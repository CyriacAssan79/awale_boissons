-- Chaque pos_id du staging doit appartenir à exactement un magasin (pos_key),
-- sinon la dimension double-compterait ou perdrait des ventes.
WITH ids AS (

    SELECT
        pos_id,
        COUNT(DISTINCT pos_key) AS n_keys
    FROM {{ ref('stg_pos_sales_daily') }}
    GROUP BY pos_id

)

SELECT pos_id, n_keys
FROM ids
WHERE n_keys <> 1

UNION ALL

-- Un même magasin ne doit pas vendre sous deux identifiants le même jour :
-- ce serait une fusion abusive (deux magasins distincts au nom identique).
SELECT
    pos_key AS pos_id,
    COUNT(DISTINCT pos_id) AS n_keys
FROM {{ ref('stg_pos_sales_daily') }}
GROUP BY pos_key, sale_date
HAVING COUNT(DISTINCT pos_id) > 1
