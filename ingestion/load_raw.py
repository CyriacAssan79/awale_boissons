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


def read_sheet(sheet_name: str) -> pd.DataFrame:
    """Read one Excel sheet without applying business transformations."""
    return pd.read_excel(
        SOURCE_FILE,
        sheet_name=sheet_name
    )


def main() -> None:

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    if not SOURCE_FILE.exists():
        raise FileNotFoundError(
            f"Source file not found: {SOURCE_FILE}"
        )

    con = duckdb.connect(str(DB_PATH))

    try:

        for table_name, sheet_name in SHEETS.items():

            print(f"\n[INFO] Loading sheet: {sheet_name}")

            df = read_sheet(sheet_name)

            if df.empty:
                print(f"[WARNING] {sheet_name} is empty")
                continue

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