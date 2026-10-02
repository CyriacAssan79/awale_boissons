from __future__ import annotations

import duckdb

from .intent import QueryIntent
from .sql_builder import build_sql
from .question_parser import parse_question
from pathlib import Path


DB_PATH = Path("data/awale.duckdb")


def execute_intent(intent: QueryIntent):
    """Construit puis exécute le SQL dans DuckDB."""
    sql = build_sql(intent)

    with duckdb.connect(DB_PATH, read_only=True) as con:
        return con.execute(sql).df()

if __name__ == "__main__":
    question = "Combien avons-nous dépensé sur Meta en juin 2026 ?"

    intent = parse_question(question)

    print("Question :", question)
    print("Intent :", intent)

    result = execute_intent(intent)

    print("\nRésultat :")
    print(result)