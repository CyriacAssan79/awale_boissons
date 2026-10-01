from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Any

import duckdb
import pandas as pd


DB_PATH = Path("data/awale.duckdb")


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------

def _scalar(
    df: pd.DataFrame,
    column: str,
    default: Any = None,
) -> Any:
    """Return the first value of a column safely."""
    if df.empty:
        return default

    if column not in df.columns:
        return default

    value = df.iloc[0][column]

    if pd.isna(value):
        return default

    return value


def _month_start(year: int, month: int) -> date:
    """Return the first day of a month."""
    return date(year, month, 1)


def _direction(value: float | None) -> str:
    """Convert a numeric variation into a deterministic direction."""
    if value is None:
        return "inconnue"

    if value > 0:
        return "hausse"

    if value < 0:
        return "baisse"

    return "stable"


def _safe_float(value: Any, default: float = 0.0) -> float:
    """Convert a value to float without crashing on NULL/NaN."""
    if value is None:
        return default

    try:
        if pd.isna(value):
            return default
    except TypeError:
        pass

    return float(value)


def _safe_int(value: Any, default: int = 0) -> int:
    """Convert a value to int without crashing on NULL/NaN."""
    if value is None:
        return default

    try:
        if pd.isna(value):
            return default
    except TypeError:
        pass

    return int(value)


def _format_fcfa(value: float | int | None) -> str:
    """
    Format a monetary value for human-readable reporting.

    Example:
        1110900 -> "1 110 900 FCFA"
    """

    if value is None:
        return "donnée non disponible"

    value = float(value)

    if value.is_integer():
        return f"{int(value):,}".replace(",", " ") + " FCFA"

    return (
        f"{value:,.2f}"
        .replace(",", " ")
        .replace(".", ",")
        + " FCFA"
    )


def _format_pct(value: float | int | None) -> str:
    """
    Format a percentage.

    Example:
        -68.4 -> "−68,4 %"
    """

    if value is None:
        return "donnée non disponible"

    value = float(value)

    sign = "−" if value < 0 else ""

    return (
        f"{sign}{abs(value):.1f}"
        .replace(".", ",")
        + " %"
    )


def _format_number(value: float | int | None) -> str:
    """
    Format an integer-like business metric.
    """

    if value is None:
        return "donnée non disponible"

    value = float(value)

    if value.is_integer():
        return f"{int(value):,}".replace(",", " ")

    return f"{value:,.2f}".replace(",", " ")


def _month_label(year: int, month: int) -> str:
    """
    Return a French month label.
    """

    months = [
        "janvier",
        "février",
        "mars",
        "avril",
        "mai",
        "juin",
        "juillet",
        "août",
        "septembre",
        "octobre",
        "novembre",
        "décembre",
    ]

    return f"{months[month - 1]} {year}"


def _previous_period(year: int, month: int) -> tuple[int, int]:
    """
    Return the previous calendar month.
    """

    if month == 1:
        return year - 1, 12

    return year, month - 1

# ---------------------------------------------------------------------
# Main brief builder
# ---------------------------------------------------------------------

def build_monthly_brief(
    year: int,
    month: int,
    db_path: str | Path = DB_PATH,
) -> dict[str, Any]:
    """
    Build the deterministic monthly business brief.

    IMPORTANT
    ---------
    This function performs ALL numerical calculations.

    The future LLM reporting layer must NOT:
    - calculate revenue variations;
    - calculate budget shares;
    - determine which channel spent the most;
    - infer the majority sentiment;
    - invent missing values;
    - infer causal relationships.

    The LLM will only transform this structured brief
    into readable French.
    """

    # =============================================================
    # 0. PERIOD
    # =============================================================

    target_month = _month_start(year, month)

    previous_year, previous_month = _previous_period(
        year,
        month,
    )

    current_period_label = _month_label(
        year,
        month,
    )

    previous_period_label = _month_label(
        previous_year,
        previous_month,
    )

    con = duckdb.connect(
        str(db_path),
        read_only=True,
    )

    try:

        # =============================================================
        # 1. MONTHLY PERFORMANCE
        # =============================================================

        performance = con.execute(
            """
            SELECT *
            FROM mart_monthly_performance
            WHERE month = ?
            """,
            [target_month],
        ).df()

        if performance.empty:
            raise ValueError(
                f"Aucune donnée de performance pour "
                f"{year}-{month:02d}."
            )

        previous = con.execute(
            """
            SELECT *
            FROM mart_monthly_performance
            WHERE month < ?
            ORDER BY month DESC
            LIMIT 1
            """,
            [target_month],
        ).df()

        # -------------------------------------------------------------
        # Revenue
        # -------------------------------------------------------------

        revenue_fcfa = _safe_float(
            _scalar(
                performance,
                "net_revenue_fcfa",
                0,
            )
        )

        previous_revenue_fcfa = None

        if not previous.empty:
            previous_revenue_fcfa = _safe_float(
                _scalar(
                    previous,
                    "net_revenue_fcfa",
                    0,
                )
            )

        # -------------------------------------------------------------
        # Revenue evolution
        # -------------------------------------------------------------

        if (
            previous_revenue_fcfa is None
            or previous_revenue_fcfa == 0
        ):
            revenue_growth_pct = None

        else:
            revenue_growth_pct = round(
                (
                    (revenue_fcfa - previous_revenue_fcfa)
                    / previous_revenue_fcfa
                )
                * 100,
                1,
            )

        revenue_direction = _direction(
            revenue_growth_pct
        )

        # -------------------------------------------------------------
        # Sales coverage
        # -------------------------------------------------------------

        missing_sales_days = _scalar(
            performance,
            "missing_sales_days",
            None,
        )

        observed_sales_days = _safe_int(
            _scalar(
                performance,
                "observed_sales_days",
                0,
            )
        )

        calendar_days = _safe_int(
            _scalar(
                performance,
                "calendar_days",
                0,
            )
        )

        # -------------------------------------------------------------
        # Deterministic revenue statement
        # -------------------------------------------------------------

        if revenue_direction == "hausse":

            revenue_statement = (
                f"Le CA est en hausse de "
                f"{_format_pct(revenue_growth_pct)} "
                f"par rapport à "
                f"{previous_period_label}."
            )

        elif revenue_direction == "baisse":

            revenue_statement = (
                f"Le CA est en baisse de "
                f"{_format_pct(abs(revenue_growth_pct))} "
                f"par rapport à "
                f"{previous_period_label}."
            )

        else:

            revenue_statement = (
                f"Le CA est stable par rapport à "
                f"{previous_period_label}."
            )

        # -------------------------------------------------------------
        # Data quality statement
        # -------------------------------------------------------------

        if (
            missing_sales_days is not None
            and _safe_float(missing_sales_days) > 0
        ):

            data_quality_statement = (
                "La comparaison mensuelle doit être interprétée "
                "avec prudence car certaines journées de vente "
                "ne sont pas observées."
            )

        else:

            data_quality_statement = (
                "La couverture temporelle des ventes est complète "
                "pour le mois."
            )

        # =============================================================
        # 2. MARKETING CHANNELS
        # =============================================================

        channels = con.execute(
            """
            SELECT
                channel,
                campaign_spend_fcfa,
                planned_budget_fcfa,
                invoiced_fcfa,
                campaign_vs_invoiced_variance_fcfa,
                source_coverage,
                clicks,
                impressions
            FROM mart_marketing_channel_monthly
            WHERE month = ?
            ORDER BY campaign_spend_fcfa DESC
            """,
            [target_month],
        ).df()

        total_spend_fcfa = _safe_float(
            _scalar(
                performance,
                "campaign_spend_fcfa",
                0,
            )
        )

        channel_rows: list[dict[str, Any]] = []

        for _, row in channels.iterrows():

            spend = _safe_float(
                row.get("campaign_spend_fcfa")
            )

            share_pct = None

            if total_spend_fcfa > 0:
                share_pct = round(
                    spend / total_spend_fcfa * 100,
                    1,
                )

            # ---------------------------------------------------------
            # Source coverage
            # ---------------------------------------------------------

            raw_coverage = row.get(
                "source_coverage"
            )

            source_coverage = (
                str(raw_coverage)
                if raw_coverage is not None
                else "non disponible"
            )

            channel_rows.append(
                {
                    "channel": row.get(
                        "channel"
                    ),

                    # Dépense réellement utilisée
                    # pour les calculs du reporting.
                    "spend_fcfa": round(
                        spend,
                        0,
                    ),

                    "share_pct": share_pct,

                    "planned_budget_fcfa": (
                        _safe_float(
                            row.get(
                                "planned_budget_fcfa"
                            )
                        )
                    ),

                    "invoiced_fcfa": (
                        _safe_float(
                            row.get(
                                "invoiced_fcfa"
                            )
                        )
                    ),

                    "variance_fcfa": (
                        _safe_float(
                            row.get(
                                "campaign_vs_invoiced_variance_fcfa"
                            )
                        )
                    ),

                    "source_coverage": source_coverage,
                }
            )

        top_spending_channel = None

        if channel_rows:

            top_spending_channel = channel_rows[0]

        # -------------------------------------------------------------
        # Deterministic marketing signal
        # -------------------------------------------------------------

        if top_spending_channel is not None:

            principal_fait_marketing = (
                f"{top_spending_channel['channel']} "
                f"représente la plus grande part des dépenses "
                f"observées, avec "
                f"{_format_pct(top_spending_channel['share_pct'])} "
                f"du total."
            )

        else:

            principal_fait_marketing = (
                "Aucune dépense marketing exploitable "
                "n'est disponible pour le mois."
            )

        # =============================================================
        # 3. CUSTOMER VOICE
        # =============================================================

        social = con.execute(
            """
            SELECT
                SUM(comments_count)
                    AS comments_count,

                SUM(unique_comments_count)
                    AS unique_comments_count,

                SUM(positive_comments_count)
                    AS positive_comments_count,

                SUM(negative_comments_count)
                    AS negative_comments_count,

                SUM(neutral_comments_count)
                    AS neutral_comments_count,

                SUM(spam_comments_count)
                    AS spam_comments_count,

                SUM(taste_comments_count)
                    AS taste_comments_count,

                SUM(price_comments_count)
                    AS price_comments_count,

                SUM(promotion_comments_count)
                    AS promotion_comments_count,

                SUM(availability_comments_count)
                    AS availability_comments_count,

                SUM(packaging_comments_count)
                    AS packaging_comments_count,

                SUM(health_comments_count)
                    AS health_comments_count,

                SUM(delivery_comments_count)
                    AS delivery_comments_count,

                SUM(service_comments_count)
                    AS service_comments_count,

                SUM(product_question_comments_count)
                    AS product_question_comments_count,

                SUM(other_theme_comments_count)
                    AS other_theme_comments_count

            FROM mart_social_monthly

            WHERE month = ?
            """,
            [target_month],
        ).df()

        comments_count = _safe_int(
            _scalar(
                social,
                "comments_count",
                0,
            )
        )

        unique_comments_count = _safe_int(
            _scalar(
                social,
                "unique_comments_count",
                0,
            )
        )

        positive_count = _safe_int(
            _scalar(
                social,
                "positive_comments_count",
                0,
            )
        )

        negative_count = _safe_int(
            _scalar(
                social,
                "negative_comments_count",
                0,
            )
        )

        neutral_count = _safe_int(
            _scalar(
                social,
                "neutral_comments_count",
                0,
            )
        )

        spam_count = _safe_int(
            _scalar(
                social,
                "spam_comments_count",
                0,
            )
        )

        # -------------------------------------------------------------
        # Sentiment
        # -------------------------------------------------------------

        sentiment_total = (
            positive_count
            + negative_count
            + neutral_count
        )

        if sentiment_total > 0:

            sentiment_values = {
                "positif": positive_count,
                "négatif": negative_count,
                "neutre": neutral_count,
            }

            sentiment_majority = max(
                sentiment_values,
                key=sentiment_values.get,
            )

        else:

            sentiment_majority = "inconnu"

        if sentiment_total > 0:

            positive_share_pct = round(
                positive_count
                / sentiment_total
                * 100,
                1,
            )

            negative_share_pct = round(
                negative_count
                / sentiment_total
                * 100,
                1,
            )

            neutral_share_pct = round(
                neutral_count
                / sentiment_total
                * 100,
                1,
            )

        else:

            positive_share_pct = None
            negative_share_pct = None
            neutral_share_pct = None

        # -------------------------------------------------------------
        # Themes
        # -------------------------------------------------------------

        themes = {
            "goût": _safe_int(
                _scalar(
                    social,
                    "taste_comments_count",
                    0,
                )
            ),

            "prix": _safe_int(
                _scalar(
                    social,
                    "price_comments_count",
                    0,
                )
            ),

            "promotion": _safe_int(
                _scalar(
                    social,
                    "promotion_comments_count",
                    0,
                )
            ),

            "disponibilité": _safe_int(
                _scalar(
                    social,
                    "availability_comments_count",
                    0,
                )
            ),

            "emballage": _safe_int(
                _scalar(
                    social,
                    "packaging_comments_count",
                    0,
                )
            ),

            "santé": _safe_int(
                _scalar(
                    social,
                    "health_comments_count",
                    0,
                )
            ),

            "livraison": _safe_int(
                _scalar(
                    social,
                    "delivery_comments_count",
                    0,
                )
            ),

            "service": _safe_int(
                _scalar(
                    social,
                    "service_comments_count",
                    0,
                )
            ),

            "question produit": _safe_int(
                _scalar(
                    social,
                    "product_question_comments_count",
                    0,
                )
            ),

            "autre": _safe_int(
                _scalar(
                    social,
                    "other_theme_comments_count",
                    0,
                )
            ),
        }

        top_themes = [
            {
                "theme": theme,
                "comments": count,
            }
            for theme, count in sorted(
                themes.items(),
                key=lambda item: item[1],
                reverse=True,
            )
            if count > 0
        ][:3]

        # -------------------------------------------------------------
        # Deterministic Customer Voice signal
        # -------------------------------------------------------------

        if sentiment_majority == "positif":

            principal_signal_client = (
                "Les commentaires positifs sont majoritaires."
            )

        elif sentiment_majority == "négatif":

            principal_signal_client = (
                "Les commentaires négatifs sont majoritaires."
            )

        elif sentiment_majority == "neutre":

            principal_signal_client = (
                "Les commentaires neutres sont majoritaires."
            )

        else:

            principal_signal_client = (
                "La majorité des sentiments n'est pas déterminable."
            )

        # =============================================================
        # 4. PRODUCT MIX
        # =============================================================

        products = con.execute(
            """
            SELECT
                product,
                format,
                product_sku,
                net_units,
                net_revenue_fcfa,
                revenue_share_of_month,
                month_missing_sales_days
            FROM mart_product_mix_monthly
            WHERE month = ?
            ORDER BY net_revenue_fcfa DESC
            """,
            [target_month],
        ).df()

        product_rows: list[dict[str, Any]] = []

        for _, row in products.head(5).iterrows():

            revenue_share = _safe_float(
                row.get(
                    "revenue_share_of_month"
                ),
                0,
            )

            product_rows.append(
                {
                    "product": row.get(
                        "product"
                    ),

                    "format": row.get(
                        "format"
                    ),

                    "product_sku": row.get(
                        "product_sku"
                    ),

                    "net_units": _safe_float(
                        row.get(
                            "net_units"
                        )
                    ),

                    "net_revenue_fcfa": _safe_float(
                        row.get(
                            "net_revenue_fcfa"
                        )
                    ),

                    "revenue_share_pct": round(
                        revenue_share * 100,
                        1,
                    ),
                }
            )

        top_product = (
            product_rows[0]
            if product_rows
            else None
        )

        # =============================================================
        # 5. WHATSAPP
        # =============================================================

        whatsapp = con.execute(
            """
            SELECT *
            FROM mart_whatsapp_monthly
            WHERE month = ?
            """,
            [target_month],
        ).df()

        whatsapp_data: dict[str, Any] = {}

        if not whatsapp.empty:

            row = whatsapp.iloc[0]

            whatsapp_data = {
                "orders": _safe_int(
                    row.get("orders")
                ),

                "delivered_orders": _safe_int(
                    row.get("delivered_orders")
                ),

                "cancelled_orders": _safe_int(
                    row.get("cancelled_orders")
                ),

                "pending_orders": _safe_int(
                    row.get("pending_orders")
                ),

                "total_units": _safe_int(
                    row.get("total_units")
                ),

                "bissap_units": _safe_int(
                    row.get("bissap_units")
                ),

                "gingembre_units": _safe_int(
                    row.get("gingembre_units")
                ),

                "bouye_units": _safe_int(
                    row.get("bouye_units")
                ),

                "delivered_known_amount_fcfa": _safe_float(
                    row.get(
                        "delivered_known_amount_fcfa"
                    )
                ),

                "delivered_amount_missing_orders": _safe_int(
                    row.get(
                        "delivered_amount_missing_orders"
                    )
                ),

                "delivered_outlier_amount_orders": _safe_int(
                    row.get(
                        "delivered_outlier_amount_orders"
                    )
                ),
            }

        # =============================================================
        # 6. DETERMINISTIC ATTENTION / POSITIVE POINTS
        # =============================================================

        attention_points: list[str] = []

        positive_points: list[str] = []

        # -------------------------------------------------------------
        # Sales decline
        # -------------------------------------------------------------

        if (
            revenue_growth_pct is not None
            and revenue_growth_pct < 0
        ):

            attention_points.append(
                "CA net en baisse par rapport "
                "au mois précédent."
            )

        # -------------------------------------------------------------
        # Incomplete sales coverage
        # -------------------------------------------------------------

        if (
            missing_sales_days is not None
            and _safe_float(missing_sales_days) > 0
        ):

            attention_points.append(
                "La couverture des ventes est "
                "incomplète sur le mois."
            )

        # -------------------------------------------------------------
        # Negative sentiment majority
        # -------------------------------------------------------------

        if (
            negative_count > positive_count
            and sentiment_total > 0
        ):

            attention_points.append(
                "Les commentaires négatifs "
                "dépassent les commentaires positifs."
            )

        # -------------------------------------------------------------
        # WhatsApp missing amounts
        # -------------------------------------------------------------

        if (
            whatsapp_data
            and whatsapp_data[
                "delivered_amount_missing_orders"
            ] > 0
        ):

            attention_points.append(
                "Certaines commandes WhatsApp "
                "livrées n'ont pas de montant exploitable."
            )

        # -------------------------------------------------------------
        # Sales increase
        # -------------------------------------------------------------

        if (
            revenue_growth_pct is not None
            and revenue_growth_pct > 0
        ):

            positive_points.append(
                "CA net en hausse par rapport "
                "au mois précédent."
            )

        # -------------------------------------------------------------
        # Positive sentiment majority
        # -------------------------------------------------------------

        if (
            positive_count > negative_count
            and sentiment_total > 0
        ):

            positive_points.append(
                "Les commentaires positifs "
                "sont majoritaires."
            )

        # =============================================================
        # 7. FORMATTED VALUES FOR REPORTING
        # =============================================================

        # -------------------------------------------------------------
        # Marketing
        # -------------------------------------------------------------

        formatted_channels = []

        for channel in channel_rows:

            formatted_channels.append(
                {
                    "channel": channel["channel"],

                    "spend": _format_fcfa(
                        channel["spend_fcfa"]
                    ),

                    "share": _format_pct(
                        channel["share_pct"]
                    ),

                    "planned_budget": _format_fcfa(
                        channel["planned_budget_fcfa"]
                    ),

                    "invoiced": _format_fcfa(
                        channel["invoiced_fcfa"]
                    ),

                    "variance": _format_fcfa(
                        channel["variance_fcfa"]
                    ),

                    "source_coverage": channel[
                        "source_coverage"
                    ],
                }
            )

        # -------------------------------------------------------------
        # Products
        # -------------------------------------------------------------

        formatted_products = []

        for product in product_rows:

            formatted_products.append(
                {
                    "product": product["product"],
                    "format": product["format"],
                    "product_sku": product["product_sku"],

                    "units": _format_number(
                        product["net_units"]
                    ),

                    "revenue": _format_fcfa(
                        product["net_revenue_fcfa"]
                    ),

                    "revenue_share": _format_pct(
                        product["revenue_share_pct"]
                    ),
                }
            )

        # -------------------------------------------------------------
        # WhatsApp
        # -------------------------------------------------------------

        formatted_whatsapp = {}

        if whatsapp_data:

            formatted_whatsapp = {
                "orders": _format_number(
                    whatsapp_data["orders"]
                ),

                "delivered_orders": _format_number(
                    whatsapp_data["delivered_orders"]
                ),

                "cancelled_orders": _format_number(
                    whatsapp_data["cancelled_orders"]
                ),

                "pending_orders": _format_number(
                    whatsapp_data["pending_orders"]
                ),

                "total_units": _format_number(
                    whatsapp_data["total_units"]
                ),

                "bissap_units": _format_number(
                    whatsapp_data["bissap_units"]
                ),

                "gingembre_units": _format_number(
                    whatsapp_data["gingembre_units"]
                ),

                "bouye_units": _format_number(
                    whatsapp_data["bouye_units"]
                ),

                "delivered_known_amount": _format_fcfa(
                    whatsapp_data[
                        "delivered_known_amount_fcfa"
                    ]
                ),

                "missing_amount_orders": _format_number(
                    whatsapp_data[
                        "delivered_amount_missing_orders"
                    ]
                ),

                "outlier_amount_orders": _format_number(
                    whatsapp_data[
                        "delivered_outlier_amount_orders"
                    ]
                ),
            }

        # =============================================================
        # 8. FINAL STRUCTURED BRIEF
        # =============================================================

        return {

            # ---------------------------------------------------------
            # Period
            # ---------------------------------------------------------

            "period": {

                "year": year,

                "month": month,

                "label": (
                    f"{month:02d}/{year}"
                ),

                "current_period_label": (
                    current_period_label
                ),

                "previous_period_label": (
                    previous_period_label
                ),
            },

            # ---------------------------------------------------------
            # Sales
            # ---------------------------------------------------------

            "sales": {

                # Raw values retained for programmatic validation.
                "revenue_fcfa": round(
                    revenue_fcfa,
                    0,
                ),

                "previous_revenue_fcfa": (
                    round(
                        previous_revenue_fcfa,
                        0,
                    )
                    if previous_revenue_fcfa is not None
                    else None
                ),

                "revenue_growth_pct": (
                    revenue_growth_pct
                ),

                "revenue_direction": (
                    revenue_direction
                ),

                "net_units_sold": _safe_int(
                    _scalar(
                        performance,
                        "net_units_sold",
                        0,
                    )
                ),

                "active_pos": _safe_int(
                    _scalar(
                        performance,
                        "active_pos",
                        0,
                    )
                ),

                "active_communes": _safe_int(
                    _scalar(
                        performance,
                        "active_communes",
                        0,
                    )
                ),

                "observed_sales_days": (
                    observed_sales_days
                ),

                "calendar_days": (
                    calendar_days
                ),

                "missing_sales_days": (
                    _safe_int(
                        missing_sales_days
                    )
                    if missing_sales_days is not None
                    else None
                ),

                "return_rate_revenue": (
                    _safe_float(
                        _scalar(
                            performance,
                            "return_rate_revenue",
                            None,
                        )
                    )
                    if _scalar(
                        performance,
                        "return_rate_revenue",
                        None,
                    ) is not None
                    else None
                ),

                # Human-readable values.
                "revenue_fcfa_formatted": (
                    _format_fcfa(
                        revenue_fcfa
                    )
                ),

                "previous_revenue_fcfa_formatted": (
                    _format_fcfa(
                        previous_revenue_fcfa
                    )
                ),

                "revenue_growth_pct_formatted": (
                    _format_pct(
                        revenue_growth_pct
                    )
                ),

                "net_units_sold_formatted": (
                    _format_number(
                        _scalar(
                            performance,
                            "net_units_sold",
                            0,
                        )
                    )
                ),

                "active_pos_formatted": (
                    _format_number(
                        _scalar(
                            performance,
                            "active_pos",
                            0,
                        )
                    )
                ),

                "active_communes_formatted": (
                    _format_number(
                        _scalar(
                            performance,
                            "active_communes",
                            0,
                        )
                    )
                ),

                # Deterministic statements.
                "revenue_statement": (
                    revenue_statement
                ),

                "data_quality_statement": (
                    data_quality_statement
                ),

                "comparison_caveat": (
                    (
                        f"Comparaison avec "
                        f"{previous_period_label}. "
                        f"{int(_safe_float(missing_sales_days))} "
                        f"jour(s) de vente non observé(s) "
                        f"sur {calendar_days}."
                    )
                    if (
                        missing_sales_days is not None
                        and _safe_float(
                            missing_sales_days
                        ) > 0
                    )
                    else (
                        f"Comparaison avec "
                        f"{previous_period_label}. "
                        "Tous les jours calendaires "
                        "du mois sont observés."
                    )
                ),
            },

            # ---------------------------------------------------------
            # Marketing
            # ---------------------------------------------------------

            "marketing": {

                "total_spend_fcfa": round(
                    total_spend_fcfa,
                    0,
                ),

                "total_spend_formatted": (
                    _format_fcfa(
                        total_spend_fcfa
                    )
                ),

                "channels": channel_rows,

                "channels_formatted": (
                    formatted_channels
                ),

                "top_spending_channel": (
                    top_spending_channel
                ),

                "principal_fait_marketing": (
                    principal_fait_marketing
                ),
            },

            # ---------------------------------------------------------
            # Customer Voice
            # ---------------------------------------------------------

            "customer_voice": {

                "comments_count": (
                    comments_count
                ),

                "unique_comments_count": (
                    unique_comments_count
                ),

                "positive_count": (
                    positive_count
                ),

                "negative_count": (
                    negative_count
                ),

                "neutral_count": (
                    neutral_count
                ),

                "spam_count": (
                    spam_count
                ),

                "sentiment_total": (
                    sentiment_total
                ),

                "positive_share_pct": (
                    positive_share_pct
                ),

                "negative_share_pct": (
                    negative_share_pct
                ),

                "neutral_share_pct": (
                    neutral_share_pct
                ),

                "sentiment_majority": (
                    sentiment_majority
                ),

                "top_themes": (
                    top_themes
                ),

                "principal_signal_client": (
                    principal_signal_client
                ),
            },

            # ---------------------------------------------------------
            # Products
            # ---------------------------------------------------------

            "products": {

                "top_products": (
                    product_rows
                ),

                "top_products_formatted": (
                    formatted_products
                ),

                "top_product": (
                    top_product
                ),
            },

            # ---------------------------------------------------------
            # WhatsApp
            # ---------------------------------------------------------

            "whatsapp": whatsapp_data,

            "whatsapp_formatted": (
                formatted_whatsapp
            ),

            # ---------------------------------------------------------
            # Deterministic points
            # ---------------------------------------------------------

            "attention_points": (
                attention_points
            ),

            "positive_points": (
                positive_points
            ),

            # ---------------------------------------------------------
            # Rules
            #
            # Kept temporarily for backward compatibility.
            # They will be removed from the LLM-facing payload
            # during the next step.
            # ---------------------------------------------------------

            "rules": {
                "causal_attribution": False,
                "llm_must_calculate_numbers": False,
                "llm_must_invent_missing_values": False,
            },
        }

    finally:
        con.close()

# ---------------------------------------------------------------------
# Manual test
# ---------------------------------------------------------------------

if __name__ == "__main__":

    import json

    # Exemple :
    # python -m ai.reporting.query_marts

    today = date.today()

    brief = build_monthly_brief(
        year=2026,
        month=2,
    )

    print(
        json.dumps(
            brief,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )