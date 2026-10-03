"""Interprétation des questions libres par le modèle de langage (Qwen).

Utilisé uniquement quand les règles de question_parser ne reconnaissent
aucune métrique. Répartition des rôles :

- le modèle décide seulement de l'intention : quelle métrique, quel
  découpage, s'il faut un classement, si la question est hors sujet ;
- les faits (produits, canaux, mois, années) sont toujours extraits du
  texte de la question par les règles : le modèle ne peut pas en inventer.

Chaque valeur de la fiche est vérifiée sur des listes fermées. Le modèle
n'écrit jamais de SQL et ne voit aucune donnée.
"""

from __future__ import annotations

import json
import re
from typing import Callable

from .dimensions import resolve_dimension
from .intent import QueryIntent, build_intent
from .question_parser import (
    COMMENT_METRICS,
    comment_platforms,
    extract_mentions,
    extract_period,
    normalize,
)
from .resolver import resolve_metric


# Métriques que le modèle peut proposer (celles prises en charge par les règles).
SUPPORTED_METRICS = ("ca_net", "spend_marketing", "mix_produit", "repartition_sentiment")

ALLOWED_DIMENSIONS = ("month", "channel", "product", "format", "platform")

# Période par défaut pour « récemment », « en ce moment »…
RECENT_MONTHS = 3

# Un classement n'est retenu que si la question compare quelque chose :
# le modèle en ajoute parfois sans raison (« On s'en sort comment ? »).
RANKING_CUES = (
    r"\b(?:plus|moins|mieux|meilleure?s?|pire|top|prefer\w*|favori\w*"
    r"|lequel|laquelle|lesquels|lesquelles|cartonn\w*|domin\w*)\b"
)

OUT_OF_SCOPE_ERROR = (
    "Question hors périmètre : "
    "aucune métrique prise en charge n'a été identifiée."
)

SYSTEM_PROMPT = """Tu analyses une question sur l'activité d'une entreprise de boissons.
Tu ne réponds jamais à la question : tu renvoies uniquement une fiche JSON sur une ligne.

Champs :
- "metric" : "ca_net" (chiffre d'affaires, ventes, activité, ce que ça rapporte),
  "spend_marketing" (dépenses marketing, publicité, budget, coût des campagnes)
  "mix_produit" (répartition des ventes entre les produits, produit préféré)
  ou "repartition_sentiment" (avis, opinion, satisfaction, image auprès des clients).
- "other_metrics" : autres métriques demandées dans la même question, souvent [].
- "dimensions" : découpages parmi "month" (évolution dans le temps),
  "channel" (canaux marketing), "product" (produits), "format" (formats),
  "platform" (réseaux sociaux où les clients commentent).
- "ranking" : "max" si on cherche le meilleur ou le plus grand, "min" le plus petit, sinon null.
- "recent" : true si la question parle de la période récente sans date précise.
- "out_of_scope" : true si la question ne porte ni sur les ventes, ni sur les
  dépenses marketing, ni sur les produits vendus, ni sur l'avis des clients.
"""

# Exemples de questions que les règles ne reconnaissent pas.
EXAMPLES = [
    (
        "Qu'est-ce qui se vend le mieux chez nous ?",
        {"metric": "mix_produit", "other_metrics": [], "dimensions": ["product"],
         "ranking": "max", "recent": False, "out_of_scope": False},
    ),
    (
        "Combien nous ont coûté nos campagnes ?",
        {"metric": "spend_marketing", "other_metrics": [], "dimensions": [],
         "ranking": None, "recent": False, "out_of_scope": False},
    ),
    (
        "Est-ce que le business tourne bien en ce moment ?",
        {"metric": "ca_net", "other_metrics": [], "dimensions": ["month"],
         "ranking": None, "recent": True, "out_of_scope": False},
    ),
    (
        "Où part l'argent de la com ?",
        {"metric": "spend_marketing", "other_metrics": [], "dimensions": ["channel"],
         "ranking": None, "recent": False, "out_of_scope": False},
    ),
    (
        "Les gens aiment-ils ce qu'on fait ?",
        {"metric": "repartition_sentiment", "other_metrics": [], "dimensions": [],
         "ranking": None, "recent": False, "out_of_scope": False},
    ),
    (
        "Quel temps fera-t-il demain ?",
        {"metric": None, "other_metrics": [], "dimensions": [],
         "ranking": None, "recent": False, "out_of_scope": True},
    ),
]


# ---------------------------------------------------------------------
# GÉNÉRATION
# ---------------------------------------------------------------------

def _compact(data: dict) -> str:
    # Fiche compacte : moins de jetons à produire, donc une réponse plus rapide.
    return json.dumps(data, ensure_ascii=False, separators=(",", ":"))


def build_messages(question: str) -> list[dict]:
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for example_question, example_answer in EXAMPLES:
        messages.append({"role": "user", "content": example_question})
        messages.append({"role": "assistant", "content": _compact(example_answer)})

    messages.append({"role": "user", "content": question})
    return messages


def generate_with_model(model_bundle, messages: list[dict], max_new_tokens: int = 80) -> str:
    """Génère la fiche JSON avec le triplet (tokenizer, model, device)."""
    import torch

    tokenizer, model, device = model_bundle

    chat_text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )
    inputs = tokenizer(chat_text, return_tensors="pt")
    inputs = {key: value.to(device) for key, value in inputs.items() if hasattr(value, "to")}
    input_length = inputs["input_ids"].shape[-1]

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )

    return tokenizer.decode(outputs[0][input_length:], skip_special_tokens=True).strip()


# ---------------------------------------------------------------------
# VÉRIFICATION DE LA FICHE
# ---------------------------------------------------------------------

def _extract_json(raw: str) -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)

    if not match:
        raise ValueError(OUT_OF_SCOPE_ERROR)

    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError as exc:
        raise ValueError(OUT_OF_SCOPE_ERROR) from exc

    if not isinstance(data, dict):
        raise ValueError(OUT_OF_SCOPE_ERROR)

    return data


def _as_list(value) -> list:
    if value is None:
        return []

    return value if isinstance(value, list) else [value]


def _metric(value) -> str:
    if value not in SUPPORTED_METRICS:
        raise ValueError(OUT_OF_SCOPE_ERROR)

    return resolve_metric(value)


def intent_from_llm_output(raw: str, question: str) -> QueryIntent:
    """Construit un QueryIntent : intention du modèle + faits extraits de la question."""
    data = _extract_json(raw)

    if data.get("out_of_scope") is True:
        raise ValueError(OUT_OF_SCOPE_ERROR)

    metric = _metric(data.get("metric"))
    other_metrics = [
        m for m in dict.fromkeys(_metric(m) for m in _as_list(data.get("other_metrics")))
        if m != metric
    ]

    dimensions = _as_list(data.get("dimensions"))

    if any(d not in ALLOWED_DIMENSIONS for d in dimensions):
        raise ValueError(OUT_OF_SCOPE_ERROR)

    ranking = data.get("ranking")

    if ranking not in (None, "max", "min"):
        raise ValueError(OUT_OF_SCOPE_ERROR)

    if not re.search(RANKING_CUES, normalize(question)):
        ranking = None

    # Faits : uniquement ce qui est écrit dans la question.
    product, channel = extract_mentions(question)
    period = extract_period(question)
    platform = None

    # Commentaires : Facebook, Instagram, TikTok sont des plateformes.
    if metric in COMMENT_METRICS:
        platform = comment_platforms(normalize(question))
        channel = None

    if isinstance(platform, list) and "platform" not in dimensions:
        dimensions.insert(0, "platform")

    if not period and data.get("recent") is True:
        period = {"relative_months": RECENT_MONTHS}

    # Mêmes règles que le parseur : plusieurs éléments cités = comparaison,
    # chiffre d'affaires par produit = mix_produit.
    if isinstance(product, list) and "product" not in dimensions:
        dimensions.insert(0, "product")

    if isinstance(channel, list) and "channel" not in dimensions:
        dimensions.insert(0, "channel")

    if metric == "ca_net" and (product or {"product", "format"} & set(dimensions)):
        metric = "mix_produit"

    if product:
        resolve_dimension("product", metric)

    dimensions = [resolve_dimension(d, metric) for d in dict.fromkeys(dimensions)]

    return build_intent(
        question=question,
        metric=metric,
        dimensions=dimensions,
        channel=channel,
        product=product,
        platform=platform,
        comparison=ranking if dimensions else None,
        other_metrics=other_metrics,
        **period,
    )


def llm_parse(
    question: str,
    model_bundle=None,
    generate: Callable[[list[dict]], str] | None = None,
) -> QueryIntent:
    """Interprète une question libre. `generate` permet de remplacer le modèle (tests)."""
    if generate is None:
        if model_bundle is None:
            raise ValueError(OUT_OF_SCOPE_ERROR)

        def generate(messages):
            return generate_with_model(model_bundle, messages)

    raw = generate(build_messages(question))
    return intent_from_llm_output(raw, question)
