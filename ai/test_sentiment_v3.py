from classify_comments_hybrid import rule_sentiment


TESTS = [
    # Positifs clairs
    "J'adore cette boisson",
    "C'est délicieux",
    "C'est très bon",
    "J'aime beaucoup le bissap",
    "Le bissap est excellent",

    # Négatifs clairs
    "C'est mauvais",
    "Je n'aime pas",
    "C'est trop cher",
    "La bouteille fuit",
    "Le goût est mauvais",

    # Neutres / sans signal clair
    "Quel est le prix ?",
    "Vous avez du bissap ?",
    "C'est quoi cette boisson ?",

    # Contradictoires
    "Le bissap est bon mais la bouteille fuit",
    "C'est délicieux mais beaucoup trop cher",

    # Très courts
    "Bon",
    "Mauvais",
    "Merci",
    "😍😍😍",

     # Négations
    "Ce n'est pas bon",
    "C'est pas bon",
    "Ce n'est vraiment pas bon",
    "Ce n'est pas délicieux",
    "Ce n'est pas mauvais",
    "Ce n'est pas cher",

    # Négations complexes
    "Ce n'est pas mauvais mais ce n'est pas excellent",
    "Je ne dirais pas que c'est bon",
]


for text in TESTS:
    result = rule_sentiment(text)
    print(f"{result!r:10} | {text}")