from pathlib import Path
import duckdb
import pandas as pd

DB_PATH = Path(
    "/mnt/c/Users/KSOMS/Favorites/awale_boissons/data/awale.duckdb"
)

OUTPUT_PATH = Path(
    "/mnt/c/Users/KSOMS/Favorites/awale_boissons/ai/evaluation/labeled_sample.csv"
)


def main() -> None:
    if not DB_PATH.exists():
        raise FileNotFoundError(f"Base introuvable : {DB_PATH}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(DB_PATH))

    try:
        query = """
        SELECT
            comment_id,
            platform,
            published_at,
            author_handle,
            comment_text,
            like_count,
            reply_to_id
        FROM stg_social_comments
        USING SAMPLE reservoir(50 ROWS) REPEATABLE (42)
        """

        df = con.execute(query).df()

    finally:
        con.close()

    if len(df) != 50:
        raise RuntimeError(
            f"Échantillon inattendu : {len(df)} lignes au lieu de 50."
        )

    # Colonnes d'annotation humaine
    annotation_columns = [
        "language_human",
        "sentiment_human",
        "theme_human",
        "product_human",
        "is_spam_human",
        "annotation_notes",
    ]

    for column in annotation_columns:
        df[column] = ""

    df.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"Échantillon créé : {OUTPUT_PATH}")
    print(f"Nombre de commentaires : {len(df)}")
    print("\nColonnes disponibles :")
    print(df.columns.tolist())


if __name__ == "__main__":
    main()