from __future__ import annotations

from .answer import format_answer
from .executor import execute_intent
from .question_parser import parse_question


def ask_data(question: str) -> str:
    """Traite une question utilisateur avec le pipeline Ask the Data."""

    intent = parse_question(question)
    result = execute_intent(intent)

    return format_answer(intent, result)