#Ici , nous allons créer un script pour profiler les tables brutes de la base de données DuckDB. 
# Le script se connecte à la base de données, récupère des informations sur chaque table spécifiée 
# dans la liste TABLES, et affiche des statistiques telles que le nombre de lignes, le schéma des 
# colonnes, le nombre de valeurs nulles par colonne, le nombre de doublons exacts et un aperçu des 
# premières lignes de chaque table.
#Ici on veut voir comment sont structurer les données

from pathlib import Path
import duckdb
DB_PATH = Path("/mnt/c/Users/KSOMS/Favorites/awale_boissons/data/awale.duckdb")

TABLES = [
    "raw_campaign_spend_export",
    "raw_media_plan",
    "raw_pos_sales_daily",
    "raw_social_comments",
    "raw_whatsapp_orders",
]


def get_connection() -> duckdb.DuckDBPyConnection:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Base introuvable : {DB_PATH}")

    return duckdb.connect(str(DB_PATH))


def profile_table(con: duckdb.DuckDBPyConnection, table: str) -> None:
    print("\n" + "=" * 80)
    print(f"TABLE : {table}")
    print("=" * 80)

    # Nombre de lignes
    row_count = con.sql(
        f"SELECT COUNT(*) AS row_count FROM {table}"
    ).fetchone()[0]

    # Colonnes
    schema = con.sql(f"DESCRIBE {table}").df()

    print(f"\nNombre de lignes : {row_count}")
    print(f"Nombre de colonnes : {len(schema)}")

    print("\nSchéma :")
    print(schema[["column_name", "column_type", "null"]].to_string(index=False))

    # Valeurs nulles
    null_expr = ", ".join(
        [
            f'SUM(CASE WHEN "{col}" IS NULL THEN 1 ELSE 0 END) AS "{col}"'
            for col in schema["column_name"]
        ]
    )

    nulls = con.sql(
        f"SELECT {null_expr} FROM {table}"
    ).df().T

    nulls.columns = ["null_count"]

    print("\nValeurs NULL :")
    print(nulls.to_string())

    # Doublons exacts
    duplicate_count = con.sql(
        f"""
        SELECT COUNT(*)
        FROM (
            SELECT *, COUNT(*) OVER (
                PARTITION BY {", ".join(f'"{c}"' for c in schema["column_name"])}
            ) AS duplicate_count
            FROM {table}
        )
        WHERE duplicate_count > 1
        """
    ).fetchone()[0]

    print(f"\nNombre de lignes appartenant à un doublon exact : {duplicate_count}")

    # Aperçu
    print("\nAperçu :")
    preview = con.sql(
        f"SELECT * FROM {table} LIMIT 5"
    ).df()

    print(preview.to_string(index=False))


def main():
    con = get_connection()

    try:
        print("TABLES DISPONIBLES")
        print(con.sql("SHOW TABLES").df().to_string(index=False))

        for table in TABLES:
            profile_table(con, table)

    finally:
        con.close()


if __name__ == "__main__":
    main()