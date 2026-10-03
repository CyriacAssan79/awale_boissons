"""Voix du client : sentiment, spam, volume, plateformes et thèmes des commentaires."""

from pathlib import Path

import pandas as pd
import pytest

from ai.ask_data.intent import build_intent
from ai.ask_data.narrative import narrate
from ai.ask_data.question_parser import parse_question
from ai.ask_data.sql_builder import build_sql


# ---------------------------------------------------------------------
# Compréhension des questions
# ---------------------------------------------------------------------

# question → (métrique, autres métriques, découpages, filtres, classement)
QUESTIONS = {
    "Quel est le sentiment des clients ?":
        ("repartition_sentiment", [], [], {}, None),
    "Quelle est la répartition des sentiments ?":
        ("repartition_sentiment", [], [], {}, None),
    "Combien avons-nous de commentaires positifs ?":
        ("commentaires_positifs", [], [], {}, None),
    "Combien avons-nous de commentaires négatifs ?":
        ("commentaires_negatifs", [], [], {}, None),
    "Combien avons-nous de commentaires neutres ?":
        ("commentaires_neutres", [], [], {}, None),
    "Quel est le taux de commentaires négatifs ?":
        ("sentiment_client", [], [], {}, None),
    "Quel est le taux de commentaires positifs ?":
        ("taux_positifs", [], [], {}, None),
    "Comment évolue le sentiment des clients par mois ?":
        ("repartition_sentiment", [], ["month"], {}, None),
    "Quel mois a enregistré le plus de commentaires négatifs ?":
        ("commentaires_negatifs", [], ["month"], {}, "max"),
    "Quel mois a enregistré le plus de commentaires positifs ?":
        ("commentaires_positifs", [], ["month"], {}, "max"),
    "Donne-moi le sentiment des clients par mois.":
        ("repartition_sentiment", [], ["month"], {}, None),
    "Donne-moi le sentiment par plateforme.":
        ("repartition_sentiment", [], ["platform"], {}, None),
    "Quelle plateforme contient le plus de commentaires négatifs ?":
        ("commentaires_negatifs", [], ["platform"], {}, "max"),
    "Quelle plateforme contient le plus de commentaires positifs ?":
        ("commentaires_positifs", [], ["platform"], {}, "max"),
    "Comment évolue le sentiment sur Facebook ?":
        ("repartition_sentiment", [], ["month"], {"platform": "Facebook"}, None),
    "Quel est le sentiment des clients sur TikTok ?":
        ("repartition_sentiment", [], [], {"platform": "TikTok"}, None),
    "Combien avons-nous de commentaires exploitables ?":
        ("commentaires_exploitables", [], [], {}, None),
    "Combien de commentaires sont considérés comme du spam ?":
        ("commentaires_spam", [], [], {}, None),
    "Quel est le taux de spam ?":
        ("taux_spam", [], [], {}, None),
    "Résume-moi ce que disent les clients sur les derniers mois.":
        ("repartition_sentiment", ["themes_commentaires"], ["month"], {}, None),
    "Que pensent les clients de nos produits ?":
        ("repartition_sentiment", ["themes_commentaires"], [], {}, None),
    "Les clients sont-ils plutôt satisfaits ou mécontents ?":
        ("repartition_sentiment", [], [], {}, None),
    "Est-ce que les retours clients s'améliorent ?":
        ("repartition_sentiment", [], ["month"], {}, None),
    "Qu'est-ce qui ressort des commentaires ?":
        ("repartition_sentiment", ["themes_commentaires"], [], {}, None),
    "Les clients parlent-ils davantage positivement ou négativement de la marque ?":
        ("repartition_sentiment", [], [], {}, None),
    "Comment les clients réagissent-ils à nos produits ?":
        ("repartition_sentiment", ["themes_commentaires"], [], {}, None),
    "Quel est le ressenti des clients ce mois-ci ?":
        ("repartition_sentiment", [], [], {"month_of_year": "dernier"}, None),
    "Est-ce que les avis négatifs augmentent ?":
        ("commentaires_negatifs", ["sentiment_client"], ["month"], {}, None),
    "Quelle plateforme génère le plus de retours négatifs ?":
        ("commentaires_negatifs", [], ["platform"], {}, "max"),
    "Fais-moi un résumé des retours clients depuis janvier.":
        ("repartition_sentiment", ["themes_commentaires"], ["month"],
         {"since_month_of_year": "01"}, None),
    "Combien de commentaires avons-nous reçus par mois ?":
        ("commentaires_total", [], ["month"], {}, None),
    "Quels sont les thèmes les plus abordés ?":
        ("themes_commentaires", [], [], {}, None),
}


@pytest.mark.parametrize("question", QUESTIONS)
def test_questions_sur_les_commentaires(question):
    metric, others, dimensions, filters, comparison = QUESTIONS[question]

    intent = parse_question(question)

    assert intent.metric == metric
    assert intent.other_metrics == others
    assert intent.dimensions == dimensions
    assert intent.filters == filters
    assert intent.comparison == comparison


def test_derniers_mois_relatifs():
    intent = parse_question("Résume-moi ce que disent les clients sur les derniers mois.")

    assert intent.relative_months == 3


def test_comparaison_de_plateformes():
    intent = parse_question("Compare le sentiment sur Facebook et TikTok")

    assert intent.metric == "repartition_sentiment"
    assert intent.dimensions == ["platform"]
    assert intent.filters == {"platform": ["Facebook", "TikTok"]}


def test_meta_vaut_facebook_et_instagram_pour_les_commentaires():
    intent = parse_question("Quel est le sentiment des clients sur Meta ?")

    assert intent.filters == {"platform": ["Facebook", "Instagram"]}
    assert intent.dimensions == ["platform"]


def test_canal_sans_commentaires_refuse():
    with pytest.raises(ValueError, match="Plateforme inconnue"):
        parse_question("Quel est le sentiment sur Google ?")


def test_meta_reste_un_canal_pour_les_depenses():
    intent = parse_question("Combien avons-nous dépensé sur Facebook ?")

    assert intent.metric == "spend_marketing"
    assert intent.filters == {"channel": "Meta"}


def test_sentiment_par_produit_indisponible():
    with pytest.raises(ValueError, match="dimension 'product'"):
        parse_question("Quel est le sentiment sur le bissap ?")


def test_influenceurs_nest_pas_une_question_causale():
    # « influence » ne doit pas être trouvé dans « influenceurs ».
    intent = parse_question("Combien avons-nous dépensé sur les influenceurs ?")

    assert intent.metric == "spend_marketing"
    assert intent.filters == {"channel": "Influenceurs"}


@pytest.mark.parametrize("question", [
    "Pourquoi les avis négatifs augmentent-ils ?",
    "Est-ce que la promo a influencé le sentiment ?",
    "Quel canal a causé la hausse des commentaires positifs ?",
])
def test_questions_causales_sur_les_commentaires_refusees(question):
    with pytest.raises(ValueError, match="Analyse causale"):
        parse_question(question)


# ---------------------------------------------------------------------
# SQL
# ---------------------------------------------------------------------

def test_sql_repartition_contient_les_composantes():
    sql = build_sql(build_intent(question="", metric="repartition_sentiment", dimension="platform"))

    assert "SUM(positive_comments_count) AS positifs" in sql
    assert "SUM(neutral_comments_count) AS neutres" in sql
    assert "SUM(negative_comments_count) AS negatifs" in sql
    assert "FROM mart_social_monthly" in sql


def test_sql_filtre_plateformes():
    sql = build_sql(
        build_intent(question="", metric="commentaires_spam", platform=["facebook", "TikTok"])
    )

    assert "platform IN ('Facebook', 'TikTok')" in sql


def test_sql_injection_plateforme_refusee():
    with pytest.raises(ValueError, match="Plateforme inconnue"):
        build_sql(
            build_intent(question="", metric="taux_spam", platform="x' OR 1=1 --")
        )


def test_sql_plateforme_refusee_pour_le_ca():
    with pytest.raises(ValueError, match="dimension 'platform'"):
        build_sql(build_intent(question="", metric="ca_net", platform="Facebook"))


# ---------------------------------------------------------------------
# Rédaction
# ---------------------------------------------------------------------

SENTIMENT = pd.DataFrame({
    "month": pd.to_datetime(["2026-01-01", "2026-01-01", "2026-02-01", "2026-02-01"]),
    "platform": ["Facebook", "TikTok", "Facebook", "TikTok"],
    "repartition_sentiment": [100, 100, 100, 100],
    "positifs": [50, 40, 60, 40],
    "neutres": [20, 20, 20, 20],
    "negatifs": [30, 40, 20, 40],
})


def test_redaction_sentiment_global():
    intent = build_intent(question="", metric="repartition_sentiment")
    totals = SENTIMENT.drop(columns=["month", "platform"]).sum().to_frame().T

    text = narrate(intent, totals)

    assert "**400 commentaires exploitables**" in text
    assert "**48 % positifs** (190)" in text
    assert "32 % négatifs (130)" in text
    assert "20 % neutres (80)" in text
    assert "Les avis positifs l'emportent" in text
    assert "tendance" in text


def test_redaction_sentiment_par_mois_et_plateforme():
    intent = build_intent(
        question="", metric="repartition_sentiment", dimensions=["month", "platform"]
    )

    text = narrate(intent, SENTIMENT)

    assert "progresse de 45 % en janvier 2026 à 50 % en février 2026" in text
    assert "Facebook a la part de positifs la plus élevée (55 %)" in text
    assert "La part de négatifs est la plus forte sur TikTok (40 %)" in text
    assert "graphique" in text


def test_redaction_sentiment_compare_au_mois_precedent():
    intent = build_intent(question="", metric="repartition_sentiment", month="2026-02")
    current = pd.DataFrame(
        {"repartition_sentiment": [200], "positifs": [100], "neutres": [40], "negatifs": [60]}
    )
    previous = {"repartition_sentiment": 200.0, "positifs": 90.0, "neutres": 40.0, "negatifs": 70.0}

    text = narrate(intent, current, previous)

    assert "En février 2026" in text
    assert "en hausse de 5.0 points par rapport à janvier 2026 (45 %)" in text


def test_redaction_classement_des_mois():
    intent = build_intent(
        question="", metric="commentaires_negatifs", dimension="month", comparison="max"
    )
    data = pd.DataFrame({
        "month": pd.to_datetime(["2026-03-01", "2026-04-01"]),
        "commentaires_negatifs": [120, 166],
    })

    text = narrate(intent, data)

    assert text.startswith(
        "Le mois qui compte le plus de commentaires négatifs est avril 2026, avec **166**"
    )


def test_redaction_part_par_plateforme():
    intent = build_intent(question="", metric="sentiment_client", dimension="platform")
    data = pd.DataFrame({
        "platform": ["Facebook", "Instagram", "TikTok"],
        "sentiment_client": [0.289, 0.296, 0.33],
    })

    text = narrate(intent, data)

    assert "la plus élevée sur TikTok (**33.0 %**)" in text
    assert "la plus faible sur Facebook (**28.9 %**)" in text


def test_redaction_nombre_unique():
    intent = build_intent(question="", metric="commentaires_spam", platform="TikTok")

    text = narrate(intent, pd.DataFrame({"commentaires_spam": [64]}))

    assert text == "Sur l'ensemble de la période sur TikTok, on compte **64 commentaires indésirables (spam)**."


def test_redaction_themes():
    intent = build_intent(question="", metric="themes_commentaires")
    data = pd.DataFrame([{
        "themes_commentaires": 100, "gout": 40, "prix": 25, "promotion": 5,
        "disponibilite": 10, "emballage": 0, "sante": 0, "livraison": 0,
        "service": 0, "question_produit": 0, "autre": 20,
    }])

    text = narrate(intent, data)

    # « Autre » n'est pas un sujet : il est ignoré dans le classement.
    assert "le goût (40, 40 %), le prix (25, 25 %) et la disponibilité (10, 10 %)" in text


# ---------------------------------------------------------------------
# De bout en bout, sur la base
# ---------------------------------------------------------------------

DB_PATH = Path("data/awale.duckdb")


@pytest.mark.skipif(not DB_PATH.exists(), reason="base data/awale.duckdb absente")
@pytest.mark.parametrize("question", QUESTIONS)
def test_chaque_question_obtient_une_reponse(question):
    from ai.ask_data.service import run_ask_data

    response = run_ask_data(question)

    assert response.error is None, response.error
    assert response.narrative
    assert "Aucune donnée" not in response.narrative
