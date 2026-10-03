from __future__ import annotations

import re


MONTHS = {
    "janvier": "01",
    "février": "02",
    "fevrier": "02",
    "mars": "03",
    "avril": "04",
    "mai": "05",
    "juin": "06",
    "juillet": "07",
    "août": "08",
    "aout": "08",
    "septembre": "09",
    "octobre": "10",
    "novembre": "11",
    "décembre": "12",
    "decembre": "12",
}


def extract_month(question: str) -> str | None:
    """Extrait un mois explicite au format YYYY-MM."""
    text = question.lower()

    for month_name, month_number in MONTHS.items():
        match = re.search(
            rf"\b{month_name}\s+(\d{{4}})\b",
            text,
        )

        if match:
            year = match.group(1)
            return f"{year}-{month_number}"

    return None

# Valeur de month_of_year pour « le mois dernier » : le dernier mois
# présent dans les données, quel qu'il soit.
LATEST_MONTH = "dernier"


def mentions_latest_month(question: str) -> bool:
    """« le mois dernier », « le dernier mois », « ce mois-ci », « le mois le plus récent »."""
    text = question.lower()

    return re.search(
        r"\bmois dernier\b|\bdernier mois\b|\bmois le plus r[ée]cent\b"
        r"|\bce mois(?:-ci| ci)?\b",
        text,
    ) is not None


def extract_since(question: str) -> tuple[str | None, str | None]:
    """Point de départ d'une période ouverte.

    Retourne (YYYY-MM, None) pour « depuis mars 2026 », (None, MM) pour
    « depuis mars » ou « depuis le début de l'année » (année à résoudre),
    (None, None) sinon.
    """
    text = question.lower()

    if re.search(r"\bdepuis (?:le )?d[ée]but (?:de l'|d')ann[ée]e\b", text):
        return None, "01"

    names = "|".join(MONTHS)
    match = re.search(
        rf"\b(?:depuis|à partir de|a partir de)\s+(?:le mois de\s+|le début de\s+|le debut de\s+)?"
        rf"({names})(?:\s+(\d{{4}}))?\b",
        text,
    )

    if not match:
        return None, None

    month_number = MONTHS[match.group(1)]

    if match.group(2):
        return f"{match.group(2)}-{month_number}", None

    return None, month_number


def extract_month_without_year(question: str) -> str | None:
    """Extrait un mois cité sans année (« en mai ») au format MM."""
    text = question.lower()

    for month_name, month_number in MONTHS.items():
        if re.search(rf"\b{month_name}\b", text):
            return month_number

    return None

def validate_month(month: str) -> str:
    """Valide un mois au format YYYY-MM."""

    if not re.fullmatch(r"\d{4}-\d{2}", month):
        raise ValueError(
            f"Mois invalide : '{month}'. "
            "Format attendu : YYYY-MM."
        )

    year, month_number = month.split("-")

    month_int = int(month_number)

    if not 1 <= month_int <= 12:
        raise ValueError(
            f"Mois invalide : '{month}'. "
            "Le mois doit être compris entre 01 et 12."
        )

    return month

def previous_month(month: str) -> str:
    """Retourne le mois précédent au format YYYY-MM."""
    year, month_number = map(int, validate_month(month).split("-"))

    if month_number == 1:
        return f"{year - 1:04d}-12"

    return f"{year:04d}-{month_number - 1:02d}"

NUMBER_WORDS = {
    "un": 1, "deux": 2, "trois": 3, "quatre": 4, "cinq": 5, "six": 6,
    "sept": 7, "huit": 8, "neuf": 9, "dix": 10, "onze": 11, "douze": 12,
}

# « le dernier trimestre », « les deux derniers trimestres »…
PERIOD_LENGTHS = {
    "mois": 1,
    "trimestre": 3,
    "trimestres": 3,
    "semestre": 6,
    "semestres": 6,
}


def extract_relative_months(question: str) -> int | None:
    """
    Extrait une période relative, en nombre de mois :
    - (ces / les) 3 derniers mois, trois derniers mois
    - le dernier trimestre (3), les deux derniers trimestres (6)
    - le dernier semestre (6)
    """
    text = question.lower()

    number = rf"\d+|{'|'.join(NUMBER_WORDS)}"
    unit = "|".join(PERIOD_LENGTHS)

    match = re.search(
        rf"\b(?:(?:ces|les)\s+)?({number})\s+derni(?:er|ers|ère|ères)\s+({unit})\b",
        text,
    )

    if match:
        raw, period = match.groups()
        count = int(raw) if raw.isdigit() else NUMBER_WORDS[raw]
        months = count * PERIOD_LENGTHS[period]

        if months <= 0:
            raise ValueError(
                "Le nombre de mois doit être supérieur à 0."
            )

        return months

    # « en ce moment », « récemment »… : trois mois par défaut.
    if re.search(
        r"\ben ce moment\b|\bces derniers temps\b|\bces temps-ci\b"
        r"|\br[ée]cemment\b|\bactuellement\b",
        text,
    ):
        return 3

    # « ces derniers mois » sans nombre : trois mois par défaut.
    if re.search(r"\b(?:ces|les|des)\s+derniers\s+mois\b", text):
        return 3

    # « le dernier trimestre », « ce dernier semestre » (mais pas « le mois dernier »)
    match = re.search(r"\bderni(?:er|ère)\s+(trimestre|semestre)\b", text)

    if match:
        return PERIOD_LENGTHS[match.group(1)]

    return None

if __name__ == "__main__":
    print("\nValidation des mois :")

    tests = [
        "2026-06",
        "2025-12",
        "2026-13",
        "2026-00",
        "2026-6",
        "DROP TABLE",
        "01-2026",
    ]

    for test in tests:
        try:
            print(f"{test!r} -> {validate_month(test)}")
        except ValueError as exc:
            print(f"{test!r} -> ERREUR : {exc}")