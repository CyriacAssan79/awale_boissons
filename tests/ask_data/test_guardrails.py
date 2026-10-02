from ai.ask_data.question_parser import parse_question


def test_roi_rejete():
    try:
        parse_question("Quel est notre ROI ?")
        assert False, "Le ROI aurait dû être rejeté."
    except ValueError as exc:
        assert "Métrique non supportée" in str(exc)


def test_causalite_rejetee():
    try:
        parse_question(
            "Quel canal a causé la hausse des ventes ?"
        )
        assert False, "La question causale aurait dû être rejetée."
    except ValueError as exc:
        assert "Analyse causale non supportée" in str(exc)


def test_prevision_rejetee():
    try:
        parse_question(
            "Quel sera le CA du mois prochain ?"
        )
        assert False, "La prévision aurait dû être rejetée."
    except ValueError as exc:
        assert "Prévision non supportée" in str(exc)


def test_dimension_incompatible_ca_net():
    try:
        parse_question(
            "Quel est le CA net par plateforme ?"
        )
        assert False, "La dimension plateforme aurait dû être rejetée."
    except ValueError as exc:
        assert "dimension 'platform'" in str(exc)


def test_dimension_incompatible_spend():
    try:
        parse_question(
            "Quel est le spend par produit ?"
        )
        assert False, "La dimension produit aurait dû être rejetée."
    except ValueError as exc:
        assert "dimension 'product'" in str(exc)


def test_question_sans_metrique():
    try:
        parse_question(
            "Montre-moi quelque chose d'intéressant."
        )
        assert False, "La question aurait dû être rejetée."
    except ValueError as exc:
        assert "hors périmètre" in str(exc)