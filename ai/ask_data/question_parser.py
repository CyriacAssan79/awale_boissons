from __future__ import annotations

from .dimensions import resolve_dimension
from .intent import build_intent
from .periods import extract_month, extract_relative_months
from .resolver import resolve_metric_alias
from .filters import CHANNEL_ALIASES, resolve_channel
import re

def parse_question(question: str):
    """Transforme une question simple en QueryIntent."""

    text = question.lower()

    # ---------------------------------------------------------
    # 0. Détection des analyses non supportées
    # ---------------------------------------------------------

    causal_terms = [
        "causé",
        "cause",
        "causer",
        "pourquoi",
        "impact",
        "influence",
        "responsable",
    ]

    forecast_terms = [
        "prévoir",
        "prévision",
        "prévisions",
        "prédire",
        "prédiction",
        "prévisionnel",
        "sera",
        "seront",
        "prochain mois",
        "mois prochain",
    ]

    if any(term in text for term in causal_terms):
        raise ValueError(
            "Analyse causale non supportée : "
            "Ask the Data ne permet pas d'attribuer une causalité "
            "à partir des données disponibles."
        )

    if any(term in text for term in forecast_terms):
        raise ValueError(
            "Prévision non supportée : "
            "Ask the Data fournit uniquement des analyses "
            "des données observées."
        )

    # ---------------------------------------------------------
    # 1. Résolution de la métrique
    # ---------------------------------------------------------

    metric = None

    metric_terms = [
        # Marketing
        "dépenses marketing",
        "depenses marketing",
        "dépense marketing",
        "depense marketing",
        "dépensé",
        "depense",
        "dépenses",
        "spend",
        "budget dépensé",
        "budget depense",

        # Chiffre d'affaires
        "chiffre d'affaires",
        "chiffre d affaire",
        "revenus",
        "ca",

        # Produit
        "mix produit",
        "mix produit mensuel",
    ]

    for term in metric_terms:
        if term in text:
            metric = resolve_metric_alias(term)
            break

    unsupported_metrics = [
        "roi",
        "retour sur investissement",
        "coût par litre",
        "cout par litre",
        "chiffre d'affaires livraison",
        "ca livraison",
    ]

    for unsupported in unsupported_metrics:
        if unsupported in text:
            raise ValueError(
                f"Métrique non supportée : '{unsupported}'. "
                "Cette métrique n'est pas définie dans le semantic layer."
            )
    
    if metric is None:
        raise ValueError(
            "Question hors périmètre : "
            "aucune métrique prise en charge n'a été identifiée."
        )

    # ---------------------------------------------------------
    # 2. Résolution de la période
    # ---------------------------------------------------------

    month = extract_month(question)
    relative_months = extract_relative_months(question)

    if month and relative_months:
        raise ValueError(
            "Période ambiguë : la question contient à la fois "
            "un mois précis et une période relative."
        )

    # ---------------------------------------------------------
    # 3. Résolution du canal
    # ---------------------------------------------------------

    channel = None

    for alias in CHANNEL_ALIASES:
        pattern = rf"\b{re.escape(alias)}\b"

        if re.search(pattern, text):
            channel = resolve_channel(alias)
            break

        # ---------------------------------------------------------
    # 4. Résolution des dimensions
    # ---------------------------------------------------------

    dimensions = []

    dimension_terms = {
        "mois": [
            "par mois",
            "chaque mois",
            "mensuel",
        ],
        "canal": [
            "par canal",
            "par canaux",
        ],
        "produit": [
            "par produit",
            "par produits",
        ],
        "plateforme": [
            "par plateforme",
            "par plateformes",
        ],
        "commune": [
            "par commune",
            "par communes",
        ],
        "format": [
            "par format",
            "par formats",
        ],
    }

    for dimension_name, terms in dimension_terms.items():
        if any(term in text for term in terms):
            resolved_dimension = resolve_dimension(
                dimension_name,
                metric,
            )
            dimensions.append(resolved_dimension)

    # ---------------------------------------------------------
    # 5. Construction de l'intention
    # ---------------------------------------------------------

    return build_intent(
        question=question,
        metric=metric,
        dimensions=dimensions,
        month=month,
        channel=channel,
        relative_months=relative_months,
    )


if __name__ == "__main__":
    questions = [
        "Quel est le CA net en juin 2026 ?",
        "Quel est le CA net par mois ?",
        "Quel est le chiffre d'affaires en mars 2026 ?",
        "Combien avons-nous dépensé sur Meta ?",
        "Quel est le spend TikTok ?",
        "Combien avons-nous dépensé sur Google en juin 2026 ?",
        "Quel est le montant dépensé par canal ?",
        "Quel est le spend par canal ?",
    ]

    for question in questions:
        print(f"\nQuestion : {question}")

        try:
            intent = parse_question(question)
            print(f"Intent : {intent}")

        except ValueError as exc:
            print(f"Erreur : {exc}")