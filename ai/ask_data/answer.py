from __future__ import annotations

import pandas as pd

from .intent import QueryIntent


def _format_fcfa(value: float) -> str:
    """Formate un montant FCFA de manière lisible."""
    value = float(value)

    if abs(value) >= 1_000_000:
        return f"{value / 1_000_000:.2f} M FCFA"

    if abs(value) >= 1_000:
        return f"{value / 1_000:.1f} k FCFA"

    return f"{value:,.0f}".replace(",", " ") + " FCFA"


def _format_ratio(value: float) -> str:
    """Formate un ratio en pourcentage."""
    return f"{value * 100:.1f} %"


def format_answer(
    intent: QueryIntent,
    result: pd.DataFrame,
) -> str:
    """Transforme un résultat DuckDB en réponse lisible."""

    if result.empty:
        return "Aucune donnée disponible pour cette question."

    metric = intent.metric

    if metric is None:
        return "Aucune métrique n'a été identifiée."

    if len(result) == 1 and metric in result.columns and not intent.dimensions:
        value = result.iloc[0][metric]

        if pd.isna(value):
            return "Aucune donnée disponible pour cette question."

        if metric in {
            "ca_net",
            "ca_brut",
            "spend_marketing",
            "mix_produit",
            "ecart_depense_facture",
            "budget_test_propose",
        }:
            return _format_fcfa(float(value))

        if metric in {
            "evolution_ca",
            "part_budget_canal",
            "sentiment_client",
            "taux_reachat_livraison",
            "taux_retours",
            "whatsapp_montants_exploitables",
        }:
            return _format_ratio(float(value))

        return str(value)

    # ---------------------------------------------------------
    # Résultats avec dimensions
    # ---------------------------------------------------------

    lines = []

    dimensions = intent.dimensions

    for _, row in result.iterrows():
        parts = []

        for dimension in dimensions:
            value = row.get(dimension)

            if pd.isna(value):
                continue

            if dimension == "month":
                value = pd.to_datetime(value).strftime("%Y-%m")

            parts.append(str(value))

        value = row.get(metric)

        if pd.isna(value):
            formatted_value = "N/A"
        elif metric in {
            "ca_net",
            "ca_brut",
            "spend_marketing",
            "mix_produit",
            "ecart_depense_facture",
            "budget_test_propose",
        }:
            formatted_value = _format_fcfa(float(value))
        elif metric in {
            "evolution_ca",
            "part_budget_canal",
            "sentiment_client",
            "taux_reachat_livraison",
            "taux_retours",
            "whatsapp_montants_exploitables",
        }:
            formatted_value = _format_ratio(float(value))
        else:
            formatted_value = str(value)

        if parts:
            lines.append(
                f"{', '.join(parts)} : {formatted_value}"
            )
        else:
            lines.append(formatted_value)

    return "\n".join(lines)