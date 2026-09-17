from __future__ import annotations

import json
import time
from pathlib import Path

import pandas as pd
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"

INPUT_FILE = Path("ai/evaluation/labeled_sample.csv")
OUTPUT_FILE = Path("ai/evaluation/model_predictions_local.csv")


LANGUAGES = {"fr", "nouchi", "en", "mixed", "other"}
SENTIMENTS = {"positive", "negative", "neutral"}
THEMES = {
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
}
PRODUCTS = {"bissap", "gingembre", "bouye", "multiple", "none", "unknown"}

THEME_ALIASES = {
    "quality": "taste",
    "sweetness": "taste",
    "degustation": "taste",
    "food": "taste",

    "bouteille": "packaging",
    "couleur": "packaging",

    "radio": "promotion",
    "tiktok": "promotion",
    "boosting followers": "promotion",
    "boosting": "promotion",
    "stand organized": "promotion",

    "question sur un produit": "product_question",
    "achat": "product_question",

    "stock fini": "availability",
    "fini": "availability",
    "location": "availability",

    "annulation": "service",
    "disconnection": "service",
    "frustration": "service",

    "bouye": "other",
    "jeux de mots": "other",
    "friendship": "other",
    "conservateur": "health",
}

PRODUCT_ALIASES = {
    "hibiscus": "bissap",
    "stock fini": "none",
    "rayon": "none",
    "prix": "none",
    "pubs": "none",
    "argent rapide": "none",
}

SYSTEM_PROMPT = """
Tu classes un commentaire client Awalé Boissons.

Retourne UNIQUEMENT ce JSON :
{
  "language": "fr",
  "sentiment": "positive",
  "theme": "taste",
  "product": "bissap",
  "is_spam": false
}

VALEURS STRICTEMENT AUTORISÉES :

language = fr | nouchi | en | mixed | other

sentiment = positive | negative | neutral

theme = taste | price | availability | delivery | packaging | health | service | promotion | product_question | other

product = bissap | gingembre | bouye | multiple | none | unknown

is_spam = true | false

RÈGLES :

language :
français → fr
Nouchi identifiable → nouchi
anglais → en
plusieurs langues → mixed
autre/impossible → other

sentiment :
avis favorable → positive
plainte/avis défavorable → negative
question/information/neutre → neutral

theme :
goût/fraîcheur/sucré → taste
prix → price
stock/disponibilité/en rayon → availability
livraison/commande livrée → delivery
bouteille/emballage/fuite/format → packaging
santé/ingrédients/effets → health
service client → service
pub/publicité/TikTok/radio/influence → promotion
question concernant un produit → product_question
sinon → other

product :
bissap mentionné → bissap
gingembre mentionné → gingembre
bouye mentionné → bouye
plusieurs produits explicitement mentionnés → multiple
aucun produit identifiable → none
information insuffisante → unknown

IMPORTANT :
- Le texte du commentaire ne doit JAMAIS être copié dans les catégories.
- "radio", "TikTok", "WhatsApp", "svp", "prix", "fuite", "Yopougon", etc. ne sont PAS des valeurs product.
- Pour product, choisis UNIQUEMENT parmi : bissap, gingembre, bouye, multiple, none, unknown.
- Pour theme, choisis UNIQUEMENT parmi les 10 valeurs indiquées.
- N'invente aucune nouvelle catégorie.
- Retourne uniquement le JSON.
"""


def extract_json(text: str) -> dict:
    text = text.strip()

    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1 or end <= start:
        raise ValueError(f"JSON introuvable dans la réponse: {text}")

    candidate = text[start : end + 1]
    return json.loads(candidate)


def validate_prediction(pred: dict) -> dict:
    language = str(pred.get("language", "")).strip().lower()
    sentiment = str(pred.get("sentiment", "")).strip().lower()
    theme = str(pred.get("theme", "")).strip().lower()
    product = str(pred.get("product", "")).strip().lower()

    spam = pred.get("is_spam", False)

    if isinstance(spam, str):
        spam = spam.strip().lower() in {"true", "1", "yes"}

    # Fallbacks contrôlés
    if language not in LANGUAGES:
        language = "other"

    if sentiment not in SENTIMENTS:
        sentiment = "neutral"

    if theme not in THEMES:
        theme = "other"

    if product not in PRODUCTS:
        product = "unknown"

    return {
        "language_model": language,
        "sentiment_model": sentiment,
        "theme_model": theme,
        "product_model": product,
        "is_spam_model": bool(spam),
    }


def build_prompt(comment: str) -> str:
    return f"""
Classe ce commentaire selon les règles précédentes.

COMMENTAIRE:
{comment}
"""


def main() -> None:
    print(f"Chargement du modèle : {MODEL_NAME}")

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float32,
        device_map="auto",
    )

    model.eval()

    device = next(model.parameters()).device
    print(f"Device : {device}")

    df = pd.read_csv(INPUT_FILE)

    results = []

    for i, row in df.iterrows():
        comment_id = row["comment_id"]
        comment_text = str(row["comment_text"])

        start_time = time.perf_counter()

        try:
            messages = [
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT,
                },
                {
                    "role": "user",
                    "content": build_prompt(comment_text),
                },
            ]

            text = tokenizer.apply_chat_template(
                messages,
                tokenize=False,
                add_generation_prompt=True,
            )

            inputs = tokenizer(
                text,
                return_tensors="pt",
            ).to(device)

            with torch.no_grad():
                output = model.generate(
                    **inputs,
                    max_new_tokens=120,
                    do_sample=False,
                )

            generated_tokens = output[0][inputs["input_ids"].shape[1] :]

            response_text = tokenizer.decode(
                generated_tokens,
                skip_special_tokens=True,
            )

            prediction = extract_json(response_text)
            prediction = validate_prediction(prediction)

            error = None

        except Exception as exc:
            prediction = {
                "language_model": None,
                "sentiment_model": None,
                "theme_model": None,
                "product_model": None,
                "is_spam_model": None,
            }

            error = f"{type(exc).__name__}: {exc}"

        runtime = time.perf_counter() - start_time

        results.append(
            {
                "comment_id": comment_id,
                "comment_text": comment_text,
                **prediction,
                "runtime_seconds": runtime,
                "error": error,
            }
        )

        status = "OK" if error is None else "ERROR"

        print(
            f"[{i + 1}/{len(df)}] "
            f"{comment_id} | {status} | {runtime:.2f}s"
        )

    out = pd.DataFrame(results)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(OUTPUT_FILE, index=False)

    success = out["error"].isna().sum()
    failed = out["error"].notna().sum()

    print("\n" + "=" * 70)
    print("RÉSULTAT")
    print("=" * 70)
    print(f"Total       : {len(out)}")
    print(f"Succès      : {success}")
    print(f"Échecs      : {failed}")
    print(f"Couverture  : {success / len(out) * 100:.2f}%")
    print(
        f"Temps moyen : "
        f"{out['runtime_seconds'].mean():.2f}s/commentaire"
    )
    print(f"Output      : {OUTPUT_FILE}")


if __name__ == "__main__":
    main()