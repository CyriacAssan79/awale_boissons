from classify_comments_hybrid import rule_product


TESTS = [
    "J'adore le bissap",
    "Le BISsap est délicieux",
    "J'aime beaucoup l'hibiscus",
    "Le gingembre est trop fort",
    "Vous avez du bouye ?",
    "J'aime le bissap et le gingembre",
    "Le bouye et le bissap sont bons",
    "J'adore cette boisson",
    "C'est trop bon",
    "Quel est le prix ?",
    "😍😍😍",
    "Bissap",
    "Gingembre",
    "Bouye",
]


for text in TESTS:
    result = rule_product(text)
    print(f"{result!r:10} | {text}")