import pandas as pd

from ai.ask_data.intent import build_intent
from ai.ask_data.narrative import narrate
from ai.ask_data.periods import previous_month


def test_previous_month():
    assert previous_month("2026-06") == "2026-05"
    assert previous_month("2026-01") == "2025-12"


def test_valeur_unique_avec_comparaison():
    intent = build_intent(
        question="Quel est le CA net en juin 2026 ?",
        metric="ca_net",
        month="2026-06",
    )
    result = pd.DataFrame({"ca_net": [14125053.0]})

    answer = narrate(intent, result, previous=12470263.0)

    assert answer.startswith("En juin 2026, le chiffre d'affaires net atteint")
    assert "**14.13 M FCFA**" in answer
    assert "en hausse de 13.3 % par rapport à mai 2026 (12.47 M FCFA)" in answer


def test_valeur_unique_sans_mois_precedent():
    intent = build_intent(
        question="Quel est le CA net en janvier 2026 ?",
        metric="ca_net",
        month="2026-01",
    )
    result = pd.DataFrame({"ca_net": [17646533.0]})

    answer = narrate(intent, result)

    assert answer == "En janvier 2026, le chiffre d'affaires net atteint **17.65 M FCFA**."


def test_valeur_unique_canal_accord_pluriel():
    intent = build_intent(
        question="Combien avons-nous dépensé sur Meta en juin 2026 ?",
        metric="spend_marketing",
        month="2026-06",
        channel="Meta",
    )
    result = pd.DataFrame({"spend_marketing": [969900.0]})

    answer = narrate(intent, result, previous=969900.0)

    assert "les dépenses marketing sur Meta atteignent **969.9 k FCFA**" in answer
    assert "stable par rapport à mai 2026" in answer


def test_serie_mensuelle():
    intent = build_intent(
        question="Quel est le CA net par mois ?",
        metric="ca_net",
        dimension="month",
    )
    result = pd.DataFrame({
        "month": pd.to_datetime(["2026-01-01", "2026-02-01", "2026-03-01"]),
        "ca_net": [10_000_000.0, 5_000_000.0, 12_000_000.0],
    })

    answer = narrate(intent, result)

    # La tendance vient en premier.
    assert answer.startswith(
        "De janvier à mars 2026, le chiffre d'affaires net passe de "
        "10.00 M FCFA à 12.00 M FCFA (**en hausse de 20.0 %**)."
    )
    assert (
        "Sur le dernier mois, mars 2026 est en hausse de 140.0 % "
        "par rapport à février 2026 (5.00 M FCFA)."
    ) in answer
    assert "totalise **27.00 M FCFA**" in answer
    assert "Le mois le plus élevé est mars 2026 (12.00 M FCFA)" in answer
    assert "le plus faible février 2026 (5.00 M FCFA)" in answer


def test_serie_mensuelle_elision():
    intent = build_intent(
        question="Quel est le CA net par mois ?",
        metric="ca_net",
        dimension="month",
    )
    result = pd.DataFrame({
        "month": pd.to_datetime(["2026-04-01", "2026-05-01"]),
        "ca_net": [6_000_000.0, 12_000_000.0],
    })

    assert narrate(intent, result).startswith("D'avril à mai 2026")


def test_un_seul_mois_avec_decoupage_mensuel():
    intent = build_intent(
        question="Résumé du CA en juin 2026",
        metric="ca_net",
        dimension="month",
        month="2026-06",
    )
    result = pd.DataFrame({
        "month": pd.to_datetime(["2026-06-01"]),
        "ca_net": [14_125_053.0],
    })

    answer = narrate(intent, result)

    assert answer == "En juin 2026, le chiffre d'affaires net atteint **14.13 M FCFA**."


def test_decoupage_par_canal():
    intent = build_intent(
        question="Quel est le spend par canal ?",
        metric="spend_marketing",
        dimension="channel",
    )
    result = pd.DataFrame({
        "channel": ["Google", "Meta", "TikTok"],
        "spend_marketing": [1_000_000.0, 6_000_000.0, 3_000_000.0],
    })

    answer = narrate(intent, result)

    assert "totalisent **10.00 M FCFA**" in answer
    assert "Meta arrive en tête avec **6.00 M FCFA**, soit 60 % du total" in answer
    assert "devant TikTok (3.00 M FCFA)" in answer
    assert "Google ferme la marche (1.00 M FCFA)" in answer


def test_decoupage_mois_et_produit():
    intent = build_intent(
        question="Quel est le mix produit par mois et par produit ?",
        metric="mix_produit",
        dimensions=["month", "product"],
    )
    result = pd.DataFrame({
        "month": pd.to_datetime(["2026-01-01"] * 2 + ["2026-02-01"] * 2),
        "product": ["bissap", "bouye"] * 2,
        "mix_produit": [8_000_000.0, 1_000_000.0, 6_000_000.0, 1_000_000.0],
    })

    answer = narrate(intent, result)

    assert answer.startswith("De janvier à février 2026")
    assert "Bissap arrive en tête avec **14.00 M FCFA**" in answer
    assert "Répartition : Bissap 88 %, Bouye 12 %." in answer
    assert "Le mois le plus élevé est janvier 2026 (9.00 M FCFA)" in answer
    # Une phrase de synthèse, pas une ligne par mois et par produit.
    assert "\n" not in answer


def test_aucune_tournure_causale():
    intent = build_intent(
        question="Quel est le CA net par mois ?",
        metric="ca_net",
        dimension="month",
    )
    result = pd.DataFrame({
        "month": pd.to_datetime(["2026-01-01", "2026-02-01"]),
        "ca_net": [10_000_000.0, 5_000_000.0],
    })

    answer = narrate(intent, result).lower()

    for term in ["grâce", "à cause", "cause", "parce que", "en raison"]:
        assert term not in answer


def test_resultat_vide():
    intent = build_intent(
        question="Quel est le CA net en juin 2026 ?",
        metric="ca_net",
        month="2026-06",
    )

    answer = narrate(intent, pd.DataFrame(columns=["ca_net"]))

    assert answer == "Aucune donnée disponible pour cette question."


def test_classement_canal_le_plus():
    intent = build_intent(
        question="Donne moi le canal qui consomme le plus dans le budget",
        metric="spend_marketing",
        dimension="channel",
        comparison="max",
    )
    result = pd.DataFrame({
        "channel": ["Google", "Meta", "TikTok"],
        "spend_marketing": [1_000_000.0, 6_000_000.0, 3_000_000.0],
    })

    answer = narrate(intent, result)

    assert answer.startswith(
        "Sur l'ensemble de la période, Meta est le canal qui pèse le plus "
        "dans les dépenses marketing, avec **6.00 M FCFA**, soit 60 % du total."
    )
    assert "Suivent TikTok (3.00 M FCFA) et Google (1.00 M FCFA)." in answer


def test_classement_canal_le_moins_valeur_nulle():
    intent = build_intent(
        question="Quel canal dépense le moins ?",
        metric="spend_marketing",
        dimension="channel",
        comparison="min",
    )
    result = pd.DataFrame({
        "channel": ["Activation terrain", "Meta"],
        "spend_marketing": [0.0, 6_000_000.0],
    })

    answer = narrate(intent, result)

    assert "Activation terrain est le canal qui pèse le moins" in answer
    assert "0 % du total" not in answer


def test_classement_mois():
    intent = build_intent(
        question="Quel est le mois où le CA est le plus faible ?",
        metric="ca_net",
        dimension="month",
        comparison="min",
    )
    result = pd.DataFrame({
        "month": pd.to_datetime(["2026-03-01", "2026-04-01"]),
        "ca_net": [20_000_000.0, 6_000_000.0],
    })

    answer = narrate(intent, result)

    assert answer.startswith(
        "Le mois le plus faible pour le chiffre d'affaires net est avril 2026"
    )


def test_comparaison_deux_produits_par_mois():
    intent = build_intent(
        question="Compare le bissap et le gingembre par mois",
        metric="mix_produit",
        dimensions=["product", "month"],
        product=["bissap", "gingembre"],
    )
    result = pd.DataFrame({
        "product": ["bissap", "gingembre", "bissap", "gingembre"],
        "month": pd.to_datetime(["2026-01-01", "2026-01-01", "2026-02-01", "2026-02-01"]),
        "mix_produit": [8_000_000.0, 2_000_000.0, 1_000_000.0, 3_000_000.0],
    })

    answer = narrate(intent, result)

    assert "le bissap devance le gingembre : **9.00 M FCFA** contre **5.00 M FCFA**" in answer
    assert "soit un écart de 4.00 M FCFA (1.8 fois plus)" in answer
    assert "Le bissap est devant 1 mois sur 2." in answer


def test_mix_produit_repartition():
    intent = build_intent(
        question="Quel est le mix produit ?",
        metric="mix_produit",
        dimension="product",
    )
    result = pd.DataFrame({
        "product": ["bissap", "bouye", "gingembre"],
        "mix_produit": [7_000_000.0, 1_000_000.0, 2_000_000.0],
    })

    answer = narrate(intent, result)

    assert "Répartition : Bissap 70 %, Gingembre 20 %, Bouye 10 %." in answer
    # La part du premier n'est pas répétée.
    assert "soit 70 % du total" not in answer


def test_evolution_du_mix_part_du_premier():
    intent = build_intent(
        question="Comment évolue le mix produit au fil des mois ?",
        metric="mix_produit",
        dimensions=["month", "product"],
    )
    result = pd.DataFrame({
        "month": pd.to_datetime(["2026-01-01", "2026-01-01", "2026-02-01", "2026-02-01"]),
        "product": ["bissap", "bouye", "bissap", "bouye"],
        "mix_produit": [6_000_000.0, 4_000_000.0, 8_000_000.0, 2_000_000.0],
    })

    answer = narrate(intent, result)

    assert "La part de Bissap monte de 60 % en janvier 2026 à 80 % en février 2026." in answer
