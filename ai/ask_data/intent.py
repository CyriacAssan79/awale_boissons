from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class QueryIntent:
    """Représente l'intention structurée d'une question utilisateur."""

    metric: str | None = None
    dimensions: list[str] = field(default_factory=list)
    filters: dict[str, str] = field(default_factory=dict)
    comparison: str | None = None
    relative_months: int | None = None
    question: str = ""

def build_intent(
    question: str,
    metric: str,
    dimension: str | None = None,
    dimensions: list[str] | None = None,
    month: str | None = None,
    channel: str | None = None,
    relative_months: int | None = None,
) -> QueryIntent:
    resolved_dimensions = []

    if dimensions:
        resolved_dimensions.extend(dimensions)

    if dimension:
        resolved_dimensions.append(dimension)

    # Évite les doublons tout en conservant l'ordre.
    resolved_dimensions = list(dict.fromkeys(resolved_dimensions))

    filters = {}

    if month:
        filters["month"] = month

    if channel:
        filters["channel"] = channel

    return QueryIntent(
        metric=metric,
        dimensions=resolved_dimensions,
        filters=filters,
        question=question,
        relative_months=relative_months,
    )

if __name__ == "__main__":
    intent = build_intent(
        question="Quel est le CA net en juin 2026 ?",
        metric="ca_net",
        month="2026-06",
        
    )

    print(intent)

    intent = build_intent(
        question="Quel est le CA net par mois ?",
        metric="ca_net",
        dimension="month",
    )

    print(intent)