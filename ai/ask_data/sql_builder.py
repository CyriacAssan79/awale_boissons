from __future__ import annotations

from .semantic_layer import get_metric
from .intent import QueryIntent
from .filters import resolve_channel, resolve_platform, resolve_product
from .periods import validate_month


def _value_condition(column: str, value, resolve) -> str:
    """`col = 'x'` ou `col IN ('x', 'y')`, chaque valeur étant validée."""
    values = value if isinstance(value, list) else [value]
    resolved = [resolve(v) for v in values]

    if len(resolved) == 1:
        return f"{column} = '{resolved[0]}'"

    return f"{column} IN (" + ", ".join(f"'{v}'" for v in resolved) + ")"


def build_sql(intent: QueryIntent) -> str:
    """Construit une requête SQL uniquement à partir de la couche sémantique."""

    if not intent.metric:
        raise ValueError("Aucune métrique n'a été définie.")

    metric = get_metric(intent.metric)

    if metric is None:
        raise ValueError(
            f"Métrique inconnue : '{intent.metric}'."
        )

    model = metric["modele"]
    expression = metric["expression"]

    allowed_dimensions = metric.get("dimensions", [])

    for dimension in intent.dimensions:
        if dimension not in allowed_dimensions:
            raise ValueError(
                f"La dimension '{dimension}' n'est pas autorisée "
                f"pour '{intent.metric}'."
            )

    select_parts = intent.dimensions + [f"{expression} AS {intent.metric}"]

    # Composantes (positifs, neutres, négatifs…) : calculées dans la même
    # requête, à côté du total de référence.
    for name, component in metric.get("composantes", {}).items():
        select_parts.append(f"{component} AS {name}")

    sql = f"""
SELECT
    {", ".join(select_parts)}
FROM {model}
"""

    if "month_of_year" in intent.filters or "since_month_of_year" in intent.filters:
        raise ValueError(
            "Mois sans année : l'année doit être résolue avant la construction du SQL."
        )

    conditions = []

    if "month" in intent.filters:
        month = validate_month(intent.filters["month"])

        year, month_number = month.split("-")

        next_month = int(month_number) + 1
        next_year = int(year)

        if next_month == 13:
            next_month = 1
            next_year += 1

        start_date = f"{year}-{month_number}-01"
        end_date = f"{next_year:04d}-{next_month:02d}-01"

        conditions.append(
            f"month >= DATE '{start_date}' "
            f"AND month < DATE '{end_date}'"
        )

    if "since" in intent.filters:
        since = validate_month(intent.filters["since"])

        conditions.append(f"month >= DATE '{since}-01'")

    if intent.relative_months is not None:
        if intent.relative_months <= 0:
            raise ValueError(
                "Le nombre de mois relatifs doit être supérieur à 0."
            )

        conditions.append(
            f""" month >= (
                    SELECT MAX(month) - INTERVAL '{intent.relative_months - 1} months'
                    FROM {model}
                )
                AND month <= (
                    SELECT MAX(month)
                    FROM {model}
                )
                """.strip()
        )

    if "channel" in intent.filters:
        conditions.append(
            _value_condition("channel", intent.filters["channel"], resolve_channel)
        )

    if "product" in intent.filters:
        if "product" not in allowed_dimensions:
            raise ValueError(
                f"La dimension 'product' n'est pas disponible "
                f"pour la métrique '{intent.metric}'. "
                f"Dimensions disponibles : {allowed_dimensions}"
            )

        conditions.append(
            _value_condition("product", intent.filters["product"], resolve_product)
        )

    if "platform" in intent.filters:
        if "platform" not in allowed_dimensions:
            raise ValueError(
                f"La dimension 'platform' n'est pas disponible "
                f"pour la métrique '{intent.metric}'. "
                f"Dimensions disponibles : {allowed_dimensions}"
            )

        conditions.append(
            _value_condition("platform", intent.filters["platform"], resolve_platform)
        )

    if conditions:
        sql += "WHERE " + " AND ".join(conditions) + "\n"

    if intent.dimensions:
        sql += (
            "GROUP BY "
            + ", ".join(intent.dimensions)
            + "\n"
        )

    if intent.dimensions:
        sql += "ORDER BY " + ", ".join(intent.dimensions) + "\n"

    return sql.strip()


if __name__ == "__main__":
    from intent import build_intent

    intent = build_intent(
                question="test",
                metric="ca_net",
                month="DROP TABLE",

            )

    print(build_sql(intent))