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

def test_run_ask_data_redige_une_phrase():
    from ai.ask_data.service import run_ask_data

    response = run_ask_data("Quel est le CA net en juin 2026 ?")

    assert response.narrative == (
        "En juin 2026, le chiffre d'affaires net atteint **14.13 M FCFA**, "
        "en hausse de 13.3 % par rapport à mai 2026 (12.47 M FCFA)."
    )


def test_run_ask_data_produit_mois_sans_annee():
    from ai.ask_data.service import run_ask_data

    response = run_ask_data("Le bissap a rapporté combien en mai ?")

    assert response.intent.filters == {"product": "bissap", "month": "2026-05"}
    assert response.narrative.startswith(
        "En mai 2026, le chiffre d'affaires du bissap atteint **9.13 M FCFA**"
    )


def test_run_ask_data_mois_absent_des_donnees():
    from ai.ask_data.service import run_ask_data

    response = run_ask_data("Le bissap a rapporté combien en décembre ?")

    assert response.error is None
    assert response.narrative == "Aucune donnée n'est disponible pour décembre."


def test_run_ask_data_mois_dernier():
    from ai.ask_data.service import run_ask_data

    response = run_ask_data("Quel est le chiffre d'affaires du mois dernier ?")

    # Dernier mois présent dans les données.
    assert response.intent.filters == {"month": "2026-06"}
    assert response.narrative.startswith("En juin 2026,")


def test_run_ask_data_depuis_janvier():
    from ai.ask_data.service import run_ask_data

    response = run_ask_data("Fais-moi un résumé du chiffre d'affaires depuis janvier.")

    assert response.intent.filters == {"since": "2026-01"}
    assert response.narrative.startswith("De janvier à juin 2026")


def test_run_ask_data_deux_metriques():
    from ai.ask_data.service import run_ask_data

    response = run_ask_data(
        "Résume-moi les ventes et les dépenses marketing des derniers mois."
    )

    first, second = response.narrative.split("\n\n")

    assert "le chiffre d'affaires net" in first
    assert "les dépenses marketing" in second
    assert len(response.extras) == 1
    assert response.extras[0].intent.metric == "spend_marketing"


def test_run_ask_data_metrique_supplementaire_incompatible():
    from ai.ask_data.service import run_ask_data

    response = run_ask_data("Les ventes et les dépenses par produit")

    assert response.error is None
    assert "Je ne peux pas présenter les dépenses marketing de la même façon" in response.narrative
    assert response.extras == []
