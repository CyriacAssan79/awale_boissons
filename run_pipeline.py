"""Commande unique du cycle mensuel Awalé Boissons.

Enchaîne : ingestion -> dbt run (sans les modèles dépendants de l'IA) ->
export du texte pour l'IA -> inférence IA -> rechargement des prédictions ->
dbt run complet -> dbt test.

Usage :
    python run_pipeline.py                 # cycle complet, IA incluse
    python run_pipeline.py --skip-ai        # réutilise les prédictions déjà
                                             # présentes (ou saute la Customer
                                             # Voice si aucune n'existe)
    python run_pipeline.py --skip-tests     # saute dbt test (déconseillé)

Ce script s'arrête au premier échec critique (code de sortie non nul) :
mieux vaut un run interrompu et visible qu'un rapport silencieusement
incomplet.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
DBT_DIR = PROJECT_ROOT / "dbt"
PREDICTIONS_FILE = (
    PROJECT_ROOT / "ai" / "evaluation" / "social_comments_predictions_v2_full.csv"
)
DUCKDB_PATH = Path(
    os.environ.get("AWALE_DUCKDB_PATH", PROJECT_ROOT / "data" / "awale.duckdb")
)

# Modèles qui dépendent de raw_social_comments_predictions_v2 : ils ne
# peuvent pas être construits avant que l'IA ait tourné au moins une fois.
AI_DEPENDENT_MODELS = ["int_social_comments_enriched", "mart_social_monthly"]


def predictions_table_exists() -> bool:
    if not DUCKDB_PATH.exists():
        return False

    try:
        import duckdb
    except ImportError:
        return False

    con = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    try:
        result = con.execute(
            """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = 'raw_social_comments_predictions_v2'
            """
        ).fetchone()
        return bool(result[0])
    finally:
        con.close()


def step(title: str) -> None:
    print("\n" + "=" * 70)
    print(title)
    print("=" * 70)


def run(cmd: list[str], cwd: Path, label: str) -> None:
    print(f"[RUN] ({cwd}) {' '.join(cmd)}")
    start = time.perf_counter()

    result = subprocess.run(cmd, cwd=cwd)

    elapsed = time.perf_counter() - start

    if result.returncode != 0:
        print(f"[ERREUR] {label} a échoué (code {result.returncode}, {elapsed:.1f}s).")
        sys.exit(result.returncode)

    print(f"[OK] {label} terminé en {elapsed:.1f}s.")


def main() -> None:

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-ai",
        action="store_true",
        help="Ne pas relancer l'inférence IA (réutilise les prédictions existantes).",
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Ne pas exécuter dbt test à la fin (déconseillé en production).",
    )
    args = parser.parse_args()

    python = sys.executable

    step("1/7 — Ingestion des 5 sources brutes")
    run(
        [python, str(PROJECT_ROOT / "ingestion" / "load_raw.py")],
        cwd=PROJECT_ROOT,
        label="Ingestion",
    )
    print("[OK] 5 feuilles présentes, colonnes requises vérifiées -> 5 tables raw_*.")

    step("2/7 — dbt run (hors modèles dépendants de l'IA)")
    run(
        [
            "dbt",
            "run",
            "--exclude",
            *AI_DEPENDENT_MODELS,
        ],
        cwd=DBT_DIR,
        label="dbt run (staging/intermediate/marts hors Customer Voice)",
    )

    ai_ready = False

    if args.skip_ai:
        step("3-5/7 — IA sautée (--skip-ai)")
        ai_ready = predictions_table_exists()
        if ai_ready:
            print(
                "[INFO] raw_social_comments_predictions_v2 déjà présente en base "
                "— réutilisée telle quelle."
            )
        else:
            print(
                "[ATTENTION] Aucune prédiction en base. mart_social_monthly et "
                "int_social_comments_enriched seront exclus de ce run."
            )
    else:
        step("3/7 — Export du texte des commentaires pour l'IA")
        run(
            [python, str(PROJECT_ROOT / "analysis" / "export_ai_input.py")],
            cwd=PROJECT_ROOT,
            label="Export data/processed/social_comments_for_ai.csv",
        )

        step("4/7 — Inférence IA (modèle local, cf. docs/ai_documentation.ipynb)")
        print(
            "[INFO] Cette étape peut être longue (durée réelle non garantie "
            "à ce jour, voir la limite documentée sur le runtime IA)."
        )
        run(
            [python, str(PROJECT_ROOT / "ai" / "classify_comments_hybrid.py")],
            cwd=PROJECT_ROOT,
            label="Inférence IA",
        )
        print("[OK] AI completed.")

        step("5/7 — Rechargement des prédictions dans DuckDB")
        run(
            [python, str(PROJECT_ROOT / "ingestion" / "load_predictions.py")],
            cwd=PROJECT_ROOT,
            label="Chargement raw_social_comments_predictions_v2",
        )
        ai_ready = True

    step("6/7 — dbt run (cycle complet)")
    run_cmd = ["dbt", "run"] if ai_ready else ["dbt", "run", "--exclude", *AI_DEPENDENT_MODELS]
    run(run_cmd, cwd=DBT_DIR, label="dbt run (complet)")
    print("[OK] Transformation completed.")
    if not ai_ready:
        print(
            "[ATTENTION] Customer Voice non construite ce run-ci "
            f"({', '.join(AI_DEPENDENT_MODELS)} exclus faute de prédictions)."
        )

    if args.skip_tests:
        step("7/7 — dbt test sauté (--skip-tests)")
    else:
        step("7/7 — dbt test")
        test_cmd = ["dbt", "test"] if ai_ready else ["dbt", "test", "--exclude", *AI_DEPENDENT_MODELS]
        run(test_cmd, cwd=DBT_DIR, label="dbt test")

    step("Pipeline terminé")
    print(
        "Prochaine étape : streamlit run app/app.py\n"
        "(voir docs/Runbook_Mensuel.ipynb pour les contrôles qualité à "
        "vérifier avant d'envoyer la note client.)"
    )


if __name__ == "__main__":
    main()
