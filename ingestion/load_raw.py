import os
from pathlib import Path
import duckdb
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = Path(os.environ.get("AWALE_RAW_DIR", PROJECT_ROOT / "data" / "raw"))
RAW_DIR = DATA_DIR
DB_PATH = Path(
    os.environ.get("AWALE_DUCKDB_PATH", PROJECT_ROOT / "data" / "awale.duckdb")
)
SOURCE_FILE = RAW_DIR / "awale_boissons_starter_dataset.xlsx"

SHEETS = {
    "campaign_spend_export": "campaign_spend_export",
    "media_plan": "media_plan",
    "pos_sales_daily": "pos_sales_daily",
    "whatsapp_orders": "whatsapp_orders",
    "social_comments": "social_comments",
}

# Colonnes que les modèles dbt (staging) lisent : si l'une manque, mieux vaut
# s'arrêter ici avec un message clair que d'échouer plus loin dans dbt.
REQUIRED_COLUMNS = {
    "campaign_spend_export": [
        "platform", "campaign_name", "date_start", "date_end",
        "spend", "impressions", "clicks", "objective",
    ],
    "media_plan": [
        "plan_id", "month", "channel", "planned_budget_fcfa",
        "invoiced_fcfa", "objective", "owner", "notes",
    ],
    "pos_sales_daily": [
        "sale_date", "pos_id", "pos_name", "commune", "channel",
        "product_sku", "units_sold", "revenue_fcfa",
    ],
    "whatsapp_orders": [
        "order_ref", "received_at", "customer_phone", "items_text",
        "amount_fcfa", "delivery_zone", "status",
    ],
    "social_comments": [
        "comment_id", "platform", "post_id", "published_at",
        "author_handle", "comment_text", "like_count", "reply_to_id",
    ],
}


def read_sheet(sheet_name: str) -> pd.DataFrame:
    """Read one Excel sheet without applying business transformations."""
    try:
        return pd.read_excel(
            SOURCE_FILE,
            sheet_name=sheet_name
        )
    except ValueError as error:
        raise ValueError(
            f"Feuille '{sheet_name}' introuvable dans {SOURCE_FILE.name} "
            f"(feuilles attendues : {list(SHEETS.values())})."
        ) from error


def main() -> None:

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Source file not found: {SOURCE_FILE}"
        )

    # Passe 1 : lire ET valider les cinq feuilles avant d'écrire quoi que ce
    # soit. Une erreur sur la 4e feuille ne doit pas laisser la base dans un
    # état mixte (3 tables du nouveau mois, 2 de l'ancien).
    frames = {}

    for table_name, sheet_name in SHEETS.items():

        print(f"\n[INFO] Reading sheet: {sheet_name}")

        df = read_sheet(sheet_name)

        # Une feuille vide n'est jamais ignorée : sinon la table RAW du mois
        # précédent resterait en place et le rapport mélangerait des périodes.
        if df.empty:
            raise ValueError(
                f"La feuille '{sheet_name}' est vide : ingestion interrompue "
                "pour ne pas conserver silencieusement les données précédentes."
            )

        missing = [
            col for col in REQUIRED_COLUMNS[table_name]
            if col not in df.columns
        ]
        if missing:
            raise ValueError(
                f"Colonnes manquantes dans la feuille '{sheet_name}' : "
                f"{missing}. Colonnes trouvées : {list(df.columns)}"
            )

        frames[table_name] = df

    # Passe 2 : toutes les feuilles sont valides, on charge.
    con = duckdb.connect(str(DB_PATH))

    try:

        for table_name, df in frames.items():

            # Enregistrement temporaire dans DuckDB
            con.register("tmp_df", df)

            raw_table = f"raw_{table_name}"

            # Création de la table RAW
            con.execute(f"""
                CREATE OR REPLACE TABLE {raw_table} AS
                SELECT *
                FROM tmp_df
            """)

            count = con.execute(
                f"SELECT COUNT(*) FROM {raw_table}"
            ).fetchone()[0]

            columns = con.execute(
                f"""
                SELECT COUNT(*)
                FROM information_schema.columns
                WHERE table_name = '{raw_table}'
                """
            ).fetchone()[0]

            print(
                f"[OK] {raw_table}: "
                f"{count:,} rows × {columns} columns"
            )

            con.unregister("tmp_df")

    finally:
        con.close()

    print("\n[OK] RAW ingestion completed.")


if __name__ == "__main__":
    main()