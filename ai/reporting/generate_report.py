"""
Génération du rapport mensuel IA.

Architecture :
    DuckDB marts
        ↓
    query_marts.py
        ↓
    brief déterministe
        ↓
    build_deterministic_report.py
        ↓
    sections factuelles 2 → 8
        +
    LLM
        ↓
    synthèse + conclusion uniquement
        ↓
    rapport final

Le LLM :
- ne calcule aucun nombre ;
- ne reçoit pas les données numériques détaillées ;
- ne produit aucun chiffre ;
- ne formule aucune causalité ;
- ne recommande aucune allocation budgétaire.
"""

from __future__ import annotations

import argparse
import re
import time
from pathlib import Path
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from ai.reporting.build_deterministic_report import (
    build_deterministic_sections,
)
from ai.reporting.query_marts import build_monthly_brief


# ---------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------

DEFAULT_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"

PROMPT_PATH = (
    Path(__file__).resolve().parent
    / "prompts"
    / "monthly_report_v1.txt"
)


# ---------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------
def load_reporting_prompt() -> str:
    """Charge les règles métier qui encadrent la génération narrative."""

    return PROMPT_PATH.read_text(encoding="utf-8")


def build_synthesis_prompt(context: dict[str, str]) -> str:
    return f"""
Tu rédiges une courte synthèse professionnelle.

Faits disponibles :
- {context["revenue_statement"]}
- {context["data_quality_statement"]}
- {context["principal_marketing_fact"]}
- {context["principal_customer_signal"]}

Règles :
- utilise uniquement ces faits ;
- reformule-les simplement ;
- aucune invention ;
- aucun chiffre ;
- aucun pourcentage ;
- aucun montant ;
- aucune date ;
- aucune cause ;
- aucune explication économique ;
- aucune recommandation ;
- ne parle pas de demande ;
- ne parle pas d'évolution historique ;
- ne parle pas d'une autre période ;
- écris seulement 3 phrases ;
- aucun titre.

Retourne uniquement le paragraphe.
""".strip()

def build_conclusion_prompt(context: dict[str, str]) -> str:
    return f"""
Tu rédiges une courte conclusion professionnelle.

Faits disponibles :
- {context["revenue_statement"]}
- {context["principal_customer_signal"]}
- {context["top_product_statement"]}
- {context["whatsapp_issue"]}

Règles :
- utilise uniquement ces faits ;
- reformule-les simplement ;
- aucune invention ;
- aucun chiffre ;
- aucun pourcentage ;
- aucun montant ;
- aucune date ;
- aucune cause ;
- aucune explication économique ;
- aucune recommandation ;
- ne parle pas de demande ;
- ne parle pas d'évolution historique ;
- écris seulement 2 phrases ;
- aucun titre.

Retourne uniquement le paragraphe.
""".strip()


def build_narrative_context(brief: dict[str, Any]) -> dict[str, str]:
    """
    Construit un contexte narratif qualitatif.

    IMPORTANT :
    Aucun chiffre, pourcentage, montant ou date numérique
    n'est transmis au LLM.

    Les données quantitatives restent exclusivement
    dans les sections déterministes.
    """

    sales = brief.get("sales", {})
    marketing = brief.get("marketing", {})
    customer_voice = brief.get("customer_voice", {})
    products = brief.get("products", {})
    whatsapp = brief.get("whatsapp", {}) or {}

    top_product = products.get("top_product") or {}

    marketing_fact = (
        "Aucune dépense marketing exploitable n'est disponible."
        if not marketing.get("channels")
        else "Un canal représente la plus grande part des dépenses marketing observées."
    )

    product_fact = (
        "Un produit représente la plus grande part du chiffre d'affaires."
        if top_product
        else "Aucun produit dominant n'est déterminable dans les données disponibles."
    )

    whatsapp_issue = (
        "Certaines commandes WhatsApp livrées présentent des montants non exploitables."
        if whatsapp.get("delivered_amount_missing_orders", 0) > 0
        else "Aucun problème de montant WhatsApp livré n'est signalé dans les données disponibles."
    )

    return {
        "period": brief["period"]["current_period_label"],

        "revenue_statement": (
            "Le chiffre d'affaires est en baisse "
            "par rapport à la période précédente."
            if sales.get("revenue_direction") == "baisse"
            else
            "Le chiffre d'affaires est en hausse "
            "par rapport à la période précédente."
            if sales.get("revenue_direction") == "hausse"
            else
            "La direction du chiffre d'affaires n'est pas déterminable "
            "dans les données disponibles."
        ),

        "data_quality_statement": (
            "La couverture temporelle des ventes est complète."
            if sales.get("missing_sales_days") == 0
            else
            "La couverture temporelle des ventes présente "
            "des journées non observées."
            if sales.get("missing_sales_days") is not None
            else
            "La couverture temporelle des ventes n'est pas déterminable."
        ),

        "principal_marketing_fact": marketing_fact,

        "principal_customer_signal": (
            customer_voice.get("principal_signal_client")
            or "Aucun signal client déterminé."
        ),

        "top_product_statement": product_fact,

        "whatsapp_issue": whatsapp_issue,
    }

# ---------------------------------------------------------------------
# Modèle
# ---------------------------------------------------------------------

def resolve_local_model_source(model_name: str) -> str:
    """Utilise le cache Windows partagé lorsqu'il est visible depuis WSL."""

    model_path = Path(model_name)
    if model_path.exists():
        return str(model_path)

    cwd_parts = Path.cwd().parts
    if "Users" not in cwd_parts:
        return model_name

    user_index = cwd_parts.index("Users") + 1
    if user_index >= len(cwd_parts):
        return model_name

    windows_user = cwd_parts[user_index]
    cache_root = (
        Path("/mnt/c/Users")
        / windows_user
        / ".cache"
        / "huggingface"
        / "hub"
        / f"models--{model_name.replace('/', '--')}"
        / "snapshots"
    )

    snapshots = sorted(
        path for path in cache_root.glob("*")
        if path.is_dir() and (path / "tokenizer.json").exists()
    )

    if snapshots:
        return str(snapshots[-1])

    return model_name


def load_model(model_name: str):
    """
    Charge le modèle local Transformers.
    """

    started_at = time.perf_counter()
    print(f"[INFO] Chargement du modèle : {model_name}", flush=True)

    model_source = resolve_local_model_source(model_name)
    if model_source != model_name:
        print(
            f"[INFO] Snapshot local utilisé : {model_source}",
            flush=True,
        )

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    print("[INFO] Chargement du tokenizer...", flush=True)
    tokenizer = AutoTokenizer.from_pretrained(
        model_source,
        local_files_only=model_source != model_name,
    )

    print(
        f"[INFO] Chargement des poids ({device}, {dtype})...",
        flush=True,
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_source,
        dtype=dtype,
        low_cpu_mem_usage=True,
    )

    model.to(device)
    model.eval()

    elapsed = time.perf_counter() - started_at
    print(f"[INFO] Device : {device}", flush=True)
    print(f"[INFO] dtype : {dtype}", flush=True)
    print(
        f"[INFO] Modèle chargé en {elapsed:.1f} seconde(s).",
        flush=True,
    )

    return tokenizer, model, device


# ---------------------------------------------------------------------
# Génération
# ---------------------------------------------------------------------

def generate_narrative(
    model,
    tokenizer,
    prompt: str,
    device: str,
    max_new_tokens: int = 180,
) -> str:
    """
    Génère un court texte narratif à partir d'un prompt.

    Le LLM ne doit produire :
    - aucun chiffre ;
    - aucun pourcentage ;
    - aucune donnée numérique ;
    - aucune attribution causale ;
    - aucun titre Markdown.

    Le texte produit sera ensuite validé par Python.
    """

    messages = [
        {
            "role": "system",
            "content": (
                "Tu es un assistant de reporting commercial.\n"
                "Tu reformules uniquement les faits fournis dans le contexte.\n"
                "Tu ne dois jamais calculer, inventer ou ajouter une information.\n\n"
                f"Règles de reporting à respecter :\n{load_reporting_prompt()}\n\n"
                "Pour cette étape de synthèse uniquement, retourne seulement "
                "les faits qualitatifs fournis dans le message utilisateur : "
                "aucun chiffre, pourcentage, montant, date, causalité, "
                "recommandation ou information nouvelle."
            ),
        },
        {
            "role": "user",
            "content": prompt,
        },
    ]

    # On demande d'abord le texte du prompt au tokenizer.
    # Cette méthode est plus robuste avec les versions récentes
    # de Transformers que de transmettre directement le BatchEncoding
    # retourné par apply_chat_template().
    chat_text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    inputs = tokenizer(
        chat_text,
        return_tensors="pt",
    )

    inputs = {
        key: value.to(device)
        for key, value in inputs.items()
        if hasattr(value, "to")
    }

    input_length = inputs["input_ids"].shape[-1]

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            pad_token_id=tokenizer.eos_token_id,
        )

    generated_tokens = outputs[0][input_length:]

    text = tokenizer.decode(
        generated_tokens,
        skip_special_tokens=True,
    )

    return text.strip()


# ---------------------------------------------------------------------
# Validation minimale de la sortie LLM
# ---------------------------------------------------------------------

def validate_narrative(text: str) -> tuple[bool, list[str]]:
    """
    Vérifie que le texte produit par le LLM respecte les contraintes.

    Cette validation sera renforcée dans validate_report.py.
    """

    errors: list[str] = []

    if "[SYNTHESIS]" not in text:
        errors.append("Bloc [SYNTHESIS] absent.")

    if "[CONCLUSION]" not in text:
        errors.append("Bloc [CONCLUSION] absent.")

    # Détection de chiffres arabes.
    if re.search(r"\d", text):
        errors.append(
            "Le LLM a produit au moins un chiffre."
        )

    # Détection de pourcentages écrits sans chiffres.
    if "%" in text:
        errors.append(
            "Le LLM a produit un symbole de pourcentage."
        )

    # Détection de certains termes de causalité.
    causal_patterns = [
        r"\bgrâce à\b",
        r"\bà cause de\b",
        r"\bcausé par\b",
        r"\bprovoqué par\b",
        r"\bentraîne\b",
        r"\bentraîné par\b",
        r"\bpermet de conclure que\b",
    ]

    for pattern in causal_patterns:
        if re.search(pattern, text, flags=re.IGNORECASE):
            errors.append(
                f"Formulation causale détectée : {pattern}"
            )

    # Le modèle ne doit pas réintroduire la recommandation 15M.
    if re.search(
        r"15\s*M|15\s*millions|15\s*000\s*000",
        text,
        flags=re.IGNORECASE,
    ):
        errors.append(
            "Mention interdite de l'enveloppe de 15 M FCFA."
        )

    return len(errors) == 0, errors


def build_safe_narrative(context: dict[str, str]) -> str:
    """Retourne un texte de secours sans données générées par le modèle."""

    return (
        "[SYNTHESIS]\n"
        f"{context['revenue_statement']} "
        f"{context['data_quality_statement']} "
        f"{context['principal_customer_signal']}\n\n"
        "[CONCLUSION]\n"
        f"{context['top_product_statement']} "
        f"{context['whatsapp_issue']}"
    )


# ---------------------------------------------------------------------
# Extraction des deux blocs
# ---------------------------------------------------------------------

def extract_block(text: str, name: str) -> str:
    """
    Extrait un bloc [SYNTHESIS] ou [CONCLUSION].
    """

    if name == "SYNTHESIS":
        pattern = r"\[SYNTHESIS\](.*?)(?=\[CONCLUSION\]|$)"

    elif name == "CONCLUSION":
        pattern = r"\[CONCLUSION\](.*)$"

    else:
        raise ValueError(f"Bloc inconnu : {name}")

    match = re.search(
        pattern,
        text,
        flags=re.DOTALL | re.IGNORECASE,
    )

    if not match:
        return ""

    return match.group(1).strip()


# ---------------------------------------------------------------------
# Assemblage final
# ---------------------------------------------------------------------

def assemble_report(
    brief: dict[str, Any],
    narrative: str,
) -> str:
    """
    Assemble le rapport final.

    Les sections factuelles viennent exclusivement de Python.
    """

    period = brief["period"]

    sections = build_deterministic_sections(brief)

    synthesis = extract_block(
        narrative,
        "SYNTHESIS",
    )

    conclusion = extract_block(
        narrative,
        "CONCLUSION",
    )

    if not synthesis:
        synthesis = (
            "La synthèse narrative n'a pas pu être générée. "
            "Les sections factuelles restent disponibles."
        )

    if not conclusion:
        conclusion = (
            "La conclusion narrative n'a pas pu être générée. "
            "Les éléments factuels du rapport restent disponibles."
        )

    return f"""# Rapport mensuel — {period["current_period_label"].capitalize()}

## 1. Synthèse

{synthesis}

{sections["sales"]}

{sections["marketing"]}

{sections["customer_voice"]}

{sections["products"]}

{sections["whatsapp"]}

{sections["attention"]}

{sections["positive"]}

## 9. Conclusion

{conclusion}
"""


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Génération du rapport mensuel IA."
    )

    parser.add_argument(
        "--year",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--month",
        type=int,
        required=True,
    )

    parser.add_argument(
        "--model",
        default=DEFAULT_MODEL,
    )

    parser.add_argument(
        "--db-path",
        default="data/awale.duckdb",
    )

    parser.add_argument(
        "--save",
        action="store_true",
    )

    args = parser.parse_args()

    print(
        f"[INFO] Construction du brief "
        f"{args.month:02d}/{args.year}"
    )

    brief = build_monthly_brief(
        year=args.year,
        month=args.month,
        db_path=args.db_path,
    )

    print("[INFO] Brief construit.")

    context = build_narrative_context(brief)

    tokenizer, model, device = load_model(
        args.model,
    )

    print("[INFO] Génération de la synthèse...")

    synthesis_prompt = build_synthesis_prompt(context)

    synthesis = generate_narrative(
        prompt=synthesis_prompt,
        tokenizer=tokenizer,
        model=model,
        device=device,
        max_new_tokens=120,
    )

    print("[INFO] Génération de la conclusion...")

    conclusion_prompt = build_conclusion_prompt(context)

    conclusion = generate_narrative(
        prompt=conclusion_prompt,
        tokenizer=tokenizer,
        model=model,
        device=device,
        max_new_tokens=120,
    )

    narrative = (
        "[SYNTHESIS]\n"
        f"{synthesis}\n\n"
        "[CONCLUSION]\n"
        f"{conclusion}"
    )

    print("[INFO] Validation de la sortie LLM...")

    valid, errors = validate_narrative(
        narrative,
    )

    if not valid:
        print("[WARNING] Sortie LLM non conforme :")

        for error in errors:
            print(f"  - {error}")

        print(
            "[WARNING] Le rapport sera quand même assemblé "
            "pour faciliter le diagnostic."
        )
        narrative = build_safe_narrative(context)
        print("[INFO] Utilisation d'une synthèse de secours déterministe.")
    else:
        print("[INFO] Sortie LLM conforme.")
    report = assemble_report(
        brief=brief,
        narrative=narrative,
    )

    print()
    print(report)

    if args.save:
        output_dir = Path("outputs/reports")
        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_file = (
            output_dir
            / f"rapport_{args.year}_{args.month:02d}.md"
        )

        output_file.write_text(
            report,
            encoding="utf-8",
        )

        print(
            f"[INFO] Rapport sauvegardé : "
            f"{output_file}"
        )


if __name__ == "__main__":
    main()
