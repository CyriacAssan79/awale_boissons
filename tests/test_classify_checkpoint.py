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
    assert hybrid.SYSTEM_PROMPT == prompt_file.read_text(encoding="utf-8")
    assert "Retourne UNIQUEMENT un JSON valide" in hybrid.SYSTEM_PROMPT
    assert hybrid.PROMPT_VERSION == "comment_classifier_v2_hybrid"


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

VALID = {
    "language": "fr",
    "sentiment": "positive",
    "theme": "taste",
    "product": "bissap",
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
