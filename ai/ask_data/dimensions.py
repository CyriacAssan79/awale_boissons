from __future__ import annotations

from .semantic_layer import get_metric


DIMENSION_ALIASES = {
    "mois": "month",
    "mensuel": "month",
    "par mois": "month",
    "canal": "channel",
    "canaux": "channel",
    "produit": "product",
    "produits": "product",
    "format": "format",
    "plateforme": "platform",
    "plateformes": "platform",
    "commune": "commune",
}


def resolve_dimension(
    term: str,
    metric_name: str,
) -> str:
    """Résout une dimension et vérifie qu'elle est autorisée."""
    normalized = term.strip().lower()

    dimension = DIMENSION_ALIASES.get(normalized, normalized)

    metric = get_metric(metric_name)

    if metric is None:
        raise ValueError(f"Métrique inconnue : '{metric_name}'.")

    allowed_dimensions = metric.get("dimensions", [])

    if dimension not in allowed_dimensions:
        raise ValueError(
            f"La dimension '{dimension}' n'est pas disponible "
            f"pour la métrique '{metric_name}'. "
            f"Dimensions disponibles : {allowed_dimensions}"
        )

    return dimension

if __name__ == "__main__":
    tests = [
        ("mois", "ca_net"),
        ("canal", "spend_marketing"),
        ("plateforme", "sentiment_client"),
        ("plateforme", "ca_net"),
    ]

    for term, metric in tests:
        try:
            result = resolve_dimension(term, metric)
            print(f"{term!r} + {metric!r} -> {result}")
        except ValueError as exc:
            print(f"{term!r} + {metric!r} -> ERREUR : {exc}")