"""Ajoute au benchmark humain les commentaires validés du brouillon.

ai/evaluation/labeled_sample_draft.csv contient des commentaires que les règles
ne tranchent pas (ils partent au modèle), avec des labels PROPOSÉS. Un humain
relit chaque ligne, corrige les labels si besoin et passe la colonne
"validated" à "oui". Ce script déplace alors ces lignes vers
labeled_sample.csv ; les lignes non validées restent dans le brouillon.

Usage :
    python ai/evaluation/merge_validated_draft.py            # aperçu, n'écrit rien
    python ai/evaluation/merge_validated_draft.py --apply    # écrit les deux fichiers
"""

import argparse
from pathlib import Path

import pandas as pd


HUMAN_FILE = Path("ai/evaluation/labeled_sample.csv")
DRAFT_FILE = Path("ai/evaluation/labeled_sample_draft.csv")

LABELS = {
    "language_human": {"fr", "nouchi", "en", "mixed", "other"},
    "sentiment_human": {"positive", "negative", "neutral"},
    "theme_human": {
        "taste", "price", "availability", "delivery", "packaging",
        "health", "service", "promotion", "product_question", "other",
    },
    "product_human": {"bissap", "gingembre", "bouye", "multiple", "none", "unknown"},
    "is_spam_human": {"true", "false"},
}


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--apply", action="store_true", help="Écrit les fichiers.")
    args = parser.parse_args()

    human = pd.read_csv(HUMAN_FILE, encoding="utf-8-sig", dtype=str)
    draft = pd.read_csv(DRAFT_FILE, encoding="utf-8-sig", dtype=str)

    validated = draft["validated"].str.strip().str.lower().isin({"oui", "yes", "true"})
    to_merge = draft[validated].drop(columns="validated")
    to_merge["annotation_notes"] = (
        to_merge["annotation_notes"]
        .fillna("")
        .str.replace("PROPOSITION À VALIDER — ", "Validé humainement — ", regex=False)
    )

    if to_merge.empty:
        print("Aucune ligne validée (colonne validated = oui) : rien à ajouter.")
        return

    errors = []
    for column, allowed in LABELS.items():
        values = to_merge[column].str.strip().str.lower()
        for comment_id, value in zip(to_merge["comment_id"], values):
            if value not in allowed:
                errors.append(f"{comment_id} : {column} = {value!r}")

    duplicates = set(to_merge["comment_id"]) & set(human["comment_id"])
    errors += [f"{comment_id} : déjà dans {HUMAN_FILE.name}" for comment_id in sorted(duplicates)]

    if errors:
        print("Lignes refusées, rien n'a été écrit :")
        for error in errors:
            print(f"  - {error}")
        raise SystemExit(1)

    print(f"{len(to_merge)} ligne(s) validée(s) à ajouter à {HUMAN_FILE.name} "
          f"({len(human)} -> {len(human) + len(to_merge)} commentaires).")
    print(f"{(~validated).sum()} ligne(s) restent dans {DRAFT_FILE.name}.")

    if not args.apply:
        print("\nAperçu seulement. Relancer avec --apply pour écrire les fichiers.")
        return

    merged = pd.concat([human, to_merge[human.columns]], ignore_index=True)
    merged.to_csv(HUMAN_FILE, index=False, encoding="utf-8-sig")
    draft[~validated].to_csv(DRAFT_FILE, index=False, encoding="utf-8-sig")
    print("Fichiers écrits. Relancer ensuite :")
    print("  python ai/classify_comments_hybrid.py --bench")
    print("  python ai/evaluation/evaluate_classifier.py --model hybrid")


if __name__ == "__main__":
    main()
