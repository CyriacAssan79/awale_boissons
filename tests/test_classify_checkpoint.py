"""Tests de ai/classify_comments_hybrid.py : sauvegarde intermédiaire, reprise,
repli par commentaire et prompt versionné.

Le modèle est simulé (aucun téléchargement, aucun torch requis) : ces tests
vérifient la logique du script, pas la qualité du classifieur.
"""

from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "ai" / "classify_comments_hybrid.py"

N_COMMENTS = 23  # 6 batches de 4 (le dernier de 3)


def fake_prediction(text: str) -> dict:
    sentiments = ["positive", "negative", "neutral"]
    return {
        "language": "fr",
        "sentiment": sentiments[len(text) % 3],
        "theme": "other",
        "product": "unknown",
        "is_spam": False,
    }


@pytest.fixture()
def hybrid(monkeypatch, tmp_path):
    """Charge le script avec torch/transformers factices et des chemins temporaires."""
    for name in ("torch", "transformers"):
        monkeypatch.setitem(sys.modules, name, types.ModuleType(name))
    sys.modules["transformers"].AutoModelForCausalLM = object
    sys.modules["transformers"].AutoTokenizer = object

    spec = importlib.util.spec_from_file_location("hybrid_under_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    module.INPUT_FILE = tmp_path / "comments.csv"
    module.OUTPUT_FILE = tmp_path / "predictions.csv"
    module.CHECKPOINT_EVERY_BATCHES = 2
    monkeypatch.setattr(module, "load_model", lambda: (None, None))

    pd.DataFrame(
        {
            "comment_id": [f"C{i:04d}" for i in range(N_COMMENTS)],
            "comment_text": [f"avis client numero {i}" for i in range(N_COMMENTS)],
        }
    ).to_csv(module.INPUT_FILE, index=False)

    return module


def install_model(module, monkeypatch, calls, crash_on_call=None, bad_text=None):
    """Remplace l'inférence par une fonction qui enregistre ses appels."""

    def fake_batch(texts, tokenizer, model):
        calls.append(list(texts))

        if crash_on_call is not None and len(calls) == crash_on_call:
            raise RuntimeError("plantage simulé au milieu du run")

        if bad_text is not None and any(bad_text in t for t in texts):
            raise ValueError("JSON introuvable")

        return [fake_prediction(t) for t in texts]

    monkeypatch.setattr(module, "model_classification_batch", fake_batch)


def read_output(module) -> pd.DataFrame:
    return pd.read_csv(module.OUTPUT_FILE)


# ---------------------------------------------------------------------------
# Prompt versionné
# ---------------------------------------------------------------------------

def test_prompt_is_a_versioned_file_and_is_what_the_script_uses(hybrid):
    prompt_file = hybrid.PROMPT_FILE

    assert prompt_file.parent == ROOT / "ai" / "prompts"
    assert prompt_file.exists()
    assert hybrid.PROMPT_TEXT == prompt_file.read_text(encoding="utf-8")
    assert hybrid.SYSTEM_PROMPT in hybrid.PROMPT_TEXT
    assert "JSON" in hybrid.SYSTEM_PROMPT
    assert hybrid.PROMPT_VERSION == "comment_classifier_v4_hybrid"
    assert hybrid.PROMPT_VERSION in hybrid.CLASSIFIER_VERSION


def test_few_shot_examples_are_valid_and_never_taken_from_the_benchmark(hybrid):
    """Un exemple copié du benchmark humain gonflerait artificiellement le score."""
    examples = hybrid.FEW_SHOT_EXAMPLES
    assert len(examples) >= 8

    for text, answer in examples:
        checked = hybrid.validate_model_prediction(hybrid.extract_json(answer))
        assert checked["coerced"] == [], text

    benchmark = pd.read_csv(ROOT / "ai" / "evaluation" / "labeled_sample.csv")
    benchmark_texts = set(benchmark["comment_text"].map(hybrid.normalize_text))

    for text, _ in examples:
        assert hybrid.normalize_text(text) not in benchmark_texts, text


# ---------------------------------------------------------------------------
# Sauvegarde intermédiaire et reprise
# ---------------------------------------------------------------------------

def test_progress_is_saved_during_the_run_not_only_at_the_end(hybrid, monkeypatch):
    """À l'appel n° 4 (batch 4), le checkpoint du batch 2 doit déjà être sur disque."""
    seen = {}
    calls = []

    def fake_batch(texts, tokenizer, model):
        calls.append(list(texts))
        if len(calls) == 4:
            seen["rows_on_disk"] = (
                len(pd.read_csv(hybrid.OUTPUT_FILE)) if hybrid.OUTPUT_FILE.exists() else 0
            )
        return [fake_prediction(t) for t in texts]

    monkeypatch.setattr(hybrid, "model_classification_batch", fake_batch)

    hybrid.main()

    assert seen["rows_on_disk"] == 8  # batches 1 et 2 sauvegardés avant le batch 4


def test_crash_keeps_finished_work_and_rerun_resumes_only_what_is_missing(hybrid, monkeypatch):
    calls = []
    install_model(hybrid, monkeypatch, calls, crash_on_call=5)

    with pytest.raises(RuntimeError, match="plantage simulé"):
        hybrid.main()

    saved = read_output(hybrid)
    assert len(saved) == 16  # batches 1 à 4 conservés, batch 5 (plantage) perdu
    assert not hybrid.OUTPUT_FILE.with_suffix(".csv.tmp").exists()

    # Relance : seuls les 7 commentaires manquants sont classés.
    resumed_calls = []
    install_model(hybrid, monkeypatch, resumed_calls)
    hybrid.main()

    classified_again = [t for batch in resumed_calls for t in batch]
    assert len(classified_again) == N_COMMENTS - 16

    resumed = read_output(hybrid)
    assert len(resumed) == N_COMMENTS
    assert resumed["comment_id"].is_unique

    # Le résultat final est identique à celui d'un run sans interruption.
    clean_out = hybrid.OUTPUT_FILE.with_name("clean.csv")
    hybrid.OUTPUT_FILE.unlink()
    hybrid.OUTPUT_FILE = clean_out
    install_model(hybrid, monkeypatch, [])
    hybrid.main()

    pd.testing.assert_frame_equal(resumed, pd.read_csv(clean_out))


def test_second_run_with_nothing_new_does_not_call_the_model(hybrid, monkeypatch):
    install_model(hybrid, monkeypatch, [])
    hybrid.main()

    calls = []
    install_model(hybrid, monkeypatch, calls)
    hybrid.main()

    assert calls == []
    assert len(read_output(hybrid)) == N_COMMENTS


def test_no_temporary_file_is_left_behind(hybrid, monkeypatch):
    install_model(hybrid, monkeypatch, [])
    hybrid.main()

    leftovers = [p.name for p in hybrid.OUTPUT_FILE.parent.iterdir() if p.suffix == ".tmp"]
    assert leftovers == []


# ---------------------------------------------------------------------------
# Sortie illisible du modèle
# ---------------------------------------------------------------------------

def test_one_unreadable_output_is_retried_alone_reported_and_not_saved(hybrid, monkeypatch):
    calls = []
    install_model(hybrid, monkeypatch, calls, bad_text="numero 9")

    with pytest.raises(SystemExit) as exit_info:
        hybrid.main()

    assert exit_info.value.code == 1

    saved = read_output(hybrid)
    assert len(saved) == N_COMMENTS - 1          # tout le reste est enregistré
    assert "C0009" not in set(saved["comment_id"])  # rien n'est deviné pour le fautif

    # Le lot fautif a été retenté commentaire par commentaire.
    assert any(len(batch) == 1 and "numero 9" in batch[0] for batch in calls)


def test_the_failed_comment_is_retried_at_the_next_run(hybrid, monkeypatch):
    install_model(hybrid, monkeypatch, [], bad_text="numero 9")
    with pytest.raises(SystemExit):
        hybrid.main()

    calls = []
    install_model(hybrid, monkeypatch, calls)  # le modèle "répond" maintenant
    hybrid.main()

    assert [t for batch in calls for t in batch] == ["avis client numero 9"]
    assert len(read_output(hybrid)) == N_COMMENTS


# ---------------------------------------------------------------------------
# Garde-fou : vocabulaire fermé, remplacements jamais silencieux
# ---------------------------------------------------------------------------

# Le produit n'est jamais demandé au modèle (il est déduit par les règles).
VALID = {
    "language": "fr",
    "sentiment": "positive",
    "theme": "taste",
    "is_spam": False,
}


def test_valid_answer_is_kept_as_is(hybrid):
    checked = hybrid.validate_model_prediction(VALID)

    assert checked["coerced"] == []
    assert {k: checked[k] for k in VALID} == VALID


def test_out_of_vocabulary_and_missing_fields_are_defaulted_and_listed(hybrid):
    checked = hybrid.validate_model_prediction(
        {"language": "klingon", "theme": "taste", "product": "bissap", "is_spam": "false"}
    )

    assert checked["language"] == "other"      # hors vocabulaire -> valeur par défaut
    assert checked["sentiment"] == "neutral"   # champ absent -> valeur par défaut
    assert checked["coerced"] == ["language", "sentiment"]
    assert checked["is_spam"] is False


def test_a_model_can_never_write_a_free_text_or_a_number(hybrid):
    checked = hybrid.validate_model_prediction(
        {**VALID, "sentiment": "les ventes ont augmenté de 25 %", "theme": 42}
    )

    assert checked["sentiment"] in hybrid.SENTIMENTS
    assert checked["theme"] in hybrid.THEMES


def test_defaulted_answers_are_reported_at_the_end_of_the_run(hybrid, monkeypatch, capsys):
    def fake_batch(texts, tokenizer, model):
        return [
            hybrid.validate_model_prediction({**VALID, "language": "klingon"})
            for _ in texts
        ]

    monkeypatch.setattr(hybrid, "model_classification_batch", fake_batch)
    hybrid.main()

    output = capsys.readouterr().out
    assert "[ATTENTION]" in output and "language" in output

    saved = read_output(hybrid)
    assert set(saved["language_model"]) == {"other"}
    assert "coerced" not in saved.columns   # la trace reste dans le journal, pas dans la donnée


# ---------------------------------------------------------------------------
# Règles déterministes et fusion
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "text",
    [
        "le prix a encore monté ?",          # "a" n'est pas un marqueur anglais
        "svp on ne trouve plus c'est fini ?",  # "on" non plus
        "belle campagne pour la CAN",        # ni "can"
        "hey vous livrez sur Riviera 3 ?",   # ni "hey"
    ],
)
def test_french_words_are_not_taken_for_english(hybrid, text):
    assert hybrid.rule_language(text) == "fr"


def test_rupture_is_detected_as_availability(hybrid):
    assert hybrid.rule_theme("rupture partout à Angré") == "availability"


def test_product_is_derived_from_theme_and_never_taken_from_the_model(hybrid):
    model = {"language": "fr", "sentiment": "negative", "theme": "packaging",
             "is_spam": False, "product": "bouye"}
    no_product = {"language": "fr", "sentiment": None, "theme": None,
                  "product": None, "is_spam": None}

    assert hybrid.merge_prediction(no_product, model)["product"] == "unknown"
    assert hybrid.merge_prediction(
        no_product, {**model, "theme": "promotion"}
    )["product"] == "none"
    assert hybrid.merge_prediction(
        {**no_product, "product": "bissap"}, model
    )["product"] == "bissap"


def test_emoji_only_comment_needs_no_model(hybrid):
    rules = hybrid.deterministic_classification("❤️❤️❤️")

    assert rules == {"language": "other", "sentiment": "positive",
                     "theme": "other", "product": "none", "is_spam": False}
    assert hybrid.is_complete(rules)


def test_spam_has_no_opinion_theme_or_product(hybrid):
    rules = hybrid.deterministic_classification("Boostez vos followers 📈 DM")

    assert rules["is_spam"] is True
    assert (rules["sentiment"], rules["theme"], rules["product"]) == ("neutral", "other", "none")


def test_identical_texts_are_sent_to_the_model_once(hybrid, monkeypatch):
    calls = []
    install_model(hybrid, monkeypatch, calls)

    outcomes = hybrid.classify_batch(
        ["avis client numero 1", "AVIS CLIENT NUMERO 1 ", "avis client numero 2"],
        None, None,
    )

    assert [t for batch in calls for t in batch] == ["avis client numero 1", "avis client numero 2"]
    assert outcomes[0]["final"] == outcomes[1]["final"]
