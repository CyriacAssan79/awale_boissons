from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from .answer import format_answer
from .executor import execute_intent
from .intent import QueryIntent
from .question_parser import parse_question
from .sql_builder import build_sql


@dataclass
class AskDataResult:
    question: str
    answer: str | None = None
    intent: QueryIntent | None = None
    sql: str | None = None
    result: pd.DataFrame | None = None
    error: str | None = None


def run_ask_data(question: str) -> AskDataResult:
    """Exécute l'intégralité du pipeline Ask the Data."""

    try:
        intent = parse_question(question)
        sql = build_sql(intent)
        result = execute_intent(intent)
        answer = format_answer(intent, result)

        return AskDataResult(
            question=question,
            answer=answer,
            intent=intent,
            sql=sql,
            result=result,
        )

    except ValueError as exc:
        return AskDataResult(
            question=question,
            error=str(exc),
        )


def ask_data(question: str) -> str:
    """Retourne uniquement la réponse textuelle Ask the Data."""

    response = run_ask_data(question)

    if response.error:
        raise ValueError(response.error)

    return response.answer or "Aucune réponse disponible."
