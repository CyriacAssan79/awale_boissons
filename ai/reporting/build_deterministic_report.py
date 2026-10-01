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


def _format_channel_row(channel: dict[str, Any]) -> str:
    """Construit une ligne Markdown pour un canal marketing."""

    coverage = channel.get("source_coverage", "")

    if coverage == "both_available":
        coverage_label = "Données média + facturation"
    elif coverage == "media_plan_only":
        coverage_label = "Plan média uniquement"
    elif coverage == "invoice_only":
        coverage_label = "Facturation uniquement"
    else:
        coverage_label = "Couverture partielle"

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
## 2. Ventes

**{period["current_period_label"].capitalize()}**

{sales["revenue_statement"]}

- CA : **{sales["revenue_fcfa_formatted"]}**
- CA du mois précédent ({period["previous_period_label"]}) : **{sales["previous_revenue_fcfa_formatted"]}**
- Évolution du CA : **{sales["revenue_growth_pct_formatted"]}**
- Unités nettes vendues : **{sales["net_units_sold_formatted"]}**
- Points de vente actifs : **{sales["active_pos_formatted"]}**
- Communes couvertes : **{sales["active_communes_formatted"]}**
- Jours de vente observés : **{sales["observed_sales_days"]}/{sales["calendar_days"]}**
- Jours non observés : **{sales["missing_sales_days"]}**

**Qualité de la comparaison :**  
{sales["data_quality_statement"]}

{sales["comparison_caveat"]}
"""


def build_marketing_section(brief: dict[str, Any]) -> str:
    """Construit la section Où va l'argent ?"""

    marketing = brief["marketing"]

    rows = [
        _format_channel_row(channel)
        for channel in marketing["channels_formatted"]
    ]

    table = "\n".join(
        [
            "| Canal | Dépenses observées | Part | Budget planifié | Facturé | Couverture |",
            "|---|---:|---:|---:|---:|---|",
            *rows,
        ]
    )

    top = marketing["top_spending_channel"]
    top_share = next(
        (
            channel["share"]
            for channel in marketing["channels_formatted"]
            if channel["channel"] == top["channel"]
        ),
        "0,0 %",
    )

    return f"""
## 3. Où va l'argent ?

**Dépenses totales observées :**  
**{marketing["total_spend_formatted"]}**

{marketing["principal_fait_marketing"]}

| Canal | Dépenses observées | Part | Budget planifié | Facturé | Couverture |
|---|---:|---:|---:|---:|---|
{chr(10).join(rows)}

**Canal représentant la plus grande part des dépenses observées :**  
{top["channel"]} — **{top_share}** du total.
"""


def build_customer_voice_section(brief: dict[str, Any]) -> str:
    """Construit la section Voix du client."""

    voice = brief["customer_voice"]

    themes = voice["top_themes"]

    theme_lines = [
        f"- **{theme['theme']}** : {theme['comments']} commentaire(s)"
        for theme in themes
    ]
    def format_share(value: Any) -> str:
        if value is None:
            return "donnée non disponible"
        return f"{value:.1f}".replace(".", ",") + " %"

    positive_share = format_share(voice.get("positive_share_pct"))
    negative_share = format_share(voice.get("negative_share_pct"))
    neutral_share = format_share(voice.get("neutral_share_pct"))

    return f"""

## 4. Voix du client

**Commentaires analysés :** {voice["comments_count"]}

{voice["principal_signal_client"]}

### Sentiment

- Positif : **{voice["positive_count"]}** ({positive_share})
- Négatif : **{voice["negative_count"]}** ({negative_share})
- Neutre : **{voice["neutral_count"]}** ({neutral_share})
- Spam : **{voice["spam_count"]}**
- Total utilisé pour le calcul du sentiment : **{voice["sentiment_total"]}**

### Principaux thèmes

{chr(10).join(theme_lines)}
"""


def build_products_section(brief: dict[str, Any]) -> str:
    """Construit la section Produits."""

    products = brief["products"]
    top_products = products["top_products_formatted"]

    rows = [
        (
            f"| {product['product']} {product['format']} "
            f"| {product['units']} "
            f"| {product['revenue']} "
            f"| {product['revenue_share']} |"
        )
        for product in top_products
    ]

    top_product = products["top_product"]
    top_product_share = f"{top_product['revenue_share_pct']:.1f}".replace(".", ",")

    top_product_statement = (
        f"**{top_product['product']} {top_product['format']} "
        f"({top_product['product_sku']}) — "
        f"{top_product_share} % du CA.**"
    )

    return f"""
## 5. Produits

Le produit représentant la plus grande part du chiffre d'affaires est :

{top_product_statement}

| Produit | Unités | CA | Part du CA |
|---|---:|---:|---:|
{chr(10).join(rows)}
"""

def build_whatsapp_section(brief: dict[str, Any]) -> str:
    """Construit la section WhatsApp."""

    whatsapp = brief["whatsapp_formatted"]

    return f"""
## 6. WhatsApp

- Commandes reçues : **{whatsapp["orders"]}**
- Commandes livrées : **{whatsapp["delivered_orders"]}**
- Commandes annulées : **{whatsapp["cancelled_orders"]}**
- Commandes en attente : **{whatsapp["pending_orders"]}**
- Unités commandées : **{whatsapp["total_units"]}**

### Répartition des unités

- Bissap : **{whatsapp["bissap_units"]}**
- Gingembre : **{whatsapp["gingembre_units"]}**
- Bouye : **{whatsapp["bouye_units"]}**

### Qualité des montants

- Montant connu des commandes livrées : **{whatsapp["delivered_known_amount"]}**
- Commandes livrées sans montant exploitable : **{whatsapp["missing_amount_orders"]}**
- Commandes présentant un montant considéré comme atypique : **{whatsapp["outlier_amount_orders"]}**
"""


def build_attention_section(brief: dict[str, Any]) -> str:
    """Construit la section Points d'attention."""

    points = brief.get("attention_points", [])

    if not points:
        return """

## 7. Points d'attention

Aucun point d'attention déterministe n'a été identifié dans les données disponibles.
"""

    lines = [f"- {point}" for point in points]

    return f"""
## 7. Points d'attention

{chr(10).join(lines)}
"""


def build_positive_section(brief: dict[str, Any]) -> str:
    """Construit la section Points positifs."""

    points = brief.get("positive_points", [])

    if not points:
        return """
## 8. Points positifs

Aucun point positif déterministe n'a été identifié dans les données disponibles.
"""

    lines = [f"- {point}" for point in points]

    return f"""
## 8. Points positifs

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
