from __future__ import annotations

import pandas as pd

from .answer import RATIO_METRICS, format_answer, format_count, format_value
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
    "repartition_sentiment": ("le sentiment des clients", False),
    "themes_commentaires": ("les thèmes des commentaires", True),
    "commentaires_positifs": ("les commentaires positifs", True),
    "commentaires_negatifs": ("les commentaires négatifs", True),
    "commentaires_neutres": ("les commentaires neutres", True),
    "commentaires_total": ("le volume de commentaires", False),
    "commentaires_exploitables": ("les commentaires exploitables", True),
    "commentaires_spam": ("les commentaires indésirables (spam)", True),
    "sentiment_client": ("la part de commentaires négatifs", False),
    "taux_positifs": ("la part de commentaires positifs", False),
    "taux_spam": ("la part de spam dans les commentaires", False),
}

# Ce que l'on compte, pour « le mois qui compte le plus de … ».
COUNT_NOUNS = {
    "commentaires_positifs": "commentaires positifs",
    "commentaires_negatifs": "commentaires négatifs",
    "commentaires_neutres": "commentaires neutres",
    "commentaires_total": "commentaires",
    "commentaires_exploitables": "commentaires exploitables",
    "commentaires_spam": "commentaires indésirables (spam)",
}

# Composantes de la répartition du sentiment et des thèmes (couche sémantique).
SENTIMENT_LABELS = {
    "positifs": "Positif",
    "neutres": "Neutre",
    "negatifs": "Négatif",
}

THEME_LABELS = {
    "gout": "Goût",
    "prix": "Prix",
    "promotion": "Promotion",
    "disponibilite": "Disponibilité",
    "emballage": "Emballage",
    "sante": "Santé",
    "livraison": "Livraison",
    "service": "Service",
    "question_produit": "Questions produit",
    "autre": "Autre",
}

THEME_NOUNS = {
    "gout": "le goût",
    "prix": "le prix",
    "promotion": "les promotions",
    "disponibilite": "la disponibilité",
    "emballage": "l'emballage",
    "sante": "la santé",
    "livraison": "la livraison",
    "service": "le service",
    "question_produit": "les questions sur les produits",
}

SENTIMENT_CAVEAT = (
    "*Classement automatique des commentaires : à lire comme une tendance, "
    "pas comme une mesure exacte.*"
)

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

    if isinstance(channel, str):
        return f" sur {channel}"

    platform = intent.filters.get("platform")

    if isinstance(platform, str):
        return f" sur {platform}"

    if isinstance(platform, list):
        return f" sur {_join_and(platform)}"

    return ""


def _variation(current: float, previous: float) -> float | None:
    if pd.isna(current) or pd.isna(previous) or previous == 0:
        return None

    return (current - previous) / abs(previous)


def _trend(change: float) -> str:
    if abs(change) < STABLE_THRESHOLD:
        return "stable"

    direction = "en hausse" if change > 0 else "en baisse"
    return f"{direction} de {abs(change) * 100:.1f} %"


def _points(change: float) -> str:
    """Écart entre deux parts, en points : « en hausse de 2.4 points »."""
    if abs(change) < 0.005:
        return "stable"

    direction = "en hausse" if change > 0 else "en baisse"
    return f"{direction} de {abs(change) * 100:.1f} points"


def _pct(value: float) -> str:
    return f"{value * 100:.0f} %"


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

    if metric in COUNT_NOUNS:
        sentence = (
            f"{_period(intent, pd.DataFrame())}{_scope(intent)}, on compte "
            f"**{format_value(metric, value)} {COUNT_NOUNS[metric]}**"
        )
    else:
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
        # Une part se compare en points, un montant en pourcentage.
        trend = _points(value - previous) if metric in RATIO_METRICS else _trend(change)
        sentence += (
            f", {trend} par rapport à {previous_label} "
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
            f"{period}, {subject}{_scope(intent)} passe de "
            f"{format_value(metric, first[metric])} en {_month_label(first['month'])} à "
            f"{format_value(metric, last[metric])} en {_month_label(last['month'])} "
            f"(**{_points(last[metric] - first[metric])}**). Le niveau le plus élevé "
            f"est atteint en {_month_label(best['month'])} "
            f"({format_value(metric, best[metric])}), le plus bas en "
            f"{_month_label(worst['month'])} ({format_value(metric, worst[metric])})."
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

    if metric in COUNT_NOUNS:
        most = "le moins" if lowest else "le plus"
        noun = COUNT_NOUNS[metric]

        if dimension == "month":
            name = _month_label
            sentence = (
                f"Le mois qui compte {most} de {noun}{_scope(intent)} est "
                f"{name(pick['month'])}, avec {value}{share}."
            )
        else:
            name = _category
            sentence = (
                f"{_period(intent, data)}, {name(pick[dimension])} est "
                f"{DIMENSION_NOUNS.get(dimension, 'l’élément')} qui compte {most} "
                f"de {noun}, avec {value}{share}."
            )
    elif metric in RATIO_METRICS:
        level = "la plus faible" if lowest else "la plus élevée"

        if dimension == "month":
            name = _month_label
            sentence = (
                f"{_capitalize(subject)}{_scope(intent)} est {level} en "
                f"{name(pick['month'])}, avec {value}."
            )
        else:
            name = _category
            sentence = (
                f"{_period(intent, data)}, {subject} est {level} sur "
                f"{name(pick[dimension])}, avec {value}."
            )
    elif dimension == "month":
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
COMPARED_FILTERS = {"product": "product", "channel": "channel", "platform": "platform"}


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
# VOIX DU CLIENT
# ---------------------------------------------------------------------

def _ratio_by_category(intent: QueryIntent, data: pd.DataFrame, dimension: str) -> str:
    """Une part par plateforme (ou canal) : la plus élevée, la plus faible, le détail."""
    metric = intent.metric
    subject, _ = _subject(metric, intent)
    ranked = data.dropna(subset=[metric]).sort_values(metric, ascending=False)
    period = _period(intent, data)

    if len(ranked) == 1:
        row = ranked.iloc[0]
        return (
            f"{period}, {subject} sur {_category(row[dimension])} atteint "
            f"**{format_value(metric, row[metric])}**."
        )

    high, low = ranked.iloc[0], ranked.iloc[-1]
    sentence = (
        f"{period}, {subject} est la plus élevée sur {_category(high[dimension])} "
        f"(**{format_value(metric, high[metric])}**) et la plus faible sur "
        f"{_category(low[dimension])} (**{format_value(metric, low[metric])}**)."
    )

    if len(ranked) > 2:
        detail = [
            f"{_category(row[dimension])} {format_value(metric, row[metric])}"
            for _, row in ranked.iterrows()
        ]
        sentence += f" Détail : {', '.join(detail)}."

    return sentence


def _sentiment_shares(frame: pd.DataFrame, total: str) -> pd.DataFrame:
    """Parts de positifs et de négatifs pour chaque ligne d'un tableau agrégé."""
    shares = pd.DataFrame(index=frame.index)
    shares["positifs"] = frame["positifs"] / frame[total]
    shares["negatifs"] = frame["negatifs"] / frame[total]
    return shares.dropna()


def _sentiment(intent: QueryIntent, data: pd.DataFrame, previous=None) -> str:
    """Répartition positif / neutre / négatif, puis évolution et plateformes."""
    metric = intent.metric
    totals = data[[metric, *SENTIMENT_LABELS]].sum()
    total = totals[metric]

    if not total:
        return "Aucun commentaire exploitable sur cette période."

    positive, neutral, negative = (totals[name] for name in ("positifs", "neutres", "negatifs"))

    sentences = [
        f"{_period(intent, data)}{_scope(intent)} : **{format_count(total)} commentaires "
        f"exploitables** (hors spam), dont **{_pct(positive / total)} positifs** "
        f"({format_count(positive)}), {_pct(negative / total)} négatifs "
        f"({format_count(negative)}) et {_pct(neutral / total)} neutres "
        f"({format_count(neutral)})."
    ]

    if negative and positive > negative:
        sentences.append(
            f"Les avis positifs l'emportent : {positive / negative:.1f} commentaires "
            "positifs pour un négatif."
        )
    elif positive and negative > positive:
        sentences.append(
            f"Les avis négatifs l'emportent : {negative / positive:.1f} commentaires "
            "négatifs pour un positif."
        )
    elif positive == negative:
        sentences.append("Les avis positifs et négatifs sont aussi nombreux.")

    # Un seul mois : comparaison avec le mois précédent.
    if isinstance(previous, dict) and previous.get(metric):
        previous_share = previous["positifs"] / previous[metric]
        previous_label = _month_label(
            pd.Timestamp(intent.filters["month"] + "-01") - pd.DateOffset(months=1)
        )
        sentences.append(
            f"La part de positifs est {_points(positive / total - previous_share)} "
            f"par rapport à {previous_label} ({_pct(previous_share)})."
        )

    has_months = "month" in data.columns and data["month"].nunique() > 1
    has_platforms = "platform" in data.columns and data["platform"].nunique() > 1

    if has_months:
        monthly = _sentiment_shares(
            data.groupby("month")[[metric, *SENTIMENT_LABELS]].sum().sort_index(), metric
        )
        first_month, last_month = monthly.index[0], monthly.index[-1]
        start, end = monthly.loc[first_month, "positifs"], monthly.loc[last_month, "positifs"]

        if abs(end - start) < 0.01:
            sentences.append(
                f"La part de commentaires positifs reste stable autour de {_pct(end)} "
                f"{_between(first_month, last_month)}."
            )
        else:
            direction = "progresse" if end > start else "recule"
            sentences.append(
                f"La part de commentaires positifs {direction} de {_pct(start)} en "
                f"{_month_label(first_month)} à {_pct(end)} en {_month_label(last_month)} "
                f"(**{_points(end - start)}**)."
            )

        worst = monthly["negatifs"].idxmax()
        sentences.append(
            f"La part de négatifs la plus élevée est en {_month_label(worst)} "
            f"({_pct(monthly.loc[worst, 'negatifs'])})."
        )

    if has_platforms:
        platforms = _sentiment_shares(
            data.groupby("platform")[[metric, *SENTIMENT_LABELS]].sum(), metric
        )
        best = platforms["positifs"].idxmax()
        lowest = platforms["positifs"].idxmin()
        most_negative = platforms["negatifs"].idxmax()

        sentences.append(
            f"Par plateforme, {best} a la part de positifs la plus élevée "
            f"({_pct(platforms.loc[best, 'positifs'])}) et {lowest} la plus faible "
            f"({_pct(platforms.loc[lowest, 'positifs'])}). La part de négatifs est la "
            f"plus forte sur {most_negative} ({_pct(platforms.loc[most_negative, 'negatifs'])})."
        )

    if has_months and has_platforms:
        sentences.append("Le détail mois par mois figure dans le graphique.")

    sentences.append(SENTIMENT_CAVEAT)
    return " ".join(sentences)


def _themes(intent: QueryIntent, data: pd.DataFrame) -> str:
    """Sujets les plus abordés dans les commentaires exploitables."""
    metric = intent.metric
    total = data[metric].sum()
    totals = data[list(THEME_LABELS)].sum().sort_values(ascending=False)
    top = [name for name in totals.index if name in THEME_NOUNS and totals[name] > 0][:3]

    if not total or not top:
        return "Aucun thème n'est disponible sur cette période."

    items = [
        f"{THEME_NOUNS[name]} ({format_count(totals[name])}, {_pct(totals[name] / total)})"
        for name in top
    ]

    return (
        f"{_period(intent, data)}{_scope(intent)}, les sujets les plus abordés dans les "
        f"commentaires exploitables sont {_join_and(items)}."
    )


# ---------------------------------------------------------------------
# DESCRIPTION DE L'INTERPRÉTATION
# ---------------------------------------------------------------------

DIMENSION_LABELS = {
    "month": "par mois",
    "channel": "par canal",
    "product": "par produit",
    "format": "par format",
    "platform": "par plateforme",
}


def describe_intent(intent: QueryIntent) -> str:
    """Interprétation retenue, en clair : « chiffre d'affaires net, par produit, en juin 2026 »."""
    metrics = [intent.metric, *intent.other_metrics]
    parts = [_join_and([metric_subject(m) for m in metrics])]

    parts += [DIMENSION_LABELS.get(d, d) for d in intent.dimensions]

    for key, label in (("product", "produit"), ("channel", "canal"), ("platform", "plateforme")):
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

    data = result.copy()

    if "month" in data.columns:
        data["month"] = pd.to_datetime(data["month"])

    # Répartitions (composantes de la couche sémantique) : rédaction dédiée.
    if metric == "repartition_sentiment":
        return _sentiment(intent, data, previous)

    if metric == "themes_commentaires":
        return _themes(intent, data)

    if not dimensions:
        return _single_value(intent, result.iloc[0][metric], previous)

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

    if dimensions == others and len(others) == 1 and metric in RATIO_METRICS:
        return _ratio_by_category(intent, data, others[0])

    if len(others) == 1 and metric not in RATIO_METRICS:
        if "month" in dimensions:
            return _by_month_and_category(intent, data, others[0])

        return _by_category(intent, data, others[0])

    # Combinaison non prévue (ratios par catégorie, trois découpages…) :
    # on garde la liste ligne par ligne.
    return format_answer(intent, result)
