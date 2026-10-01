"""
Construction déterministe du rapport mensuel.

Principe :
- aucun LLM ;
- aucun calcul métier nouveau ;
- aucun chiffre inventé ;
- toutes les informations viennent du monthly brief ;
- les nombres sont injectés directement depuis le brief formaté.
"""

from __future__ import annotations

from typing import Any


def _label(text: str) -> str:
    """Met une majuscule initiale sans toucher au reste (« bissap 1L » → « Bissap 1L »)."""

    return text[:1].upper() + text[1:] if text else text


def _format_channel_row(channel: dict[str, Any]) -> str:
    """Construit une ligne Markdown pour un canal marketing."""

    coverage = channel.get("source_coverage", "")

    if coverage == "both_available":
        coverage_label = "Suivi + factures"
    elif coverage == "media_plan_only":
        coverage_label = "Plan seulement"
    elif coverage == "invoice_only":
        coverage_label = "Factures seulement"
    else:
        coverage_label = "Partielles"

    return (
        f"| {channel.get('channel', 'Inconnu')} "
        f"| {channel.get('spend', '0 FCFA')} "
        f"| {channel.get('share', '0,0 %')} "
        f"| {channel.get('planned_budget', 'Non disponible')} "
        f"| {channel.get('invoiced', 'Non disponible')} "
        f"| {coverage_label} |"
    )


def build_sales_section(brief: dict[str, Any]) -> str:
    """Construit la section Ventes."""

    period = brief["period"]
    sales = brief["sales"]

    return f"""
## Ventes

{sales["revenue_statement"]}

- Chiffre d'affaires : **{sales["revenue_fcfa_formatted"]}**
- Mois précédent ({period["previous_period_label"]}) : **{sales["previous_revenue_fcfa_formatted"]}**
- Évolution : **{sales["revenue_growth_pct_formatted"]}**
- Unités vendues : **{sales["net_units_sold_formatted"]}**
- Points de vente actifs : **{sales["active_pos_formatted"]}**, dans **{sales["active_communes_formatted"]}** communes
- Jours couverts par les données : **{sales["observed_sales_days"]} sur {sales["calendar_days"]}**

*{sales["data_quality_statement"]}*
"""


def build_marketing_section(brief: dict[str, Any]) -> str:
    """Construit la section Où va l'argent ?"""

    marketing = brief["marketing"]

    rows = [
        _format_channel_row(channel)
        for channel in marketing["channels_formatted"]
    ]

    return f"""
## Où va l'argent ?

Total dépensé : **{marketing["total_spend_formatted"]}**

{marketing["principal_fait_marketing"]}

| Canal | Dépensé | Part | Prévu | Facturé | Sources |
|---|---:|---:|---:|---:|---|
{chr(10).join(rows)}

*Sources : « Suivi + factures » signifie que la dépense est confirmée par le suivi des campagnes et par les factures.*
"""


def build_customer_voice_section(brief: dict[str, Any]) -> str:
    """Construit la section Voix du client."""

    voice = brief["customer_voice"]

    theme_names = {"autre": "Autres sujets"}

    theme_lines = [
        f"- {theme_names.get(theme['theme'], _label(theme['theme']))} : "
        f"**{theme['comments']}** commentaire(s)"
        for theme in voice["top_themes"]
    ]

    def format_share(value: Any) -> str:
        if value is None:
            return "donnée non disponible"
        return f"{value:.1f}".replace(".", ",") + " %"

    positive_share = format_share(voice.get("positive_share_pct"))
    negative_share = format_share(voice.get("negative_share_pct"))
    neutral_share = format_share(voice.get("neutral_share_pct"))

    return f"""
## Voix du client

{voice["principal_signal_client"]}

**Ce que pensent les clients** — {voice["sentiment_total"]} avis sur {voice["comments_count"]} commentaires

- Positifs : **{voice["positive_count"]}** ({positive_share})
- Négatifs : **{voice["negative_count"]}** ({negative_share})
- Neutres : **{voice["neutral_count"]}** ({neutral_share})
- Messages indésirables, non comptés : **{voice["spam_count"]}**

**Sujets les plus abordés**

{chr(10).join(theme_lines)}
"""


def build_products_section(brief: dict[str, Any]) -> str:
    """Construit la section Produits."""

    products = brief["products"]
    top_products = products["top_products_formatted"]

    rows = [
        (
            f"| {_label(product['product'])} {product['format']} "
            f"| {product['units']} "
            f"| {product['revenue']} "
            f"| {product['revenue_share']} |"
        )
        for product in top_products
    ]

    top_product = products["top_product"]
    top_product_share = f"{top_product['revenue_share_pct']:.1f}".replace(".", ",")

    return f"""
## Produits

Produit phare du mois : **{_label(top_product['product'])} {top_product['format']}**, avec **{top_product_share} %** du chiffre d'affaires.

| Produit | Unités | Chiffre d'affaires | Part |
|---|---:|---:|---:|
{chr(10).join(rows)}
"""

def build_whatsapp_section(brief: dict[str, Any]) -> str:
    """Construit la section WhatsApp."""

    whatsapp = brief["whatsapp_formatted"]

    return f"""
## Commandes WhatsApp

- Commandes reçues : **{whatsapp["orders"]}**
- Livrées : **{whatsapp["delivered_orders"]}**
- Annulées : **{whatsapp["cancelled_orders"]}**
- En attente : **{whatsapp["pending_orders"]}**

**Unités commandées : {whatsapp["total_units"]}**

- Bissap : **{whatsapp["bissap_units"]}**
- Gingembre : **{whatsapp["gingembre_units"]}**
- Bouye : **{whatsapp["bouye_units"]}**

**Montants des commandes livrées**

- Total des montants renseignés : **{whatsapp["delivered_known_amount"]}**
- Commandes sans montant renseigné : **{whatsapp["missing_amount_orders"]}**
- Commandes au montant inhabituel, écartées du total : **{whatsapp["outlier_amount_orders"]}**
"""


def build_attention_section(brief: dict[str, Any]) -> str:
    """Construit la section Points d'attention."""

    points = brief.get("attention_points", [])

    if not points:
        return """
## Points d'attention

Aucun point d'attention ce mois-ci.
"""

    lines = [f"- {point}" for point in points]

    return f"""
## Points d'attention

{chr(10).join(lines)}
"""


def build_positive_section(brief: dict[str, Any]) -> str:
    """Construit la section Points positifs."""

    points = brief.get("positive_points", [])

    if not points:
        return """
## Points positifs

Aucun point positif particulier ce mois-ci.
"""

    lines = [f"- {point}" for point in points]

    return f"""
## Points positifs

{chr(10).join(lines)}
"""


def build_deterministic_sections(brief: dict[str, Any]) -> dict[str, str]:
    """
    Construit toutes les sections factuelles du rapport.

    Retour :
        {
            "sales": "...",
            "marketing": "...",
            "customer_voice": "...",
            "products": "...",
            "whatsapp": "...",
            "attention": "...",
            "positive": "..."
        }
    """

    return {
        "sales": build_sales_section(brief),
        "marketing": build_marketing_section(brief),
        "customer_voice": build_customer_voice_section(brief),
        "products": build_products_section(brief),
        "whatsapp": build_whatsapp_section(brief),
        "attention": build_attention_section(brief),
        "positive": build_positive_section(brief),
    }


def build_full_deterministic_report(brief: dict[str, Any]) -> str:
    """
    Construit un rapport entièrement déterministe.

    Cette fonction est surtout utilisée pour tester la structure
    avant d'introduire le LLM.
    """

    period = brief["period"]

    sections = build_deterministic_sections(brief)

    return f"""
# Rapport mensuel — {period["current_period_label"].capitalize()}

{sections["sales"]}

{sections["marketing"]}

{sections["customer_voice"]}

{sections["products"]}

{sections["whatsapp"]}

{sections["attention"]}

{sections["positive"]}
"""


if __name__ == "__main__":
    from ai.reporting.query_marts import build_monthly_brief

    brief = build_monthly_brief(
        year=2026,
        month=2,
    )

    report = build_full_deterministic_report(brief)

    print(report)
