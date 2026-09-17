# Profilage métier pour Awalé Boissons, en faisant cette requête on va problème liés aux 
# données brutes et voir comment les traiter pour les rendre plus propres et utilisables.

from pathlib import Path
import duckdb

DB_PATH = Path("/mnt/c/Users/KSOMS/Favorites/awale_boissons/data/awale.duckdb")


def connect_db():
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Base introuvable : {DB_PATH}")
    return duckdb.connect(str(DB_PATH))


def run_query(con, title, query):
    print("\n" + "=" * 90)
    print(title)
    print("=" * 90)

    try:
        result = con.sql(query)
        print(result)
    except Exception as exc:
        print(f"ERREUR : {exc}")


def profile_campaign_spend(con):
    run_query(
        con,
        "CAMPAIGN SPEND — plateformes",
        """
        SELECT platform, COUNT(*) AS rows
        FROM raw_campaign_spend_export
        GROUP BY platform
        ORDER BY rows DESC;
        """,
    )

    run_query(
        con,
        "CAMPAIGN SPEND — campagnes",
        """
        SELECT campaign_name, COUNT(*) AS rows
        FROM raw_campaign_spend_export
        GROUP BY campaign_name
        ORDER BY rows DESC;
        """,
    )

    run_query(
        con,
        "CAMPAIGN SPEND — objectifs",
        """
        SELECT objective, COUNT(*) AS rows
        FROM raw_campaign_spend_export
        GROUP BY objective
        ORDER BY rows DESC;
        """,
    )

    run_query(
        con,
        "CAMPAIGN SPEND — lignes sans impressions/clics",
        """
        SELECT
            COUNT(*) FILTER (WHERE impressions IS NULL) AS missing_impressions,
            COUNT(*) FILTER (WHERE clicks IS NULL) AS missing_clicks
        FROM raw_campaign_spend_export;
        """,
    )

    run_query(
        con,
        "CAMPAIGN SPEND — valeurs de spend",
        """
        SELECT DISTINCT spend
        FROM raw_campaign_spend_export
        ORDER BY spend
        LIMIT 100;
        """,
    )

    run_query(
        con,
        "CAMPAIGN SPEND — doublons campagne/date",
        """
        SELECT
            platform,
            campaign_name,
            date_start,
            date_end,
            COUNT(*) AS occurrences
        FROM raw_campaign_spend_export
        GROUP BY 1,2,3,4
        HAVING COUNT(*) > 1
        ORDER BY occurrences DESC;
        """,
    )


def profile_media_plan(con):
    run_query(
        con,
        "MEDIA PLAN — canaux",
        """
        SELECT channel, COUNT(*) AS rows
        FROM raw_media_plan
        GROUP BY channel
        ORDER BY rows DESC;
        """,
    )

    run_query(
        con,
        "MEDIA PLAN — mois",
        """
        SELECT month, COUNT(*) AS rows
        FROM raw_media_plan
        GROUP BY month
        ORDER BY month;
        """,
    )

    run_query(
        con,
        "MEDIA PLAN — facturation manquante",
        """
        SELECT
            COUNT(*) AS total_rows,
            COUNT(*) FILTER (WHERE invoiced_fcfa IS NULL) AS missing_invoiced
        FROM raw_media_plan;
        """,
    )

    run_query(
        con,
        "MEDIA PLAN — prévu vs facturé",
        """
        SELECT
            channel,
            SUM(planned_budget_fcfa) AS planned_fcfa,
            SUM(invoiced_fcfa) AS invoiced_fcfa,
            SUM(invoiced_fcfa) - SUM(planned_budget_fcfa) AS variance_fcfa
        FROM raw_media_plan
        GROUP BY channel
        ORDER BY planned_fcfa DESC;
        """,
    )


def profile_pos_sales(con):
    run_query(
        con,
        "POS SALES — période",
        """
        SELECT
            MIN(CAST(sale_date AS DATE)) AS min_date,
            MAX(CAST(sale_date AS DATE)) AS max_date,
            COUNT(DISTINCT CAST(sale_date AS DATE)) AS distinct_days
        FROM raw_pos_sales_daily;
        """,
    )

    run_query(
        con,
        "POS SALES — communes",
        """
        SELECT commune, COUNT(*) AS rows
        FROM raw_pos_sales_daily
        GROUP BY commune
        ORDER BY rows DESC;
        """,
    )

    run_query(
        con,
        "POS SALES — canaux de vente",
        """
        SELECT channel, COUNT(*) AS rows
        FROM raw_pos_sales_daily
        GROUP BY channel
        ORDER BY rows DESC;
        """,
    )

    run_query(
        con,
        "POS SALES — produits",
        """
        SELECT product_sku, COUNT(*) AS rows
        FROM raw_pos_sales_daily
        GROUP BY product_sku
        ORDER BY rows DESC;
        """,
    )

    run_query(
        con,
        "POS SALES — revenus négatifs",
        """
        SELECT
            COUNT(*) AS negative_rows,
            SUM(CASE WHEN revenue_fcfa < 0 THEN revenue_fcfa ELSE 0 END)
                AS negative_revenue
        FROM raw_pos_sales_daily;
        """,
    )

    run_query(
        con,
        "POS SALES — unités négatives",
        """
        SELECT COUNT(*) AS negative_units_rows
        FROM raw_pos_sales_daily
        WHERE units_sold < 0;
        """,
    )

    run_query(
        con,
        "POS SALES — pos_id utilisés avec plusieurs noms",
        """
        SELECT
            pos_id,
            COUNT(DISTINCT pos_name) AS distinct_names,
            STRING_AGG(DISTINCT pos_name, ' | ') AS names
        FROM raw_pos_sales_daily
        GROUP BY pos_id
        HAVING COUNT(DISTINCT pos_name) > 1
        ORDER BY distinct_names DESC;
        """,
    )

    run_query(
        con,
        "POS SALES — pos_name associés à plusieurs pos_id",
        """
        SELECT
            pos_name,
            COUNT(DISTINCT pos_id) AS distinct_ids,
            STRING_AGG(DISTINCT pos_id, ' | ') AS ids
        FROM raw_pos_sales_daily
        GROUP BY pos_name
        HAVING COUNT(DISTINCT pos_id) > 1
        ORDER BY distinct_ids DESC;
        """,
    )

    run_query(
        con,
        "POS SALES — dates avec données",
        """
        SELECT
            CAST(sale_date AS DATE) AS sale_date,
            COUNT(*) AS rows
        FROM raw_pos_sales_daily
        GROUP BY sale_date
        ORDER BY sale_date;
        """,
    )


def profile_whatsapp(con):
    run_query(
        con,
        "WHATSAPP — références répétées",
        """
        SELECT
            order_ref,
            COUNT(*) AS occurrences
        FROM raw_whatsapp_orders
        GROUP BY order_ref
        HAVING COUNT(*) > 1
        ORDER BY occurrences DESC;
        """,
    )

    run_query(
        con,
        "WHATSAPP — montants manquants",
        """
        SELECT
            COUNT(*) AS total_orders,
            COUNT(*) FILTER (WHERE amount_fcfa IS NULL) AS missing_amounts
        FROM raw_whatsapp_orders;
        """,
    )

    run_query(
        con,
        "WHATSAPP — statuts",
        """
        SELECT status, COUNT(*) AS rows
        FROM raw_whatsapp_orders
        GROUP BY status
        ORDER BY rows DESC;
        """,
    )

    run_query(
        con,
        "WHATSAPP — zones",
        """
        SELECT delivery_zone, COUNT(*) AS rows
        FROM raw_whatsapp_orders
        GROUP BY delivery_zone
        ORDER BY rows DESC
        LIMIT 50;
        """,
    )

    run_query(
        con,
        "WHATSAPP — formats de téléphone",
        """
        SELECT
            customer_phone,
            LENGTH(
                REGEXP_REPLACE(customer_phone, '[^0-9]', '', 'g')
            ) AS normalized_length
        FROM raw_whatsapp_orders
        LIMIT 30;
        """,
    )


def profile_social(con):
    run_query(
        con,
        "SOCIAL — plateformes",
        """
        SELECT platform, COUNT(*) AS rows
        FROM raw_social_comments
        GROUP BY platform
        ORDER BY rows DESC;
        """,
    )

    run_query(
        con,
        "SOCIAL — comment_id répétés",
        """
        SELECT
            comment_id,
            COUNT(*) AS occurrences
        FROM raw_social_comments
        GROUP BY comment_id
        HAVING COUNT(*) > 1
        ORDER BY occurrences DESC;
        """,
    )

    run_query(
        con,
        "SOCIAL — commentaires vides",
        """
        SELECT
            COUNT(*) AS total,
            COUNT(*) FILTER (
                WHERE TRIM(comment_text) = ''
            ) AS empty_comments
        FROM raw_social_comments;
        """,
    )

    run_query(
        con,
        "SOCIAL — taille des commentaires",
        """
        SELECT
            MIN(LENGTH(comment_text)) AS min_length,
            AVG(LENGTH(comment_text)) AS avg_length,
            MAX(LENGTH(comment_text)) AS max_length
        FROM raw_social_comments;
        """,
    )

    run_query(
        con,
        "SOCIAL — posts",
        """
        SELECT
            platform,
            COUNT(DISTINCT post_id) AS distinct_posts
        FROM raw_social_comments
        GROUP BY platform
        ORDER BY distinct_posts DESC;
        """,
    )


def main():
    con = connect_db()

    try:
        print("\n" + "#" * 90)
        print("PROFILAGE MÉTIER — AWALÉ BOISSONS")
        print("#" * 90)

        profile_campaign_spend(con)
        profile_media_plan(con)
        profile_pos_sales(con)
        profile_whatsapp(con)
        profile_social(con)

    finally:
        con.close()


if __name__ == "__main__":
    main()