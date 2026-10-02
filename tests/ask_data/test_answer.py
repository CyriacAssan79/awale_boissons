import pandas as pd

from ai.ask_data.answer import format_answer
from ai.ask_data.intent import build_intent


def test_answer_montant_unique():
    intent = build_intent(
        question="Quel est le CA net en juin 2026 ?",
        metric="ca_net",
        month="2026-06",
    )

    result = pd.DataFrame({
        "ca_net": [14125053.0],
    })

    answer = format_answer(intent, result)

    assert answer == "14.13 M FCFA"


def test_answer_par_canal():
    intent = build_intent(
        question="Quel est le spend par canal ?",
        metric="spend_marketing",
        dimension="channel",
    )

    result = pd.DataFrame({
        "channel": ["Meta", "Google"],
        "spend_marketing": [6953100.0, 1782501.0],
    })

    answer = format_answer(intent, result)

    assert "Meta : 6.95 M FCFA" in answer
    assert "Google : 1.78 M FCFA" in answer


def test_answer_multi_dimensions():
    intent = build_intent(
        question="Quel est le mix produit par mois et par produit ?",
        metric="mix_produit",
        dimensions=["month", "product"],
    )

    result = pd.DataFrame({
        "month": pd.to_datetime(["2026-01-01"]),
        "product": ["bissap"],
        "mix_produit": [12651685.0],
    })

    answer = format_answer(intent, result)

    assert "2026-01" in answer
    assert "bissap" in answer
    assert "12.65 M FCFA" in answer


def test_answer_resultat_vide():
    intent = build_intent(
        question="Quel est le CA net en juin 2026 ?",
        metric="ca_net",
        month="2026-06",
    )

    result = pd.DataFrame(columns=["ca_net"])

    answer = format_answer(intent, result)

    assert answer == "Aucune donnée disponible pour cette question."