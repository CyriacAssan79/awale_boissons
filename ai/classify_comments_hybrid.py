from __future__ import annotations

import hashlib
import json
import os
import re
import sys
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


# Le prompt vit dans un fichier versionné (ai/prompts/), pas dans le code : on
# le relit, on le compare et on le fait évoluer sans toucher au script. Toute
# modification du prompt doit passer par un nouveau fichier (v3, ...) et par un
# nouveau passage du benchmark humain (voir docs/ai_documentation.ipynb).
PROMPT_FILE = (
    Path(__file__).resolve().parent / "prompts" / "comment_classifier_v2_hybrid.txt"
)
SYSTEM_PROMPT = PROMPT_FILE.read_text(encoding="utf-8")
PROMPT_VERSION = PROMPT_FILE.stem
PROMPT_SHA256 = hashlib.sha256(SYSTEM_PROMPT.encode("utf-8")).hexdigest()[:12]

# Sauvegarde intermédiaire : toutes les N batches (4 commentaires par batch,
# soit ~2 minutes de calcul pour 5 batches). Un plantage ou un Ctrl+C ne fait
# perdre que le travail depuis la dernière sauvegarde, jamais tout le run.
CHECKPOINT_EVERY_BATCHES = 5


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
    """Ramène la réponse du modèle à un vocabulaire fermé.

    Garde-fou : le modèle ne peut produire que des catégories connues, jamais un
    nombre ni un libellé libre. Une réponse absente ou hors vocabulaire est
    remplacée par une valeur par défaut, MAIS le champ concerné est listé dans
    "coerced" et le script en affiche le total : un remplacement n'est jamais
    silencieux.
    """
    coerced = []

    def pick(field: str, allowed: set, default: str) -> str:
        value = str(pred.get(field, default)).strip().lower()

        if field not in pred or value not in allowed:
            coerced.append(field)
            return default

        return value

    language = pick("language", LANGUAGES, "other")
    sentiment = pick("sentiment", SENTIMENTS, "neutral")
    theme = pick("theme", THEMES, "other")
    product = pick("product", PRODUCTS, "unknown")

    spam = pred.get("is_spam", False)

    if isinstance(spam, str):
        spam = spam.strip().lower() in {"true", "1", "yes"}

    return {
        "language": language,
        "sentiment": sentiment,
        "theme": theme,
        "product": product,
        "is_spam": bool(spam),
        "coerced": coerced,
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

OUTPUT_COLUMNS = [
    "comment_id",
    "comment_text",
    "language_model",
    "sentiment_model",
    "theme_model",
    "product_model",
    "is_spam_model",
    "model_used",
    "rules_complete",
]


def classify_with_fallback(texts, tokenizer, model):
    """Classe un lot ; si la sortie du modèle est illisible, retente chaque texte seul.

    Un seul JSON invalide ne doit pas faire échouer le lot entier (et donc le run).
    Retourne deux listes alignées sur `texts` : les prédictions (None en cas
    d'échec) et le message d'erreur correspondant.
    """
    try:
        predictions = list(model_classification_batch(texts, tokenizer, model))
        return predictions, [None] * len(texts)
    except (ValueError, KeyError, TypeError):
        # json.JSONDecodeError est une ValueError : on retombe ici pour tout
        # JSON introuvable ou invalide.
        pass

    predictions, errors = [], []

    for text in texts:
        try:
            predictions.append(model_classification_batch([text], tokenizer, model)[0])
            errors.append(None)
        except (ValueError, KeyError, TypeError) as error:
            predictions.append(None)
            errors.append(str(error)[:200])

    return predictions, errors


def write_predictions(existing: pd.DataFrame, new_predictions: pd.DataFrame) -> pd.DataFrame:
    """Fusionne l'existant et les nouvelles prédictions, puis écrit OUTPUT_FILE.

    L'écriture est atomique (fichier temporaire puis remplacement) : une
    interruption pendant l'écriture ne peut pas laisser un fichier tronqué. Comme
    le script ne classe que les comment_id absents de OUTPUT_FILE, relancer après
    une interruption reprend exactement où le run s'est arrêté.
    """
    output = (
        pd.concat([existing, new_predictions], ignore_index=True)
        .drop_duplicates(subset="comment_id", keep="last")
        .sort_values("comment_id")
        .reset_index(drop=True)
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    tmp_file = OUTPUT_FILE.with_suffix(OUTPUT_FILE.suffix + ".tmp")
    output.to_csv(tmp_file, index=False)
    os.replace(tmp_file, OUTPUT_FILE)

    return output


def load_existing_predictions() -> pd.DataFrame:
    """Prédictions déjà produites lors d'un run précédent, s'il y en a.

    Le traitement est incrémental : un commentaire déjà présent ici n'est
    jamais reclassé. Pour forcer une reclassification complète (nouvelle
    version de modèle ou de prompt), supprimer OUTPUT_FILE avant de lancer.
    """
    if not OUTPUT_FILE.exists():
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    return pd.read_csv(OUTPUT_FILE)


def main():

    df = pd.read_csv(INPUT_FILE)
    existing = load_existing_predictions()

    already_done = set(existing["comment_id"])
    df = df[~df["comment_id"].isin(already_done)].reset_index(drop=True)

    print(f"Commentaires source            : {len(existing) + len(df)}")
    print(f"Déjà classés (runs précédents) : {len(existing)}")
    print(f"À classer ce run               : {len(df)}")

    if df.empty:
        print("\nRien à classer ce mois-ci — prédictions déjà à jour.")
        print(f"Output : {OUTPUT_FILE}")
        return

    print(f"Prompt : {PROMPT_FILE.name} (sha256 {PROMPT_SHA256})")

    tokenizer, model = load_model()

    BATCH_SIZE = 4

    results = []
    failed = []
    coerced_log = []

    total_batches = (len(df) + BATCH_SIZE - 1) // BATCH_SIZE

    try:

        for batch_number, start_idx in enumerate(range(0, len(df), BATCH_SIZE), start=1):

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
            model_errors = {}

            if model_indices:

                texts_for_model = [
                    texts[i]
                    for i in model_indices
                ]

                predictions, errors = classify_with_fallback(
                    texts_for_model,
                    tokenizer,
                    model,
                )

                for local_idx, prediction, error in zip(
                    model_indices,
                    predictions,
                    errors,
                ):
                    if prediction is None:
                        model_errors[local_idx] = error
                    else:
                        model_predictions[local_idx] = prediction

            for i, (_, row) in enumerate(batch.iterrows()):

                rules = rules_batch[i]

                if i in model_errors:
                    # Le modèle n'a pas produit de sortie exploitable : on ne
                    # devine rien et on n'enregistre rien. Le commentaire n'est
                    # pas dans OUTPUT_FILE, il sera donc retenté au prochain run.
                    failed.append((row["comment_id"], model_errors[i]))
                    continue

                if i in model_predictions:

                    model_prediction = model_predictions[i]

                    if model_prediction.get("coerced"):
                        coerced_log.append(
                            (row["comment_id"], model_prediction["coerced"])
                        )

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

            if batch_number % CHECKPOINT_EVERY_BATCHES == 0 and batch_number < total_batches:
                write_predictions(
                    existing,
                    pd.DataFrame(results, columns=OUTPUT_COLUMNS),
                )
                print(
                    f"    sauvegarde intermédiaire : {len(existing) + len(results)} "
                    f"commentaires enregistrés dans {OUTPUT_FILE.name}"
                )

    finally:
        # Sauvegarde finale, y compris après une erreur ou un Ctrl+C : ce qui a
        # déjà été classé n'est jamais perdu.
        new_predictions = pd.DataFrame(results, columns=OUTPUT_COLUMNS)
        output = write_predictions(existing, new_predictions)

    print("\n" + "=" * 70)
    print("RÉSULTAT V2 HYBRIDE — INCRÉMENTAL")
    print("=" * 70)

    print(f"Classés ce run       : {len(new_predictions)}")
    print(
        f"  dont règles seules  : "
        f"{(~new_predictions['model_used']).sum()}"
    )
    print(
        f"  dont modèle local   : "
        f"{new_predictions['model_used'].sum()}"
    )
    print(f"Total accumulé (fichier) : {len(output)}")
    print(f"Output                   : {OUTPUT_FILE}")

    if coerced_log:
        fields = sorted({f for _, fs in coerced_log for f in fs})
        print(
            f"\n[ATTENTION] {len(coerced_log)} commentaire(s) dont la réponse du modèle "
            f"était absente ou hors vocabulaire (champs : {', '.join(fields)}) ont reçu "
            "la valeur par défaut. À surveiller : une hausse signale un modèle ou un "
            "prompt qui dérive."
        )

    if failed:
        print(f"\n[ERREUR] {len(failed)} commentaire(s) sans sortie exploitable du modèle :")
        for comment_id, error in failed[:20]:
            print(f"  - {comment_id} : {error}")
        print(
            "Ils ne sont PAS enregistrés et seront retentés au prochain lancement. "
            "Le rapport ne doit pas être livré tant qu'ils manquent."
        )
        sys.exit(1)


if __name__ == "__main__":
    main()