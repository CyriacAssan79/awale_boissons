# Profilage des anomalies dans les données brutes pour Awalé Boissons.

from pathlib import Path
import duckdb

DB_PATH = Path(
    "/mnt/c/Users/KSOMS/Favorites/awale_boissons/data/awale.duckdb"
)


def main():
    con = duckdb.connect(str(DB_PATH))

    print("\n" + "=" * 80)
    print("1. POS SALES — RETOURS / VALEURS NEGATIVES")
    print("=" * 80)

    print(
        con.sql(
            """
            SELECT
                COUNT(*) FILTER (WHERE revenue_fcfa < 0) AS negative_revenue_rows,
                SUM(CASE WHEN revenue_fcfa < 0 THEN revenue_fcfa ELSE 0 END)
                    AS total_returns_fcfa,
                COUNT(*) FILTER (WHERE units_sold < 0) AS negative_units_rows,
                SUM(CASE WHEN units_sold < 0 THEN units_sold ELSE 0 END)
                    AS total_return_units
            FROM raw_pos_sales_daily;
            """
        )
    )

    print("\nExemples de retours :")
    print(
        con.sql(
            """
            SELECT *
            FROM raw_pos_sales_daily
            WHERE revenue_fcfa < 0 OR units_sold < 0
            ORDER BY sale_date
            LIMIT 20;
            """
        )
    )

    print("\n" + "=" * 80)
    print("2. POS SALES — DATES MANQUANTES")
    print("=" * 80)

    print(
    con.sql(
        """
        WITH calendar AS (
            SELECT 
                CAST(date_value AS DATE) AS sale_date
            FROM generate_series(
                DATE '2026-01-01',
                DATE '2026-06-30',
                INTERVAL '1 day'
            ) AS t(date_value)
        ),
        actual AS (
            SELECT DISTINCT 
                CAST(sale_date AS DATE) AS sale_date
            FROM raw_pos_sales_daily
        )
        SELECT c.sale_date
        FROM calendar c
        LEFT JOIN actual a USING (sale_date)
        WHERE a.sale_date IS NULL
        ORDER BY c.sale_date;
        """
    )
)

    print("\n" + "=" * 80)
    print("3. CAMPAIGN — DETAIL DES DOUBLONS")
    print("=" * 80)

    print(
        con.sql(
            """
            SELECT
                platform,
                campaign_name,
                date_start,
                date_end,
                spend,
                impressions,
                clicks,
                objective
            FROM raw_campaign_spend_export
            WHERE (platform, campaign_name, date_start, date_end) IN (
                SELECT
                    platform,
                    campaign_name,
                    date_start,
                    date_end
                FROM raw_campaign_spend_export
                GROUP BY 1,2,3,4
                HAVING COUNT(*) > 1
            )
            ORDER BY platform, campaign_name, date_start;
            """
        )
    )

    print("\n" + "=" * 80)
    print("4. WHATSAPP — DETAIL DES ORDER_REF REPETES")
    print("=" * 80)

    print(
        con.sql(
            """
            SELECT *
            FROM raw_whatsapp_orders
            WHERE order_ref IN (
                SELECT order_ref
                FROM raw_whatsapp_orders
                GROUP BY order_ref
                HAVING COUNT(*) > 1
            )
            ORDER BY order_ref, received_at;
            """
        )
    )

    print("\n" + "=" * 80)
    print("5. SOCIAL — DETAIL DES COMMENT_ID REPETES")
    print("=" * 80)

    print(
        con.sql(
            """
            SELECT *
            FROM raw_social_comments
            WHERE comment_id IN (
                SELECT comment_id
                FROM raw_social_comments
                GROUP BY comment_id
                HAVING COUNT(*) > 1
            )
            ORDER BY comment_id;
            """
        )
    )

    con.close()


if __name__ == "__main__":
    main()