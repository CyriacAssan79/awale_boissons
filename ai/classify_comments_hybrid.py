from __future__ import annotations

import json
import re
import time
from pathlib import Path

import pandas as pd
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"

INPUT_FILE = Path("data/processed/social_comments_for_ai.csv")
OUTPUT_FILE = Path(
    "ai/evaluation/social_comments_predictions_v2_full.csv"
)
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

PRODUCTS = {
    "bissap",
    "gingembre",
    "bouye",
    "multiple",
    "none",
    "unknown",
}


SYSTEM_PROMPT = """
Tu es un classifieur de commentaires clients Awalé Boissons.

Retourne UNIQUEMENT un JSON valide :

{
  "language": "fr",
  "sentiment": "positive",
  "theme": "taste",
  "product": "none",
  "is_spam": false
}

Valeurs autorisées :

language:
fr | nouchi | en | mixed | other

sentiment:
positive | negative | neutral

theme:
taste | price | availability | delivery | packaging | health |
service | promotion | product_question | other

product:
bissap | gingembre | bouye | multiple | none | unknown

is_spam:
true | false

Règles importantes :

- Ne jamais inventer une catégorie.
- Ne jamais inventer un produit.
- product = bissap uniquement si bissap ou hibiscus est explicitement mentionné.
- product = gingembre uniquement si gingembre est explicitement mentionné.
- product = bouye uniquement si bouye est explicitement mentionné.
- Plusieurs produits explicitement cités → multiple.
- Aucun produit identifiable → none.
- Information insuffisante → unknown.

Pour le sentiment :
- avis favorable → positive
- plainte ou avis défavorable → negative
- question ou information sans polarité claire → neutral

Pour le thème :
- goût, frais, sucré, délicieux → taste
- prix, cher → price
- stock, rupture, plus rien, en rayon → availability
- livraison, commande livrée → delivery
- bouteille, étiquette, emballage, fuite, format → packaging
- sucre ajouté, conservateurs, santé, ingrédients → health
- service client → service
- publicité, pub, radio, TikTok, influence, stand → promotion
- question concernant un produit → product_question
- sinon → other

Ne renvoie aucun texte en dehors du JSON.
"""


# ---------------------------------------------------------------------
# Règles déterministes
# ---------------------------------------------------------------------

NOUCHI_TERMS = {
    "dèh",
    "deh",
    "wallah",
    "no drap",
    "enjai",
    "enjaillant",
    "paa",
    "wê",
    "we ",
}


SPAM_PATTERNS = [
    r"\bboostez?\s+vos\s+followers\b",
    r"\bsuis[- ]moi\b",
    r"\bje\s+te\s+suis\b",
    r"\bpr[êe]t\s+d[' ]argent\b",
    r"\bsans\s+garantie\b.*\bcontact",
    r"\bdm\b.*\b(follow|followers|abonne)",
]


THEME_RULES = {
    "availability": [
        r"\bstock\s+fini\b",
        r"\bstock\b",
        r"\brupture\b",
        r"\bplus\s+de\b",
        r"\bplus\s+rien\b",
        r"\brien\s+en\s+rayon\b",
        r"\bpas\s+au\s+maquis\b",
        r"\bon\s+ne\s+trouve\s+plus\b",
        r"\bc[' ]est\s+fini\b",
    ],
    "packaging": [
        r"\bbouteille\b",
        r"\bbouteilles\b",
        r"\bfuit\b",
        r"\bfuite\b",
        r"\b[ée]tiquette\b",
        r"\b33cl\b",
        r"\b1l\b",
        r"\bemballage\b",
        r"\bformat\b",
    ],
    "price": [
        r"\bprix\b",
        r"\bcher\b",
        r"\bco[uû]te\b",
    ],
    "promotion": [
        r"\bpub\b",
        r"\bpublicit",
        r"\btiktok\b",
        r"\bradio\b",
        r"\binfluence",
        r"\bstand\b",
        r"\bboost",
    ],
    "delivery": [
        r"\blivraison\b",
        r"\bcommand[ée]\b",
        r"\bcommande\b",
        r"\bwhatsapp\b",
        r"\blivr[ée]\b",
        r"\barriv[ée]\b",
    ],
    "health": [
        r"\bsucre\b",
        r"\bsucr[ée]",
        r"\bconservateur",
        r"\bingr[ée]dient",
        r"\bsant[ée]\b",
    ],
}


POSITIVE_PATTERNS = [
    r"\btop\b",
    r"\bparfait\b",
    r"\bexcellent\b",
    r"\bbravo\b",
    r"\bbon\b",
    r"\bbonne\b",
    r"\bmeilleur\b",
    r"\bdoux\b",
    r"\bdrôle\b",
    r"\benjaillant\b",
    r"\bfranchement\b.*\bbien\b",
    r"\bne\s+regrette\s+pas\b",
    r"😍",
    r"😋",
    r"👍",
    r"❤️",
    r"🔥",
    r"👏",
]


NEGATIVE_PATTERNS = [
    r"\bcher\b",
    r"\bfuit\b",
    r"\bfuite\b",
    r"\brupture\b",
    r"\bstock\s+fini\b",
    r"\bplus\s+rien\b",
    r"\barr[êe]tez\b",
    r"\bannul[ée]\b",
    r"\bfrustr",
    r"😤",
    r"😭",
]


def normalize_text(text: str) -> str:
    return str(text).strip().lower()


def contains_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def rule_language(text: str) -> str | None:
    t = normalize_text(text)

    # Anglais évident
    english_patterns = [
        r"\bthe\b",
        r"\bis\b",
        r"\bgreat\b",
        r"\bone\b",
        r"\bsweet\b",
        r"\bplease\b",
    ]

    has_english = contains_any(t, english_patterns)

    has_nouchi = any(term in t for term in NOUCHI_TERMS)

    has_french = bool(
        re.search(
            r"\b(le|la|les|de|du|des|est|c'est|pour|avec|dans|"
            r"plus|bien|très|mon|ma|je|vous|on)\b",
            t,
        )
    )

    if has_nouchi and has_french:
        return "nouchi"

    if has_nouchi:
        return "nouchi"

    if has_english and has_french:
        return "mixed"

    if has_english:
        return "en"

    # emoji seul : on laisse le modèle décider
    return None


def rule_spam(text: str) -> bool | None:
    t = normalize_text(text)

    if contains_any(t, SPAM_PATTERNS):
        return True

    return None


def rule_product(text: str) -> str | None:
    t = normalize_text(text)

    found = set()

    if re.search(r"\bbissap\b|\bhibiscus\b", t):
        found.add("bissap")

    if re.search(r"\bgingembre\b", t):
        found.add("gingembre")

    if re.search(r"\bbouye\b", t):
        found.add("bouye")

    if len(found) > 1:
        return "multiple"

    if len(found) == 1:
        return next(iter(found))

    return None


def rule_theme(text: str) -> str | None:
    t = normalize_text(text)

    # Les thèmes les plus explicites passent en premier.
    for theme, patterns in THEME_RULES.items():
        if contains_any(t, patterns):
            return theme

    # Quelques règles sémantiques simples
    if re.search(r"\b(quels?|quelle|version|comment)\b", t):
        if re.search(r"\bproduit|sucre|bissap|gingembre|bouye\b", t):
            return "product_question"

    return None


def rule_sentiment(text: str) -> str | None:
    t = normalize_text(text)

    positive = contains_any(t, POSITIVE_PATTERNS)
    negative = contains_any(t, NEGATIVE_PATTERNS)

    if positive and not negative:
        return "positive"

    if negative and not positive:
        return "negative"

    return None


def deterministic_classification(text: str) -> dict:
    return {
        "language": rule_language(text),
        "sentiment": rule_sentiment(text),
        "theme": rule_theme(text),
        "product": rule_product(text),
        "is_spam": rule_spam(text),
    }


def is_complete(result: dict) -> bool:
    """
    Le modèle local n'est utilisé que si toutes les dimensions
    principales sont déterminables par les règles.
    """
    required = [
        "language",
        "sentiment",
        "theme",
        "product",
        "is_spam",
    ]

    return all(result[k] is not None for k in required)


# ---------------------------------------------------------------------
# Modèle local
# ---------------------------------------------------------------------

def extract_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError(f"JSON introuvable: {text}")

    return json.loads(text[start:end + 1])


def validate_model_prediction(pred: dict) -> dict:
    language = str(pred.get("language", "other")).strip().lower()
    sentiment = str(pred.get("sentiment", "neutral")).strip().lower()
    theme = str(pred.get("theme", "other")).strip().lower()
    product = str(pred.get("product", "unknown")).strip().lower()

    spam = pred.get("is_spam", False)

    if isinstance(spam, str):
        spam = spam.strip().lower() in {"true", "1", "yes"}

    if language not in LANGUAGES:
        language = "other"

    if sentiment not in SENTIMENTS:
        sentiment = "neutral"

    if theme not in THEMES:
        theme = "other"

    if product not in PRODUCTS:
        product = "unknown"

    return {
        "language": language,
        "sentiment": sentiment,
        "theme": theme,
        "product": product,
        "is_spam": bool(spam),
    }


def load_model():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    tokenizer.padding_side = "left"

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        torch_dtype=torch.float32,
        device_map="auto",
    )

    model.eval()

    return tokenizer, model

def model_classification(text: str, tokenizer, model) -> dict:
    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT,
        },
        {
            "role": "user",
            "content": f"Classe ce commentaire :\n\n{text}",
        },
    ]

    prompt = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    device = next(model.parameters()).device

    inputs = tokenizer(
        prompt,
        return_tensors="pt",
    ).to(device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=120,
            do_sample=False,
        )

    generated = outputs[0][inputs["input_ids"].shape[1]:]

    response = tokenizer.decode(
        generated,
        skip_special_tokens=True,
    )

    return validate_model_prediction(
        extract_json(response)
    )

def model_classification_batch(
    texts: list[str],
    tokenizer,
    model,
) -> list[dict]:

    messages_batch = []

    for text in texts:
        messages_batch.append([
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            {
                "role": "user",
                "content": f"Classe ce commentaire :\n\n{text}",
            },
        ])

    prompts = [
        tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )
        for messages in messages_batch
    ]

    device = next(model.parameters()).device

    inputs = tokenizer(
        prompts,
        return_tensors="pt",
        padding=True,
        truncation=True,
    ).to(device)

    with torch.inference_mode():

        outputs = model.generate(
            **inputs,
            max_new_tokens=80,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )

    predictions = []

    for i in range(len(texts)):

        generated = outputs[i][inputs["input_ids"].shape[1]:]

        response = tokenizer.decode(
            generated,
            skip_special_tokens=True,
        )

        predictions.append(
            validate_model_prediction(
                extract_json(response)
            )
        )

    return predictions

def main():

    df = pd.read_csv(INPUT_FILE)

    print(f"Commentaires chargés : {len(df)}")

    tokenizer, model = load_model()

    BATCH_SIZE = 4

    results = []

    for start_idx in range(0, len(df), BATCH_SIZE):

        batch = df.iloc[start_idx:start_idx + BATCH_SIZE]

        texts = [
            str(text)
            for text in batch["comment_text"]
        ]

        batch_start = time.perf_counter()

        rules_batch = [
            deterministic_classification(text)
            for text in texts
        ]

        model_indices = [
            i
            for i, rules in enumerate(rules_batch)
            if not is_complete(rules)
        ]

        model_predictions = {}

        if model_indices:

            texts_for_model = [
                texts[i]
                for i in model_indices
            ]

            predictions = model_classification_batch(
                texts_for_model,
                tokenizer,
                model,
            )

            for local_idx, prediction in zip(
                model_indices,
                predictions,
            ):
                model_predictions[local_idx] = prediction

        for i, (_, row) in enumerate(batch.iterrows()):

            rules = rules_batch[i]

            if i in model_predictions:

                model_prediction = model_predictions[i]

                prediction = {
                    "language": (
                        rules["language"]
                        if rules["language"] is not None
                        else model_prediction["language"]
                    ),
                    "sentiment": (
                        rules["sentiment"]
                        if rules["sentiment"] is not None
                        else model_prediction["sentiment"]
                    ),
                    "theme": (
                        rules["theme"]
                        if rules["theme"] is not None
                        else model_prediction["theme"]
                    ),
                    "product": (
                        rules["product"]
                        if rules["product"] is not None
                        else model_prediction["product"]
                    ),
                    "is_spam": (
                        rules["is_spam"]
                        if rules["is_spam"] is not None
                        else model_prediction["is_spam"]
                    ),
                }

                model_used = True

            else:

                prediction = rules
                model_used = False

            results.append({
                "comment_id": row["comment_id"],
                "comment_text": row["comment_text"],
                "language_model": prediction["language"],
                "sentiment_model": prediction["sentiment"],
                "theme_model": prediction["theme"],
                "product_model": prediction["product"],
                "is_spam_model": prediction["is_spam"],
                "model_used": model_used,
                "rules_complete": is_complete(rules),
            })

        elapsed = time.perf_counter() - batch_start

        print(
            f"[{start_idx + 1}/{len(df)}] "
            f"batch={len(batch)} | "
            f"model={len(model_indices)} | "
            f"{elapsed:.2f}s"
        )

    output = pd.DataFrame(results)

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print("\n" + "=" * 70)
    print("RÉSULTAT V2 HYBRIDE — FULL DATASET")
    print("=" * 70)

    print(f"Total               : {len(output)}")
    print(
        f"Règles seules       : "
        f"{(~output['model_used']).sum()}"
    )
    print(
        f"Modèle local utilisé: "
        f"{output['model_used'].sum()}"
    )
    print(f"Output              : {OUTPUT_FILE}")

if __name__ == "__main__":
    main()