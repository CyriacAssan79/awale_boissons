from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import Callable

import pandas as pd

from .answer import format_answer
from .executor import execute_intent, latest_month_of_year
from .intent import QueryIntent
from .llm_parser import llm_parse
from .narrative import describe_intent, metric_subject, narrate
from .periods import LATEST_MONTH, previous_month
from .question_parser import parse_question
from .sql_builder import build_sql


@dataclass
class AskDataPart:
    """Réponse pour une métrique supplémentaire (« … et les dépenses »)."""

    intent: QueryIntent
    result: pd.DataFrame


@dataclass
class AskDataResult:
    question: str
    answer: str | None = None
    narrative: str | None = None
    intent: QueryIntent | None = None
    sql: str | None = None
    result: pd.DataFrame | None = None
    error: str | None = None
    # Résultats des autres métriques citées, pour leurs graphiques.
    extras: list[AskDataPart] = field(default_factory=list)
    # Question comprise par le modèle de langage plutôt que par les règles.
    used_llm: bool = False
    # Interprétation retenue, en clair (affichée quand used_llm est vrai).
    interpretation: str | None = None


def fetch_previous_value(intent: QueryIntent) -> float | None:
    """Valeur du mois précédent, pour une question sur un seul mois sans découpage."""
    month = intent.filters.get("month")

    if not month or intent.dimensions:
        return None

    previous_intent = replace(
        intent,
        filters={**intent.filters, "month": previous_month(month)},
    )
    result = execute_intent(previous_intent)

    if result.empty or pd.isna(result.iloc[0][intent.metric]):
        return None

    return float(result.iloc[0][intent.metric])


MONTH_NAMES = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]

# Filtre « mois sans année » → filtre résolu (« mai » → month, « depuis mai » → since).
UNRESOLVED_MONTHS = {
    "month_of_year": "month",
    "since_month_of_year": "since",
}


def resolve_month_of_year(intent: QueryIntent) -> QueryIntent | None:
    """Remplace « mai » par le dernier mai disponible (ex. 2026-05).

    Traite aussi « depuis mai ». Retourne None si les données ne
    contiennent pas ce mois.
    """
    filters = dict(intent.filters)

    for unresolved, resolved in UNRESOLVED_MONTHS.items():
        month_number = filters.pop(unresolved, None)

        if month_number is None:
            continue

        month = latest_month_of_year(intent, month_number)

        if month is None:
            return None

        filters[resolved] = month

    return replace(intent, filters=filters)


def _no_data_message(parsed: QueryIntent) -> str:
    month_number = parsed.filters.get("month_of_year") or parsed.filters.get(
        "since_month_of_year"
    )

    if month_number == LATEST_MONTH:
        return "Aucune donnée n'est disponible pour le moment."

    month_name = MONTH_NAMES[int(month_number) - 1]

    if "since_month_of_year" in parsed.filters:
        return f"Aucune donnée n'est disponible depuis {month_name}."

    return f"Aucune donnée n'est disponible pour {month_name}."


def _answer_other_metric(intent: QueryIntent, metric: str) -> tuple[str, AskDataPart | None]:
    """Réponse pour une métrique supplémentaire, avec la même période et les mêmes découpages."""
    other = replace(intent, metric=metric, other_metrics=[])

    try:
        build_sql(other)
    except ValueError:
        # Découpage ou filtre non disponible pour cette métrique
        # (ex. dépenses marketing par produit).
        subject = metric_subject(metric)
        return (
            f"Je ne peux pas présenter {subject} de la même façon : "
            "posez une question dédiée.",
            None,
        )

    result = execute_intent(other)
    narrative = narrate(other, result, fetch_previous_value(other))

    return narrative, AskDataPart(intent=other, result=result)


def parse_with_fallback(
    question: str,
    model_loader: Callable[[], object] | None = None,
) -> tuple[QueryIntent, bool]:
    """Règles d'abord ; le modèle seulement si aucune métrique n'est reconnue.

    Les refus volontaires (causalité, prévision, métrique non définie,
    découpage indisponible) ne sont jamais confiés au modèle.
    """
    try:
        return parse_question(question), False
    except ValueError as exc:
        if model_loader is None or "hors périmètre" not in str(exc):
            raise

        try:
            return llm_parse(question, model_bundle=model_loader()), True
        except ValueError as llm_exc:
            # Interprétation impossible ou invalide : on garde le refus
            # d'origine, sauf si la fiche vise un découpage indisponible.
            if "dimension" in str(llm_exc):
                raise
            raise exc from llm_exc


def run_ask_data(
    question: str,
    model_loader: Callable[[], object] | None = None,
) -> AskDataResult:
    """Exécute l'intégralité du pipeline Ask the Data.

    `model_loader` renvoie le triplet (tokenizer, model, device) ; il n'est
    appelé que si les règles ne comprennent pas la question.
    """

    try:
        parsed, used_llm = parse_with_fallback(question, model_loader)
        intent = resolve_month_of_year(parsed)

        if intent is None:
            message = _no_data_message(parsed)

            return AskDataResult(
                question=question,
                answer=message,
                narrative=message,
                intent=parsed,
                used_llm=used_llm,
                interpretation=describe_intent(parsed),
            )

        sql = build_sql(intent)
        result = execute_intent(intent)
        answer = format_answer(intent, result)
        narratives = [narrate(intent, result, fetch_previous_value(intent))]
        extras = []

        for metric in intent.other_metrics:
            narrative, part = _answer_other_metric(intent, metric)
            narratives.append(narrative)

            if part is not None:
                extras.append(part)

        return AskDataResult(
            question=question,
            answer=answer,
            narrative="\n\n".join(narratives),
            intent=intent,
            sql=sql,
            result=result,
            extras=extras,
            used_llm=used_llm,
            interpretation=describe_intent(intent),
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
