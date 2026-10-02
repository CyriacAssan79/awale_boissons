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

def extract_relative_months(question: str) -> int | None:
    """
    Extrait une période relative du type :
    - 3 derniers mois
    - ces 3 derniers mois
    - les 3 derniers mois
    - 3 derniers mois
    """
    text = question.lower()

    patterns = [
        r"\b(?:ces|les)?\s*(\d+)\s+derniers?\s+mois\b",
    ]

    for pattern in patterns:
        match = re.search(pattern, text)

        if match:
            months = int(match.group(1))

            if months <= 0:
                raise ValueError(
                    "Le nombre de mois doit être supérieur à 0."
                )

            return months

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