from pathlib import Path

import pandas as pd
from sklearn.metrics import accuracy_score, classification_report


HUMAN_FILE = Path("ai/evaluation/labeled_sample.csv")
MODEL_FILE = Path("ai/evaluation/model_predictions_hybrid.csv")
OUTPUT_FILE = Path("ai/evaluation/classification_errors.csv")


def normalize_bool(value):
    if pd.isna(value):
        return None

    if isinstance(value, bool):
        return value

    value = str(value).strip().lower()

    if value in {"true", "1", "yes"}:
        return True

    if value in {"false", "0", "no"}:
        return False

    return None


def normalize_text(value):
    if pd.isna(value):
        return None

    return str(value).strip().lower()


def main():

    human = pd.read_csv(HUMAN_FILE)
    model = pd.read_csv(MODEL_FILE)

    # ------------------------------------------------------------
    # Vérification des colonnes
    # ------------------------------------------------------------

    print("Colonnes HUMAN :")
    print(human.columns.tolist())

    print("\nColonnes MODEL :")
    print(model.columns.tolist())

    required_human = [
        "comment_id",
        "comment_text",
        "language_human",
        "sentiment_human",
        "theme_human",
        "product_human",
        "is_spam_human",
    ]

    required_model = [
        "comment_id",
        "comment_text",
        "language_model",
        "sentiment_model",
        "theme_model",
        "product_model",
        "is_spam_model",
    ]

    missing_human = [
        col for col in required_human
        if col not in human.columns
    ]

    missing_model = [
        col for col in required_model
        if col not in model.columns
    ]

    if missing_human:
        raise ValueError(
            f"Colonnes manquantes dans labeled_sample.csv : "
            f"{missing_human}"
        )

    if missing_model:
        raise ValueError(
            f"Colonnes manquantes dans model_predictions_local.csv : "
            f"{missing_model}"
        )

    # ------------------------------------------------------------
    # Sélection des colonnes utiles
    # ------------------------------------------------------------

    human = human[
        [
            "comment_id",
            "comment_text",
            "language_human",
            "sentiment_human",
            "theme_human",
            "product_human",
            "is_spam_human",
        ]
    ].copy()

    model = model[
        [
            "comment_id",
            "comment_text",
            "language_model",
            "sentiment_model",
            "theme_model",
            "product_model",
            "is_spam_model",
        ]
    ].copy()

    # ------------------------------------------------------------
    # Normalisation
    # ------------------------------------------------------------

    human_text_columns = [
        "language_human",
        "sentiment_human",
        "theme_human",
        "product_human",
    ]

    model_text_columns = [
        "language_model",
        "sentiment_model",
        "theme_model",
        "product_model",
    ]

    for column in human_text_columns:
        human[column] = human[column].apply(normalize_text)

    for column in model_text_columns:
        model[column] = model[column].apply(normalize_text)

    human["is_spam_human"] = (
        human["is_spam_human"]
        .apply(normalize_bool)
    )

    model["is_spam_model"] = (
        model["is_spam_model"]
        .apply(normalize_bool)
    )

    # ------------------------------------------------------------
    # Fusion annotations humaines + prédictions modèle
    # ------------------------------------------------------------

    merged = human.merge(
        model,
        on=["comment_id", "comment_text"],
        how="inner",
        validate="one_to_one",
    )

    print("\n" + "=" * 80)
    print("CLASSIFIER EVALUATION")
    print("=" * 80)

    print(f"Commentaires humains : {len(human)}")
    print(f"Commentaires modèle  : {len(model)}")
    print(f"Commentaires évalués : {len(merged)}")

    if len(merged) != len(human):
        print(
            f"⚠️ ATTENTION : "
            f"{len(human) - len(merged)} commentaire(s) "
            f"humains n'ont pas été retrouvés."
        )

    # ------------------------------------------------------------
    # Variables à évaluer
    # ------------------------------------------------------------

    fields = [
        ("language", "language_human", "language_model"),
        ("sentiment", "sentiment_human", "sentiment_model"),
        ("theme", "theme_human", "theme_model"),
        ("product", "product_human", "product_model"),
        ("is_spam", "is_spam_human", "is_spam_model"),
    ]

    # ------------------------------------------------------------
    # Métriques par variable
    # ------------------------------------------------------------

    print("\n" + "=" * 80)
    print("MÉTRIQUES PAR VARIABLE")
    print("=" * 80)

    results = []

    for field_name, human_col, model_col in fields:

        y_true = merged[human_col]
        y_pred = merged[model_col]

        valid_mask = (
            y_true.notna()
            & y_pred.notna()
        )

        y_true_valid = y_true[valid_mask]
        y_pred_valid = y_pred[valid_mask]

        accuracy = accuracy_score(
            y_true_valid,
            y_pred_valid,
        )

        print("\n" + "-" * 80)
        print(field_name)
        print("-" * 80)

        print(
            f"Échantillons évalués : "
            f"{len(y_true_valid)}"
        )

        print(
            f"Accuracy : "
            f"{accuracy:.4f} "
            f"({accuracy * 100:.2f} %)"
        )

        print(
            classification_report(
                y_true_valid,
                y_pred_valid,
                zero_division=0,
            )
        )

        results.append(
            {
                "field": field_name,
                "accuracy": accuracy,
                "n": len(y_true_valid),
            }
        )

    # ------------------------------------------------------------
    # Accord par dimension
    # ------------------------------------------------------------

    merged["language_match"] = (
        merged["language_human"]
        == merged["language_model"]
    )

    merged["sentiment_match"] = (
        merged["sentiment_human"]
        == merged["sentiment_model"]
    )

    merged["theme_match"] = (
        merged["theme_human"]
        == merged["theme_model"]
    )

    merged["product_match"] = (
        merged["product_human"]
        == merged["product_model"]
    )

    merged["is_spam_match"] = (
        merged["is_spam_human"]
        == merged["is_spam_model"]
    )

    # ------------------------------------------------------------
    # Accord exact sur les 5 dimensions
    # ------------------------------------------------------------

    merged["exact_match"] = (
        merged["language_match"]
        & merged["sentiment_match"]
        & merged["theme_match"]
        & merged["product_match"]
        & merged["is_spam_match"]
    )

    exact_agreement = merged["exact_match"].mean()

    print("\n" + "=" * 80)
    print("ACCORD EXACT — 5 DIMENSIONS")
    print("=" * 80)

    print(
        f"{exact_agreement:.4f} "
        f"({exact_agreement * 100:.2f} %)"
    )

    # ------------------------------------------------------------
    # Erreurs par dimension
    # ------------------------------------------------------------

    print("\n" + "=" * 80)
    print("ERREURS PAR DIMENSION")
    print("=" * 80)

    match_columns = [
        ("language", "language_match"),
        ("sentiment", "sentiment_match"),
        ("theme", "theme_match"),
        ("product", "product_match"),
        ("is_spam", "is_spam_match"),
    ]

    for field, match_column in match_columns:

        errors_count = (
            ~merged[match_column]
        ).sum()

        error_rate = (
            errors_count / len(merged)
            if len(merged) > 0
            else 0
        )

        print(
            f"{field:12s} : "
            f"{errors_count:3d} erreurs "
            f"({error_rate * 100:.2f} %)"
        )

    # ------------------------------------------------------------
    # Export des erreurs
    # ------------------------------------------------------------

    error_mask = ~merged["exact_match"]

    errors = merged.loc[
        error_mask,
        [
            "comment_id",
            "comment_text",

            "language_human",
            "language_model",

            "sentiment_human",
            "sentiment_model",

            "theme_human",
            "theme_model",

            "product_human",
            "product_model",

            "is_spam_human",
            "is_spam_model",

            "language_match",
            "sentiment_match",
            "theme_match",
            "product_match",
            "is_spam_match",
        ],
    ].copy()

    errors.to_csv(
        OUTPUT_FILE,
        index=False,
    )

    print("\n" + "=" * 80)
    print("ERREURS")
    print("=" * 80)

    print(
        f"Commentaires avec au moins une erreur : "
        f"{len(errors)}"
    )

    print(f"Fichier : {OUTPUT_FILE}")

    # ------------------------------------------------------------
    # Résumé final
    # ------------------------------------------------------------

    print("\n" + "=" * 80)
    print("RÉSUMÉ FINAL")
    print("=" * 80)

    for result in results:

        print(
            f"{result['field']:12s} : "
            f"{result['accuracy'] * 100:6.2f} % "
            f"(n={result['n']})"
        )

    print(
        f"{'exact_match':12s} : "
        f"{exact_agreement * 100:6.2f} %"
    )


if __name__ == "__main__":
    main()