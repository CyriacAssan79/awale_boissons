"""Interprétation par le modèle : intention du modèle, faits extraits de la question.

Le modèle est remplacé par une réponse fixe : ces tests ne chargent pas Qwen.
"""

import json

import pytest

from ai.ask_data.llm_parser import build_messages, intent_from_llm_output, llm_parse
from ai.ask_data.service import parse_with_fallback


def fiche(**fields) -> str:
    base = {
        "metric": "ca_net", "other_metrics": [], "dimensions": [],
        "ranking": None, "recent": False, "out_of_scope": False,
    }
    base.update(fields)
    return json.dumps(base)


def test_question_ajoutee_en_dernier_message():
    messages = build_messages("Ma question ?")

    assert messages[0]["role"] == "system"
    assert messages[-1] == {"role": "user", "content": "Ma question ?"}


def test_fiche_simple():
    intent = intent_from_llm_output(
        fiche(metric="spend_marketing"),
        "Combien nous ont coûté nos pubs ?",
    )

    assert intent.metric == "spend_marketing"
    assert intent.filters == {}


def test_texte_autour_du_json_ignore():
    raw = "Voici la fiche :\n" + fiche(dimensions=["month"]) + "\nBonne journée"

    intent = intent_from_llm_output(raw, "q")

    assert intent.dimensions == ["month"]


# ---------------------------------------------------------------------
# Les faits viennent de la question, jamais du modèle
# ---------------------------------------------------------------------

def test_canal_absent_de_la_question_jamais_ajoute():
    # Erreur observée avec Qwen : « Meta » ajouté alors que la question
    # n'en parle pas. Les canaux de la fiche ne sont plus lus du tout.
    raw = fiche(metric="spend_marketing", channels=["Meta"], period_month="04",
                period_year="2026", period_type="month")

    intent = intent_from_llm_output(raw, "Combien nous a coûté la pub au printemps ?")

    assert intent.filters == {}


def test_depuis_lu_dans_la_question():
    # Erreur observée avec Qwen : « depuis mars » compris comme « en mars ».
    intent = intent_from_llm_output(
        fiche(dimensions=["month"]),
        "Donne-moi un point sur l'activité depuis mars",
    )

    assert intent.filters == {"since_month_of_year": "03"}


def test_canal_et_mois_cites_repris_de_la_question():
    intent = intent_from_llm_output(
        fiche(metric="spend_marketing"),
        "Combien nous a coûté la pub Facebook en mars 2026 ?",
    )

    assert intent.filters == {"month": "2026-03", "channel": "Meta"}


def test_recent_sans_date():
    intent = intent_from_llm_output(
        fiche(dimensions=["month"], recent=True),
        "Le business tourne bien en ce moment ?",
    )

    assert intent.relative_months == 3


def test_recent_ignore_si_la_question_donne_une_date():
    intent = intent_from_llm_output(
        fiche(recent=True),
        "Le business a bien tourné en mai 2026 ?",
    )

    assert intent.relative_months is None
    assert intent.filters == {"month": "2026-05"}


def test_ca_par_produit_devient_mix_et_classement():
    intent = intent_from_llm_output(
        fiche(dimensions=["product"], ranking="max"),
        "Qu'est-ce qui se vend le mieux ?",
    )

    assert intent.metric == "mix_produit"
    assert intent.dimensions == ["product"]
    assert intent.comparison == "max"


def test_produits_cites_compares():
    intent = intent_from_llm_output(fiche(), "Bissap ou gingembre, lequel cartonne ?")

    assert intent.metric == "mix_produit"
    assert intent.dimensions == ["product"]
    assert intent.filters == {"product": ["bissap", "gingembre"]}


@pytest.mark.parametrize("fields", [
    {"out_of_scope": True},
    {"metric": "roi"},                       # métrique hors liste
    {"metric": None},
    {"dimensions": ["commune"]},             # découpage hors liste
    {"other_metrics": ["marge"]},
    {"ranking": "moyenne"},
])
def test_fiche_invalide_refusee(fields):
    with pytest.raises(ValueError, match="hors périmètre"):
        intent_from_llm_output(fiche(**fields), "q")


def test_decoupage_indisponible_refuse():
    with pytest.raises(ValueError, match="dimension 'channel'"):
        intent_from_llm_output(fiche(dimensions=["channel"]), "q")


def test_sortie_non_json_refusee():
    with pytest.raises(ValueError, match="hors périmètre"):
        intent_from_llm_output("Je ne sais pas.", "q")


def test_llm_parse_avec_generateur_injecte():
    intent = llm_parse("q", generate=lambda messages: fiche(metric="spend_marketing"))

    assert intent.metric == "spend_marketing"


# ---------------------------------------------------------------------
# Repli : règles d'abord, modèle seulement si aucune métrique reconnue
# ---------------------------------------------------------------------

class FakeLoader:
    """Charge un « modèle » qui renvoie toujours la même fiche."""

    def __init__(self, raw: str):
        self.raw = raw
        self.calls = 0

    def __call__(self):
        self.calls += 1
        return self


@pytest.fixture
def fake_model(monkeypatch):
    def install(raw: str) -> FakeLoader:
        loader = FakeLoader(raw)
        monkeypatch.setattr(
            "ai.ask_data.llm_parser.generate_with_model",
            lambda bundle, messages: bundle.raw,
        )
        return loader

    return install


def test_regles_suffisantes_modele_non_charge(fake_model):
    loader = fake_model(fiche(metric="spend_marketing"))

    intent, used_llm = parse_with_fallback("Quel est le CA net en juin 2026 ?", loader)

    assert intent.metric == "ca_net"
    assert used_llm is False
    assert loader.calls == 0


def test_question_libre_confiee_au_modele(fake_model):
    loader = fake_model(fiche(dimensions=["product"], ranking="max"))

    intent, used_llm = parse_with_fallback("Qu'est-ce qui cartonne chez nous ?", loader)

    assert used_llm is True
    assert intent.metric == "mix_produit"
    assert loader.calls == 1


@pytest.mark.parametrize("question, message", [
    ("Quel canal a causé la hausse des ventes ?", "Analyse causale"),
    ("Quel sera le CA du mois prochain ?", "Prévision"),
    ("Quel est notre ROI ?", "Métrique non supportée"),
])
def test_refus_volontaires_jamais_confies_au_modele(fake_model, question, message):
    loader = fake_model(fiche())

    with pytest.raises(ValueError, match=message):
        parse_with_fallback(question, loader)

    assert loader.calls == 0


def test_modele_hors_perimetre_garde_le_refus_d_origine(fake_model):
    loader = fake_model(fiche(out_of_scope=True, metric=None))

    with pytest.raises(ValueError, match="hors périmètre"):
        parse_with_fallback("Quelle est la capitale du Sénégal ?", loader)


def test_sans_modele_comportement_inchange():
    with pytest.raises(ValueError, match="hors périmètre"):
        parse_with_fallback("Qu'est-ce qui cartonne chez nous ?", None)


def test_classement_ignore_sans_mot_de_comparaison():
    # Erreur observée avec Qwen : « le plus élevé » ajouté à « On s'en sort comment ? ».
    intent = intent_from_llm_output(
        fiche(dimensions=["month"], ranking="max"),
        "On s'en sort comment niveau chiffres ?",
    )

    assert intent.comparison is None


def test_classement_garde_avec_mot_de_comparaison():
    intent = intent_from_llm_output(
        fiche(dimensions=["product"], ranking="max"),
        "Quelle boisson les clients préfèrent-ils ?",
    )

    assert intent.comparison == "max"
