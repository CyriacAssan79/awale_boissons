from __future__ import annotations

import duckdb

from .intent import QueryIntent
from .sql_builder import build_sql
from .question_parser import parse_question
from .periods import LATEST_MONTH
from .semantic_layer import get_metric
from pathlib import Path


DB_PATH = Path("data/awale.duckdb")


def execute_intent(intent: QueryIntent):
    """Construit puis exécute le SQL dans DuckDB."""
    sql = build_sql(intent)

    with duckdb.connect(DB_PATH, read_only=True) as con:
        return con.execute(sql).df()

def latest_month_of_year(intent: QueryIntent, month_number: str) -> str | None:
    """Dernier mois disponible (YYYY-MM) correspondant à un mois sans année.

    `month_number` vaut LATEST_MONTH pour le dernier mois disponible tout court.
    """
    metric = get_metric(intent.metric)

    if metric is None:
        raise ValueError(f"Métrique inconnue : '{intent.metric}'.")

    # Le nom de table vient de la couche sémantique ; le mois est paramétré.
    sql = f"""
        SELECT strftime(MAX(month), '%Y-%m')
        FROM {metric["modele"]}
    """
    params = []

    if month_number != LATEST_MONTH:
        sql += "WHERE EXTRACT(MONTH FROM month) = ?"
        params.append(int(month_number))

    with duckdb.connect(DB_PATH, read_only=True) as con:
        return con.execute(sql, params).fetchone()[0]

if __name__ == "__main__":
    question = "Combien avons-nous dépensé sur Meta en juin 2026 ?"

    intent = parse_question(question)

    print("Question :", question)
    print("Intent :", intent)

    result = execute_intent(intent)

    print("\nRésultat :")
    print(result)