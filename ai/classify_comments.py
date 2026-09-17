from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

import pandas as pd
from dotenv import load_dotenv
from openai import OpenAI, RateLimitError
from tenacity import retry, stop_after_attempt, wait_exponential


ROOT = Path("/mnt/c/Users/KSOMS/Favorites/awale_boissons")

SAMPLE_PATH = ROOT / "ai/evaluation/labeled_sample.csv"
PROMPT_PATH = ROOT / "ai/prompts/comment_classifier_v1.txt"
OUTPUT_PATH = ROOT / "ai/evaluation/model_predictions.csv"

MODEL = "gpt-4.1-mini"

# Délai volontaire entre deux appels
REQUEST_DELAY_SECONDS = 2


load_dotenv(ROOT / ".env")


def load_prompt() -> str:
    if not PROMPT_PATH.exists():
        raise FileNotFoundError(
            f"Prompt introuvable : {PROMPT_PATH}"
        )

    return PROMPT_PATH.read_text(encoding="utf-8")


def validate_prediction(data: dict[str, Any]) -> dict[str, Any]:

    allowed = {
        "language": {
            "fr",
            "nouchi",
            "en",
            "mixed",
            "other",
        },
        "sentiment": {
            "positive",
            "negative",
            "neutral",
        },
        "theme": {
            "taste",
            "price",
            "availability",
            "delivery",
            "packaging",
            "health",
            "service",
            "promotion",
            "product_question",
            "other",
        },
        "product": {
            "bissap",
            "gingembre",
            "bouye",
            "multiple",
            "none",
            "unknown",
        },
    }

    required = [
        "language",
        "sentiment",
        "theme",
        "product",
        "is_spam",
    ]

    for field in required:
        if field not in data:
            raise ValueError(
                f"Champ manquant : {field}"
            )

    for field, values in allowed.items():
        if data[field] not in values:
            raise ValueError(
                f"Valeur invalide pour {field}: "
                f"{data[field]}"
            )

    if not isinstance(data["is_spam"], bool):
        raise ValueError(
            "is_spam doit être un booléen"
        )

    return data


@retry(
    retry=lambda retry_state: isinstance(
        retry_state.outcome.exception(),
        RateLimitError,
    ),
    stop=stop_after_attempt(6),
    wait=wait_exponential(
        multiplier=3,
        min=5,
        max=60,
    ),
    reraise=True,
)
def classify_comment(
    client: OpenAI,
    system_prompt: str,
    comment: str,
) -> dict[str, Any]:

    response = client.chat.completions.create(
        model=MODEL,
        temperature=0,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": system_prompt,
            },
            {
                "role": "user",
                "content": comment,
            },
        ],
    )

    content = response.choices[0].message.content

    if not content:
        raise ValueError(
            "Réponse LLM vide"
        )

    result = json.loads(content)

    return validate_prediction(result)


def main() -> None:

    if not SAMPLE_PATH.exists():
        raise FileNotFoundError(
            f"Échantillon introuvable : {SAMPLE_PATH}"
        )

    if not PROMPT_PATH.exists():
        raise FileNotFoundError(
            f"Prompt introuvable : {PROMPT_PATH}"
        )

    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY est absent du fichier .env"
        )

    df = pd.read_csv(SAMPLE_PATH)

    if len(df) == 0:
        raise ValueError(
            "Le fichier d'annotation est vide"
        )

    system_prompt = load_prompt()
    client = OpenAI(api_key=api_key)

    # ---------------------------------------------------------
    # Charger les résultats existants pour permettre la reprise
    # ---------------------------------------------------------

    existing = {}

    if OUTPUT_PATH.exists():

        previous = pd.read_csv(
            OUTPUT_PATH,
            dtype={"comment_id": str},
        )

        for _, row in previous.iterrows():

            # On ne considère comme terminé que les prédictions
            # complètement valides.
            required_predictions = [
                "language_model",
                "sentiment_model",
                "theme_model",
                "product_model",
                "is_spam_model",
            ]

            if all(
                pd.notna(row.get(column))
                for column in required_predictions
            ):
                existing[str(row["comment_id"])] = row.to_dict()

        print(
            f"Prédictions déjà valides : "
            f"{len(existing)}"
        )

    results = list(existing.values())

    total_start = time.perf_counter()

    for index, row in df.iterrows():

        comment_id = str(row["comment_id"])
        comment = str(row["comment_text"])

        # -----------------------------------------------------
        # Ne pas retraiter une prédiction déjà réussie
        # -----------------------------------------------------

        if comment_id in existing:

            print(
                f"[{index + 1}/{len(df)}] "
                f"{comment_id} → déjà traité"
            )

            continue

        print(
            f"\n[{index + 1}/{len(df)}] "
            f"Traitement de {comment_id}"
        )

        start = time.perf_counter()

        try:

            prediction = classify_comment(
                client,
                system_prompt,
                comment,
            )

            error = None

            print(
                f"  ✓ {prediction}"
            )

        except RateLimitError as exc:

            print(
                f"RateLimitError : {exc}"
            )

            prediction = {
                "language": None,
                "sentiment": None,
                "theme": None,
                "product": None,
                "is_spam": None,
            }

            error = (
                f"RateLimitError: {exc}"
            )

        except Exception as exc:

            print(
                f"{type(exc).__name__}: {exc}"
            )

            prediction = {
                "language": None,
                "sentiment": None,
                "theme": None,
                "product": None,
                "is_spam": None,
            }

            error = (
                f"{type(exc).__name__}: {exc}"
            )

        elapsed = (
            time.perf_counter() - start
        )

        result = {
            "comment_id": comment_id,
            "comment_text": comment,

            "language_model":
                prediction["language"],

            "sentiment_model":
                prediction["sentiment"],

            "theme_model":
                prediction["theme"],

            "product_model":
                prediction["product"],

            "is_spam_model":
                prediction["is_spam"],

            "runtime_seconds": elapsed,

            "error": error,
        }

        results.append(result)

        # -----------------------------------------------------
        # Sauvegarde immédiate
        # -----------------------------------------------------

        output = pd.DataFrame(results)

        output.to_csv(
            OUTPUT_PATH,
            index=False,
            encoding="utf-8-sig",
        )

        print(
            f"  Temps : {elapsed:.2f}s"
        )

        print(
            f"  Sauvegardé : {OUTPUT_PATH}"
        )

        # -----------------------------------------------------
        # Petit délai entre les requêtes
        # -----------------------------------------------------

        if index < len(df) - 1:

            time.sleep(
                REQUEST_DELAY_SECONDS
            )

    total_runtime = (
        time.perf_counter() - total_start
    )

    output = pd.DataFrame(results)

    print("\n" + "=" * 70)
    print("CLASSIFICATION TERMINÉE")
    print("=" * 70)

    print(
        f"Commentaires : {len(output)}"
    )

    print(
        f"Prédictions valides : "
        f"{output['language_model'].notna().sum()}"
    )

    print(
        f"Erreurs : "
        f"{output['error'].notna().sum()}"
    )

    print(
        f"Runtime total : "
        f"{total_runtime:.2f} s"
    )

    print(
        f"Runtime moyen : "
        f"{output.runtime_seconds.mean():.2f} s"
    )

    print(
        f"Sortie : {OUTPUT_PATH}"
    )


if __name__ == "__main__":
    main()