import os
from pathlib import Path
import duckdb
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DB_PATH = Path(
    os.environ.get("AWALE_DUCKDB_PATH", PROJECT_ROOT / "data" / "awale.duckdb")
)

PREDICTIONS_FILE = Path(
    os.environ.get(
        "AWALE_PREDICTIONS_PATH",
        PROJECT_ROOT / "ai" / "evaluation" / "social_comments_predictions_v2_full.csv",
    )
)

TABLE_NAME = "raw_social_comments_predictions_v2"

REQUIRED_COLUMNS = [
    "comment_id",
    "language_model",
    "sentiment_model",
    "theme_model",
    "product_model",
    "is_spam_model",
    "model_used",
    "rules_complete",
]


def main() -> None:

    if not PREDICTIONS_FILE.exists():
        raise FileNotFoundError(
            f"Fichier de prédictions introuvable : {PREDICTIONS_FILE}\n"
            "Lancer d'abord ai/classify_comments_hybrid.py (ou le script "
            "d'inférence retenu) pour le générer."
        )

    df = pd.read_csv(PREDICTIONS_FILE)

    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(
            f"Colonnes manquantes dans {PREDICTIONS_FILE.name} : {missing}"
        )

    if df["comment_id"].duplicated().any():
        raise ValueError(
            f"comment_id dupliqué dans {PREDICTIONS_FILE.name} : "
            "l'inférence doit produire une ligne par commentaire."
        )

    null_predictions = df[REQUIRED_COLUMNS[1:6]].isna().sum().sum()
    if null_predictions > 0:
        raise ValueError(
            f"{null_predictions} valeur(s) NULL détectée(s) dans les champs "
            "prédits — inférence incomplète."
        )

    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(DB_PATH))

    try:
        con.register("tmp_predictions", df)

        con.execute(
            f"""
            CREATE OR REPLACE TABLE {TABLE_NAME} AS
            SELECT * FROM tmp_predictions
            """
        )

        con.unregister("tmp_predictions")

        count = con.execute(
            f"SELECT COUNT(*) FROM {TABLE_NAME}"
        ).fetchone()[0]

        print(f"[OK] {TABLE_NAME}: {count:,} rows loaded from {PREDICTIONS_FILE.name}")

    finally:
        con.close()


if __name__ == "__main__":
    main()
