from pathlib import Path
import pandas as pd
from classify_comments_hybrid import deterministic_classification

INPUT_FILE = Path("data/processed/social_comments_for_ai.csv")

df = pd.read_csv(INPUT_FILE)

fields = [
    "language",
    "sentiment",
    "theme",
    "product",
    "is_spam",
]

counts = {
    field: 0
    for field in fields
}

distribution = {}

for _, row in df.iterrows():

    text = str(row["comment_text"])

    rules = deterministic_classification(text)

    unresolved = [
        field
        for field in fields
        if rules[field] is None
    ]

    n_unresolved = len(unresolved)

    distribution[n_unresolved] = (
        distribution.get(n_unresolved, 0) + 1
    )

    for field in unresolved:
        counts[field] += 1


total = len(df)

print("\n" + "=" * 70)
print("ANALYSE DU ROUTAGE V3")
print("=" * 70)

print("\nChamps encore à déterminer :")

for field in fields:
    count = counts[field]

    print(
        f"{field:12} : "
        f"{count:4}/{total} "
        f"({count / total * 100:6.2f}%)"
    )


print("\n" + "-" * 70)

print("Nombre de champs inconnus par commentaire :")

for n in sorted(distribution):

    count = distribution[n]

    print(
        f"{n} champ(s) : "
        f"{count:4} commentaires "
        f"({count / total * 100:6.2f}%)"
    )


print("\n" + "-" * 70)

weighted = sum(
    n * count
    for n, count in distribution.items()
)

print(
    f"Total de champs à déterminer : "
    f"{weighted}"
)

print(
    f"Moyenne de champs à déterminer par commentaire : "
    f"{weighted / total:.2f}"
)