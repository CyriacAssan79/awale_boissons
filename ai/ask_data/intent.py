from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class QueryIntent:
    """Représente l'intention structurée d'une question utilisateur."""

    metric: str | None = None
    dimensions: list[str] = field(default_factory=list)
    # Valeur simple, ou liste pour comparer plusieurs produits / canaux.
    filters: dict[str, str | list[str]] = field(default_factory=dict)
    comparison: str | None = None
    relative_months: int | None = None
    question: str = ""
    # Autres métriques citées (« les ventes et les dépenses »).
    other_metrics: list[str] = field(default_factory=list)

def build_intent(
    question: str,
    metric: str,
    dimension: str | None = None,
    dimensions: list[str] | None = None,
    month: str | None = None,
    channel: str | list[str] | None = None,
    relative_months: int | None = None,
    comparison: str | None = None,
    product: str | list[str] | None = None,
    platform: str | list[str] | None = None,
    month_of_year: str | None = None,
    since: str | None = None,
    since_month_of_year: str | None = None,
    other_metrics: list[str] | None = None,
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

    if product:
        filters["product"] = product

    if platform:
        filters["platform"] = platform

    # Mois cité sans année (« en mai ») : l'année est fixée par le service,
    # d'après les données disponibles, avant la construction du SQL.
    if month_of_year:
        filters["month_of_year"] = month_of_year

    # « depuis mars 2026 » / « depuis mars » (année résolue par le service).
    if since:
        filters["since"] = since

    if since_month_of_year:
        filters["since_month_of_year"] = since_month_of_year

    return QueryIntent(
        metric=metric,
        dimensions=resolved_dimensions,
        filters=filters,
        question=question,
        relative_months=relative_months,
        comparison=comparison,
        other_metrics=list(other_metrics or []),
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