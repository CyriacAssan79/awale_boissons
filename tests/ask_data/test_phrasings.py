"""Formulations libres : la même intention doit être reconnue quelle que soit la tournure."""

import pytest

from ai.ask_data.periods import extract_relative_months
from ai.ask_data.question_parser import normalize, parse_question


def test_normalize():
    assert normalize("Chiffre d’Affaire  de  Février") == "chiffre d'affaire de fevrier"


@pytest.mark.parametrize("question", [
    "Combien chaque produit rapporte mensuellement?",
    "Combien chaque produit rapporte chaque mois?",
    "Quel est le chiffre d'affaire de chaque produit par mois?",
    "Quel est le chiffre d’affaires de chaque produit par mois ?",
    "Quelles sont les ventes par produit et par mois ?",
])
def test_ca_par_produit_et_par_mois(question):
    intent = parse_question(question)

    # Le CA détaillé par produit est porté par mix_produit.
    assert intent.metric == "mix_produit"
    assert set(intent.dimensions) == {"month", "product"}


@pytest.mark.parametrize("question", [
    "Quel est le chiffre d'affaire de juin 2026 ?",
    "Quel est le Chiffre d’Affaires de Juin 2026 ?",
    "Combien avons-nous fait de revenus en juin 2026 ?",
    "Quelles sont les recettes de juin 2026 ?",
    "Combien rapportent les ventes en juin 2026 ?",
])
def test_ca_mois_precis(question):
    intent = parse_question(question)

    assert intent.metric == "ca_net"
    assert intent.filters == {"month": "2026-06"}


@pytest.mark.parametrize("question", [
    "Combien avons-nous investi sur Meta ?",
    "Quel budget pour Meta ?",
    "Dépenses Facebook ?",
])
def test_depenses_meta(question):
    intent = parse_question(question)

    assert intent.metric == "spend_marketing"
    assert intent.filters == {"channel": "Meta"}


def test_produit_qui_rapporte_le_plus():
    intent = parse_question("Quel produit rapporte le plus ?")

    assert intent.metric == "mix_produit"
    assert intent.dimensions == ["product"]
    assert intent.comparison == "max"


def test_selon_le_canal():
    intent = parse_question("Répartition des dépenses selon le canal")

    assert intent.metric == "spend_marketing"
    assert intent.dimensions == ["channel"]


def test_rapport_nom_commun_ignore():
    # « par rapport à » ne doit pas être lu comme « rapporte ».
    with pytest.raises(ValueError, match="hors périmètre"):
        parse_question("Fais-moi un rapport")


@pytest.mark.parametrize("text, expected", [
    ("ces trois derniers mois", 3),
    ("les deux derniers mois", 2),
    ("le dernier trimestre", 3),
    ("les deux derniers trimestres", 6),
    ("le dernier semestre", 6),
    ("le mois dernier", None),
])
def test_periodes_relatives_en_lettres(text, expected):
    assert extract_relative_months(text) == expected


def test_produit_et_mois_sans_annee():
    intent = parse_question("Le bissap a rapporté combien en mai ?")

    assert intent.metric == "mix_produit"
    assert intent.filters == {"product": "bissap", "month_of_year": "05"}


def test_produit_sans_metrique():
    intent = parse_question("Combien de gingembre en juin 2026 ?")

    assert intent.metric == "mix_produit"
    assert intent.filters == {"month": "2026-06", "product": "gingembre"}


def test_produit_incompatible_avec_les_depenses():
    with pytest.raises(ValueError, match="dimension 'product'"):
        parse_question("Dépenses marketing du bissap ?")


def test_mois_avec_annee_prioritaire():
    intent = parse_question("Quel est le CA en mai 2026 ?")

    assert intent.filters == {"month": "2026-05"}


@pytest.mark.parametrize("question", [
    "Combien avons-nous vendu en juin 2026 ?",
    "Qu'avons-nous vendu en juin 2026 ?",
])
def test_vendu(question):
    intent = parse_question(question)

    assert intent.metric == "ca_net"
    assert intent.filters == {"month": "2026-06"}


@pytest.mark.parametrize("question", [
    "Quel est le chiffre d'affaires du mois dernier ?",
    "Quel est le CA du dernier mois ?",
    "Le CA du mois le plus récent ?",
])
def test_mois_dernier(question):
    from ai.ask_data.periods import LATEST_MONTH

    intent = parse_question(question)

    assert intent.metric == "ca_net"
    assert intent.filters == {"month_of_year": LATEST_MONTH}
    assert intent.relative_months is None


def test_derniers_mois_reste_une_periode_relative():
    intent = parse_question("Le CA des 3 derniers mois ?")

    assert intent.relative_months == 3
    assert "month_of_year" not in intent.filters


def test_comparer_deux_produits():
    intent = parse_question("Compare le chiffre d'affaires du bissap et du gingembre.")

    assert intent.metric == "mix_produit"
    assert intent.dimensions == ["product"]
    assert intent.filters == {"product": ["bissap", "gingembre"]}


def test_comparer_deux_canaux_sans_metrique():
    intent = parse_question("Compare Meta et TikTok en juin 2026")

    assert intent.metric == "spend_marketing"
    assert intent.dimensions == ["channel"]
    assert intent.filters == {"month": "2026-06", "channel": ["Meta", "TikTok"]}


def test_alias_du_meme_canal_non_compares():
    # Facebook et Instagram désignent tous deux Meta : pas de comparaison.
    intent = parse_question("Dépenses Facebook et Instagram ?")

    assert intent.filters == {"channel": "Meta"}
    assert intent.dimensions == []


def test_mix_produit_seul_decoupe_par_produit():
    intent = parse_question("Quel est le mix produit ?")

    assert intent.metric == "mix_produit"
    assert intent.dimensions == ["product"]


def test_repartition_entre_les_produits():
    intent = parse_question(
        "Comment se répartit le chiffre d'affaires entre les produits ?"
    )

    assert intent.metric == "mix_produit"
    assert intent.dimensions == ["product"]


def test_produit_le_plus_vendu():
    intent = parse_question("Quel est le produit le plus vendu en juin ?")

    assert intent.metric == "mix_produit"
    assert intent.dimensions == ["product"]
    assert intent.comparison == "max"
    assert intent.filters == {"month_of_year": "06"}


@pytest.mark.parametrize("question", [
    "Comment évolue le mix produit au fil des mois ?",
    "Évolution du mix produit",
    "Le mix produit mois après mois",
])
def test_evolution_du_mix(question):
    intent = parse_question(question)

    assert intent.metric == "mix_produit"
    assert intent.dimensions == ["month", "product"]


def test_evolution_des_depenses():
    intent = parse_question("Comment évoluent les dépenses Meta ?")

    assert intent.metric == "spend_marketing"
    assert intent.dimensions == ["month"]
    assert intent.filters == {"channel": "Meta"}


def test_mix_d_un_seul_produit_non_decoupe():
    intent = parse_question("Le mix produit du bissap en juin 2026")

    assert intent.dimensions == []
    assert intent.filters == {"month": "2026-06", "product": "bissap"}


def test_on_a_fait_combien():
    intent = parse_question("On a fait combien en juin ?")

    assert intent.metric == "ca_net"
    assert intent.filters == {"month_of_year": "06"}


def test_sur_quoi_avons_nous_le_plus_depense():
    intent = parse_question("Sur quoi avons-nous le plus dépensé ?")

    assert intent.metric == "spend_marketing"
    assert intent.dimensions == ["channel"]
    assert intent.comparison == "max"


@pytest.mark.parametrize("question", [
    "Comment se porte le chiffre d'affaires ces derniers mois ?",
    "Est-ce que le CA augmente ou diminue ?",
    "Le CA est-il en hausse ?",
    "Quelle est la tendance du chiffre d'affaires ?",
])
def test_tendance_decoupe_par_mois(question):
    intent = parse_question(question)

    assert intent.metric == "ca_net"
    assert intent.dimensions == ["month"]


def test_ces_derniers_mois_sans_nombre():
    intent = parse_question("Comment se porte le chiffre d'affaires ces derniers mois ?")

    assert intent.relative_months == 3


def test_produit_qui_marche_le_mieux():
    intent = parse_question("Quel est le produit qui marche le mieux ?")

    assert intent.metric == "mix_produit"
    assert intent.dimensions == ["product"]
    assert intent.comparison == "max"


@pytest.mark.parametrize("question, filters", [
    ("Fais-moi un résumé du chiffre d'affaires depuis janvier.", {"since_month_of_year": "01"}),
    ("Le CA depuis mars 2026", {"since": "2026-03"}),
    ("Le CA depuis le début de l'année", {"since_month_of_year": "01"}),
    ("Les dépenses à partir de février", {"since_month_of_year": "02"}),
])
def test_depuis(question, filters):
    intent = parse_question(question)

    assert intent.filters == filters


def test_deux_metriques():
    intent = parse_question(
        "Résume-moi les ventes et les dépenses marketing des derniers mois."
    )

    assert intent.metric == "ca_net"
    assert intent.other_metrics == ["spend_marketing"]
    assert intent.dimensions == ["month"]
    assert intent.relative_months == 3


def test_mix_et_chiffre_d_affaires_ne_font_qu_une_metrique():
    intent = parse_question("Le chiffre d'affaires du mix produit")

    assert intent.metric == "mix_produit"
    assert intent.other_metrics == []


def test_ca_pronom_n_est_pas_le_chiffre_d_affaires():
    intent = parse_question("Ça coûte combien la pub sur TikTok ?")

    assert intent.metric == "spend_marketing"
    assert intent.other_metrics == []


@pytest.mark.parametrize("question", [
    "Ça va les affaires en ce moment ?",
    "Comment va l'activité récemment ?",
    "Comment se porte le business ces derniers temps ?",
])
def test_activite_recente(question):
    intent = parse_question(question)

    assert intent.metric == "ca_net"
    assert intent.dimensions == ["month"]
    assert intent.relative_months == 3
