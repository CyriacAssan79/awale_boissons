import os
from pathlib import Path
import duckdb

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DB_PATH = Path(
    os.environ.get("AWALE_DUCKDB_PATH", PROJECT_ROOT / "data" / "awale.duckdb")
)

OUTPUT_PATH = Path(
    os.environ.get(
        "AWALE_AI_INPUT_PATH",
        PROJECT_ROOT / "data" / "processed" / "social_comments_for_ai.csv",
    )
)


def main() -> None:

    if not DB_PATH.exists():
        raise FileNotFoundError(f"Base introuvable : {DB_PATH}")

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect(str(DB_PATH), read_only=True)

    try:
        df = con.execute(
            """
            SELECT
                comment_id,
                platform,
                published_at,
                author_handle,
                comment_text,
                like_count,
                reply_to_id
            FROM stg_social_comments
            ORDER BY comment_id
            """
        ).df()

    finally:
        con.close()

    if df["comment_id"].duplicated().any():
        raise RuntimeError(
            "comment_id dupliqué dans stg_social_comments : "
            "le staging doit garantir une ligne par commentaire."
        )

    df.to_csv(OUTPUT_PATH, index=False)

    print(f"[OK] {len(df):,} commentaires exportés vers {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
