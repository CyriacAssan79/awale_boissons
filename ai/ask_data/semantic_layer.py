from __future__ import annotations

from pathlib import Path

import yaml


SEMANTIC_LAYER_PATH = Path("docs/semantic_layer.yml")


def load_semantic_layer() -> dict:
    """Charge la couche sémantique Awalé."""
    with SEMANTIC_LAYER_PATH.open("r", encoding="utf-8") as file:
        return yaml.safe_load(file)


def list_metrics() -> list[str]:
    """Retourne la liste des métriques supportées."""
    layer = load_semantic_layer()
    return list(layer.get("metriques", {}).keys())


def get_metric(metric_name: str) -> dict | None:
    """Retourne la définition d'une métrique."""
    layer = load_semantic_layer()
    return layer.get("metriques", {}).get(metric_name)

def is_valid_metric(metric_name: str) -> bool:
    """Vérifie si une métrique existe dans la couche sémantique."""
    return get_metric(metric_name) is not None

if __name__ == "__main__":
    print("Métriques disponibles :")
    print(list_metrics())

    print("\nTest ca_net :")
    print(get_metric("ca_net"))

    print("\nValidation :")
    print("ca_net ->", is_valid_metric("ca_net"))
    print("roi ->", is_valid_metric("roi"))
    print("random_metric ->", is_valid_metric("random_metric"))