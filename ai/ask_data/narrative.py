from __future__ import annotations

import pandas as pd

from .answer import RATIO_METRICS, format_answer, format_value
from .intent import QueryIntent


# Les phrases décrivent ce que montrent les données, jamais pourquoi :
# aucune tournure causale (« grâce à », « à cause de »…).

MONTH_NAMES = [
    "janvier", "février", "mars", "avril", "mai", "juin",
    "juillet", "août", "septembre", "octobre", "novembre", "décembre",
]

# Sujet de la phrase et accord du verbe pour chaque métrique.
METRIC_SUBJECTS = {
    "ca_net": ("le chiffre d'affaires net", False),
    "spend_marketing": ("les dépenses marketing", True),
    "mix_produit": ("le chiffre d'affaires des points de vente", False),
}

# Nom du découpage dans une phrase de classement.
DIMENSION_NOUNS = {
    "channel": "le canal",
    "product": "le produit",
    "format": "le format",
    "platform": "la plateforme",
    "commune": "la commune",
}

# Variation sous laquelle on parle de stabilité.
STABLE_THRESHOLD = 0.01


# ---------------------------------------------------------------------
# OUTILS DE RÉDACTION
# ---------------------------------------------------------------------

def _subject(metric: str, intent: QueryIntent | None = None) -> tuple[str, bool]:
    product = intent.filters.get("product") if intent else None

    # « le chiffre d'affaires du bissap »
    if isinstance(product, str) and metric == "mix_produit":
        return f"le chiffre d'affaires du {product}", False

    return METRIC_SUBJECTS.get(metric, (f"la valeur de « {metric} »", False))


def metric_subject(metric: str) -> str:
    """« le chiffre d'affaires net », « les dépenses marketing »…"""
    return _subject(metric)[0]


def _verb(singular: str, plural: str, is_plural: bool) -> str:
    return plural if is_plural else singular


def _capitalize(text: str) -> str:
    return text[:1].upper() + text[1:]


def _month_label(value) -> str:
    month = pd.Timestamp(value)
    return f"{MONTH_NAMES[month.month - 1]} {month.year}"


def _month_range(months: pd.Series) -> str:
    """« De janvier à juin 2026 » ou « De décembre 2025 à février 2026 »."""
    first, last = pd.Timestamp(months.min()), pd.Timestamp(months.max())

    if first == last:
        return f"En {_month_label(first)}"

    start = MONTH_NAMES[first.month - 1] if first.year == last.year else _month_label(first)

    # Élision : « D'avril », « D'août », « D'octobre ».
    de = "D'" if start[0] in "aeiouy" else "De "

    return f"{de}{start} à {_month_label(last)}"


def _between(first, last) -> str:
    """« entre janvier et juin 2026 » ou « entre décembre 2025 et février 2026 »."""
    first, last = pd.Timestamp(first), pd.Timestamp(last)

    if first.year == last.year:
        return f"entre {MONTH_NAMES[first.month - 1]} et {_month_label(last)}"

    return f"entre {_month_label(first)} et {_month_label(last)}"


def _period(intent: QueryIntent, result: pd.DataFrame) -> str:
    """Période couverte par la réponse, en début de phrase."""
    if "month" in intent.filters:
        return f"En {_month_label(intent.filters['month'] + '-01')}"

    if "month" in result.columns and result["month"].notna().any():
        return _month_range(result["month"])

    if "since" in intent.filters:
        return f"Depuis {_month_label(intent.filters['since'] + '-01')}"

    if intent.relative_months:
        return f"Sur les {intent.relative_months} derniers mois"

    return "Sur l'ensemble de la période"


def _scope(intent: QueryIntent) -> str:
    channel = intent.filters.get("channel")
    return f" sur {channel}" if isinstance(channel, str) else ""


def _variation(current: float, previous: float) -> float | None:
    if pd.isna(current) or pd.isna(previous) or previous == 0:
        return None

    return (current - previous) / abs(previous)


def _trend(change: float) -> str:
    if abs(change) < STABLE_THRESHOLD:
        return "stable"

    direction = "en hausse" if change > 0 else "en baisse"
    return f"{direction} de {abs(change) * 100:.1f} %"


def _share(value: float, total: float) -> str:
    if not total or not value:
        return ""

    return f", soit {value / total * 100:.0f} % du total"


def _category(value) -> str:
    return _capitalize(str(value))


# ---------------------------------------------------------------------
# TYPES DE RÉPONSES
# ---------------------------------------------------------------------

def _single_value(
    intent: QueryIntent,
    value: float,
    previous: float | None,
) -> str:
    """Une seule valeur, comparée au mois précédent si elle est connue."""
    metric = intent.metric
    subject, plural = _subject(metric, intent)

    sentence = (
        f"{_period(intent, pd.DataFrame())}, {subject}{_scope(intent)} "
        f"{_verb('atteint', 'atteignent', plural)} "
        f"**{format_value(metric, value)}**"
    )

    change = _variation(value, previous) if previous is not None else None

    if change is not None:
        previous_label = _month_label(
            pd.Timestamp(intent.filters["month"] + "-01") - pd.DateOffset(months=1)
        )
        sentence += (
            f", {_trend(change)} par rapport à {previous_label} "
            f"({format_value(metric, previous)})"
        )

    return sentence + "."


def _by_month(intent: QueryIntent, data: pd.DataFrame) -> str:
    """Série mensuelle : tendance d'abord, puis dernier mois, puis total et extrêmes."""
    metric = intent.metric
    subject, plural = _subject(metric, intent)

    data = data.dropna(subset=[metric]).sort_values("month")
    best = data.loc[data[metric].idxmax()]
    worst = data.loc[data[metric].idxmin()]
    first, last = data.iloc[0], data.iloc[-1]
    period = _month_range(data["month"])

    if metric in RATIO_METRICS:
        return (
            f"{period}, {subject}{_scope(intent)} "
            f"{_verb('varie', 'varient', plural)} entre "
            f"**{format_value(metric, worst[metric])}** et "
            f"**{format_value(metric, best[metric])}**."
        )

    sentences = []

    # 1. Tendance sur la période : la réponse à « ça monte ou ça baisse ? ».
    change = _variation(last[metric], first[metric])

    if change is not None:
        sentences.append(
            f"{period}, {subject}{_scope(intent)} {_verb('passe', 'passent', plural)} de "
            f"{format_value(metric, first[metric])} à "
            f"{format_value(metric, last[metric])} (**{_trend(change)}**)."
        )

    # 2. Dernier mois par rapport au précédent.
    if len(data) >= 3:
        previous = data.iloc[-2]
        recent = _variation(last[metric], previous[metric])

        if recent is not None:
            sentences.append(
                f"Sur le dernier mois, {_month_label(last['month'])} est "
                f"{_trend(recent)} par rapport à {_month_label(previous['month'])} "
                f"({format_value(metric, previous[metric])})."
            )

    # 3. Total et extrêmes.
    total_intro = "Au total" if sentences else period
    sentences.append(
        f"{total_intro}, {subject}{_scope(intent)} "
        f"{_verb('totalise', 'totalisent', plural)} "
        f"**{format_value(metric, data[metric].sum())}**."
    )

    if len(data) >= 2:
        sentences.append(
            f"Le mois le plus élevé est {_month_label(best['month'])} "
            f"({format_value(metric, best[metric])}), le plus faible "
            f"{_month_label(worst['month'])} ({format_value(metric, worst[metric])})."
        )

    return " ".join(sentences)


def _by_category(intent: QueryIntent, data: pd.DataFrame, dimension: str) -> str:
    """Découpage par canal, produit… : total, premier, second, dernier."""
    metric = intent.metric
    subject, plural = _subject(metric, intent)

    ranked = (
        data.groupby(dimension, as_index=False)[metric]
        .sum()
        .sort_values(metric, ascending=False)
        .reset_index(drop=True)
    )
    total = ranked[metric].sum()
    period = _period(intent, data)

    first = ranked.iloc[0]
    sentences = [
        f"{period}, {subject}{_scope(intent)} "
        f"{_verb('totalise', 'totalisent', plural)} "
        f"**{format_value(metric, total)}**."
    ]

    # Pour le mix, les parts sont données juste après (« Répartition : … »).
    share = "" if metric == "mix_produit" else _share(first[metric], total)
    lead = (
        f"{_category(first[dimension])} arrive en tête avec "
        f"**{format_value(metric, first[metric])}**{share}"
    )

    if len(ranked) > 1:
        second = ranked.iloc[1]
        lead += (
            f", devant {_category(second[dimension])} "
            f"({format_value(metric, second[metric])})"
        )

    sentences.append(lead + ".")

    # Mix produit : la répartition complète est l'information attendue.
    if metric == "mix_produit" and total and len(ranked) > 1:
        shares = [
            f"{_category(row[dimension])} {row[metric] / total * 100:.0f} %"
            for _, row in ranked.iterrows()
        ]
        sentences.append(f"Répartition : {', '.join(shares)}.")

    elif len(ranked) > 2:
        last = ranked.iloc[-1]
        sentences.append(
            f"{_category(last[dimension])} ferme la marche "
            f"({format_value(metric, last[metric])})."
        )

    return " ".join(sentences)


def _share_trend(data: pd.DataFrame, dimension: str, metric: str) -> str:
    """Évolution de la part du premier élément entre le premier et le dernier mois."""
    shares = data.pivot_table(
        index="month", columns=dimension, values=metric, aggfunc="sum"
    )
    shares = shares.div(shares.sum(axis=1), axis=0).sort_index()

    lead = shares.sum().idxmax()
    first_month, last_month = shares.index[0], shares.index[-1]
    start, end = shares.loc[first_month, lead], shares.loc[last_month, lead]
    name = _category(lead)

    if abs(end - start) < 0.01:
        return (
            f"La part de {name} reste stable autour de {end * 100:.0f} % "
            f"{_between(first_month, last_month)}."
        )

    direction = "monte" if end > start else "recule"
    return (
        f"La part de {name} {direction} de {start * 100:.0f} % en "
        f"{_month_label(first_month)} à {end * 100:.0f} % en {_month_label(last_month)}."
    )


def _by_month_and_category(
    intent: QueryIntent,
    data: pd.DataFrame,
    dimension: str,
) -> str:
    """Mois × catégorie : répartition globale puis meilleur et moins bon mois."""
    metric = intent.metric

    summary = _by_category(intent, data, dimension)

    monthly = data.groupby("month", as_index=False)[metric].sum()

    if len(monthly) < 2:
        return summary

    if metric == "mix_produit":
        summary += " " + _share_trend(data, dimension, metric)

    best = monthly.loc[monthly[metric].idxmax()]
    worst = monthly.loc[monthly[metric].idxmin()]

    return (
        f"{summary} Le mois le plus élevé est {_month_label(best['month'])} "
        f"({format_value(metric, best[metric])}), le plus faible "
        f"{_month_label(worst['month'])} ({format_value(metric, worst[metric])}). "
        "Le détail mois par mois figure dans le graphique."
    )


def _ranking(intent: QueryIntent, data: pd.DataFrame, dimension: str) -> str:
    """Réponse à « quel canal / produit / mois … le plus (ou le moins) »."""
    metric = intent.metric
    subject, _ = _subject(metric, intent)
    lowest = intent.comparison == "min"

    ranked = (
        data.groupby(dimension, as_index=False)[metric]
        .sum()
        .sort_values(metric, ascending=lowest)
        .reset_index(drop=True)
    )
    pick, others = ranked.iloc[0], ranked.iloc[1:]
    total = ranked[metric].sum()
    share = "" if metric in RATIO_METRICS else _share(pick[metric], total)
    value = f"**{format_value(metric, pick[metric])}**"

    if dimension == "month":
        name = _month_label
        sentence = (
            f"Le mois le plus {'faible' if lowest else 'élevé'} pour {subject}"
            f"{_scope(intent)} est {name(pick['month'])}, avec {value}{share}."
        )
    else:
        name = _category
        noun = DIMENSION_NOUNS.get(dimension, "l'élément")
        sentence = (
            f"{_period(intent, data)}, {name(pick[dimension])} est {noun} qui pèse "
            f"{'le moins' if lowest else 'le plus'} dans {subject}{_scope(intent)}, "
            f"avec {value}{share}."
        )

    if not others.empty:
        followers = [
            f"{name(row[dimension])} ({format_value(metric, row[metric])})"
            for _, row in others.head(2).iterrows()
        ]
        lead = "Viennent ensuite" if lowest else "Suivent"
        sentence += f" {lead} {' et '.join(followers)}."

    return sentence


# Filtre correspondant à chaque découpage comparable.
COMPARED_FILTERS = {"product": "product", "channel": "channel"}


def _compared_items(intent: QueryIntent, dimension: str) -> list[str] | None:
    """Éléments à comparer, quand la question en cite plusieurs."""
    value = intent.filters.get(COMPARED_FILTERS.get(dimension, ""))
    return value if isinstance(value, list) else None


def _item_name(dimension: str, value) -> str:
    """« le bissap », « Meta »."""
    return f"le {value}" if dimension == "product" else str(value)


def _compare(intent: QueryIntent, data: pd.DataFrame, dimension: str) -> str:
    """« Compare le bissap et le gingembre » : écart, rapport, mois par mois."""
    metric = intent.metric
    subject, _ = _subject(metric, intent)

    totals = (
        data.groupby(dimension, as_index=False)[metric]
        .sum()
        .sort_values(metric, ascending=False)
        .reset_index(drop=True)
    )

    if len(totals) < 2:
        return _by_category(intent, data, dimension)

    lead, second = totals.iloc[0], totals.iloc[1]
    lead_name = _item_name(dimension, lead[dimension])
    second_name = _item_name(dimension, second[dimension])
    intro = f"{_period(intent, data)}, pour {subject}"

    if len(totals) == 2 and lead[metric] == second[metric]:
        return (
            f"{intro}, {lead_name} et {second_name} font jeu égal : "
            f"**{format_value(metric, lead[metric])}** chacun."
        )

    if len(totals) == 2:
        sentence = (
            f"{intro}, {lead_name} devance {second_name} : "
            f"**{format_value(metric, lead[metric])}** contre "
            f"**{format_value(metric, second[metric])}**, soit un écart de "
            f"{format_value(metric, lead[metric] - second[metric])}"
        )

        if second[metric] > 0:
            sentence += f" ({lead[metric] / second[metric]:.1f} fois plus)"

        sentence += "."
    else:
        followers = [
            f"{_item_name(dimension, row[dimension])} ({format_value(metric, row[metric])})"
            for _, row in totals.iloc[1:].iterrows()
        ]
        sentence = (
            f"{intro}, {lead_name} arrive en tête avec "
            f"**{format_value(metric, lead[metric])}**, devant "
            f"{_join_and(followers)}."
        )

    # Mois par mois : le premier est-il toujours devant le deuxième ?
    if "month" in data.columns and data["month"].nunique() > 1:
        monthly = data.pivot_table(
            index="month", columns=dimension, values=metric, aggfunc="sum"
        )
        both = monthly[[lead[dimension], second[dimension]]].dropna()
        ahead = int((both[lead[dimension]] > both[second[dimension]]).sum())

        if ahead == len(both):
            sentence += f" {_capitalize(lead_name)} est devant chaque mois."
        else:
            sentence += (
                f" {_capitalize(lead_name)} est devant {ahead} mois "
                f"sur {len(both)}."
            )

        sentence += " Le détail mois par mois figure dans le graphique."

    return sentence


def _join_and(items: list[str]) -> str:
    return items[0] if len(items) == 1 else ", ".join(items[:-1]) + " et " + items[-1]


# ---------------------------------------------------------------------
# DESCRIPTION DE L'INTERPRÉTATION
# ---------------------------------------------------------------------

DIMENSION_LABELS = {
    "month": "par mois",
    "channel": "par canal",
    "product": "par produit",
    "format": "par format",
}


def describe_intent(intent: QueryIntent) -> str:
    """Interprétation retenue, en clair : « chiffre d'affaires net, par produit, en juin 2026 »."""
    metrics = [intent.metric, *intent.other_metrics]
    parts = [_join_and([metric_subject(m) for m in metrics])]

    parts += [DIMENSION_LABELS.get(d, d) for d in intent.dimensions]

    for key, label in (("product", "produit"), ("channel", "canal")):
        value = intent.filters.get(key)

        if isinstance(value, list):
            parts.append(f"{label}s : {_join_and([str(v) for v in value])}")
        elif value:
            parts.append(f"{label} : {value}")

    filters = intent.filters

    if "month" in filters:
        parts.append(f"en {_month_label(filters['month'] + '-01')}")
    elif "month_of_year" in filters:
        month = filters["month_of_year"]
        parts.append(
            "dernier mois disponible" if not month.isdigit()
            else f"en {MONTH_NAMES[int(month) - 1]} (dernière année disponible)"
        )
    elif "since" in filters:
        parts.append(f"depuis {_month_label(filters['since'] + '-01')}")
    elif "since_month_of_year" in filters:
        parts.append(f"depuis {MONTH_NAMES[int(filters['since_month_of_year']) - 1]}")
    elif intent.relative_months:
        parts.append(f"{intent.relative_months} derniers mois")
    else:
        parts.append("toute la période")

    if intent.comparison == "max":
        parts.append("le plus élevé")
    elif intent.comparison == "min":
        parts.append("le plus faible")

    return _capitalize(", ".join(parts))


# ---------------------------------------------------------------------
# POINT D'ENTRÉE
# ---------------------------------------------------------------------

def narrate(
    intent: QueryIntent,
    result: pd.DataFrame,
    previous: float | None = None,
) -> str:
    """Rédige une réponse en phrases à partir du résultat DuckDB.

    `previous` : valeur du mois précédent, pour une question portant sur un
    seul mois (comparaison « en hausse de … par rapport à … »).
    """
    metric = intent.metric

    if result.empty or metric is None or metric not in result.columns:
        return format_answer(intent, result)

    if result[metric].isna().all():
        return "Aucune donnée disponible pour cette question."

    dimensions = [d for d in intent.dimensions if d in result.columns]

    if not dimensions:
        return _single_value(intent, result.iloc[0][metric], previous)

    data = result.copy()

    if "month" in data.columns:
        data["month"] = pd.to_datetime(data["month"])

    others = [d for d in dimensions if d != "month"]

    # Plusieurs produits ou canaux cités : phrase de comparaison.
    for dimension in others:
        if _compared_items(intent, dimension) and metric not in RATIO_METRICS:
            return _compare(intent, data, dimension)

    if intent.comparison in ("min", "max"):
        ranked_by = others[0] if others else "month"

        # Un ratio ne s'additionne pas : pas de classement sur deux découpages.
        if metric not in RATIO_METRICS or len(dimensions) == 1:
            return _ranking(intent, data, ranked_by)

    if dimensions == ["month"]:
        # Un seul mois (ex. « résumé du CA en juin ») : phrase simple.
        if data[metric].notna().sum() == 1:
            return _single_value(intent, data[metric].dropna().iloc[0], None)

        return _by_month(intent, data)

    if len(others) == 1 and metric not in RATIO_METRICS:
        if "month" in dimensions:
            return _by_month_and_category(intent, data, others[0])

        return _by_category(intent, data, others[0])

    # Combinaison non prévue (ratios par catégorie, trois découpages…) :
    # on garde la liste ligne par ligne.
    return format_answer(intent, result)
