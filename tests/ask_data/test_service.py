from ai.ask_data.service import ask_data


def test_ask_data_montant_unique():
    answer = ask_data(
        "Combien avons-nous dépensé sur Meta en juin 2026 ?"
    )

    assert answer == "969.9 k FCFA"


def test_ask_data_par_canal():
    answer = ask_data(
        "Quel est le spend par canal ?"
    )

    assert "Meta : 6.95 M FCFA" in answer
    assert "TikTok : 4.21 M FCFA" in answer


def test_ask_data_periode_relative():
    answer = ask_data(
        "Donne moi les dépenses publicitaires par canal ces 3 derniers mois"
    )

    assert "Meta : 3.04 M FCFA" in answer
    assert "TikTok : 2.11 M FCFA" in answer
    assert "Google : 862.8 k FCFA" in answer