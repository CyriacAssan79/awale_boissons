from ai.ask_data.question_parser import parse_question


def test_ca_net_en_juin():
    intent = parse_question("Quel est le CA net en juin 2026 ?")

    assert intent.metric == "ca_net"
    assert intent.dimensions == []
    assert intent.filters == {"month": "2026-06"}


def test_ca_net_par_mois():
    intent = parse_question("Quel est le CA net par mois ?")

    assert intent.metric == "ca_net"
    assert intent.dimensions == ["month"]
    assert intent.filters == {}


def test_depense_meta():
    intent = parse_question("Combien avons-nous dépensé sur Meta ?")

    assert intent.metric == "spend_marketing"
    assert intent.dimensions == []
    assert intent.filters == {"channel": "Meta"}


def test_depense_par_canal():
    intent = parse_question("Quel est le montant dépensé par canal ?")

    assert intent.metric == "spend_marketing"
    assert intent.dimensions == ["channel"]
    assert intent.filters == {}


def test_depense_google_juin():
    intent = parse_question(
        "Combien avons-nous dépensé sur Google en juin 2026 ?"
    )

    assert intent.metric == "spend_marketing"
    assert intent.dimensions == []
    assert intent.filters == {
        "month": "2026-06",
        "channel": "Google",
    }


def test_roi_non_supporte():
    try:
        parse_question("Quel est notre ROI ?")
        assert False, "La question ROI aurait dû être rejetée."
    except ValueError as exc:
        assert "Métrique non supportée" in str(exc)


def test_question_causale_rejetee():
    try:
        parse_question("Quel canal a causé la hausse des ventes ?")
        assert False, "La question causale aurait dû être rejetée."
    except ValueError as exc:
        assert "Analyse causale non supportée" in str(exc)


def test_prevision_rejetee():
    try:
        parse_question("Quel sera le CA du mois prochain ?")
        assert False, "La prévision aurait dû être rejetée."
    except ValueError as exc:
        assert "Prévision non supportée" in str(exc)

def test_dimension_incompatible_ca_net():
    try:
        parse_question("Quel est le CA net par plateforme ?")
        assert False, "La dimension plateforme aurait dû être rejetée."
    except ValueError as exc:
        assert "dimension 'platform'" in str(exc)


def test_dimension_incompatible_spend():
    try:
        parse_question("Quel est le spend par produit ?")
        assert False, "La dimension produit aurait dû être rejetée."
    except ValueError as exc:
        assert "dimension 'product'" in str(exc)

def test_parse_question_periode_relative_non_supportee():
    question = "Donne moi les dépenses publicitaires par canal ces 3 derniers mois"

    intent = parse_question(question)

    assert intent.metric == "spend_marketing"
    assert intent.dimensions == ["channel"]
    assert intent.filters == {}