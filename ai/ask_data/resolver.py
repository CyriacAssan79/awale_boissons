from __future__ import annotations

from .semantic_layer import get_metric, list_metrics


def resolve_metric(metric_name: str) -> str:
    """Valide et retourne le nom canonique d'une métrique."""
    metric_name = metric_name.strip().lower()

    if metric_name not in list_metrics():
        raise ValueError(
            f"Métrique inconnue : '{metric_name}'. "
            f"Métriques disponibles : {', '.join(list_metrics())}"
        )

    return metric_name

METRIC_ALIASES = {
    "ca": "ca_net",
    "chiffre affaires": "ca_net",
    "chiffre d'affaires": "ca_net",
    "chiffre d affaire": "ca_net",
    "revenus": "ca_net",

    "dépenses marketing": "spend_marketing",
    "depenses marketing": "spend_marketing",
    "dépense marketing": "spend_marketing",
    "depense marketing": "spend_marketing",
    "dépensé": "spend_marketing",
    "depense": "spend_marketing",
    "dépenses": "spend_marketing",

    "spend": "spend_marketing",
    "budget dépensé": "spend_marketing",
    "budget depense": "spend_marketing",

    "mix produit": "mix_produit",
    "mix produit mensuel": "mix_produit",
}

def resolve_metric_alias(term: str) -> str:
    """Résout un terme métier vers une métrique canonique."""
    normalized = term.strip().lower()

    if normalized in METRIC_ALIASES:
        return resolve_metric(METRIC_ALIASES[normalized])

    return resolve_metric(normalized)

if __name__ == "__main__":
    tests = [
        "ca",
        "chiffre d'affaires",
        "revenus",
        "dépenses marketing",
        "spend",
        "ca_net",
    ]

    for term in tests:
        print(f"{term!r} -> {resolve_metric_alias(term)}")