from classify_comments_hybrid import (
    rule_language,
    rule_product,
    rule_sentiment,
    rule_theme,
)


TESTS = [
    # ---------------------------------------------------------
    # Français
    # ---------------------------------------------------------
    "Merci beaucoup pour cette boisson",

    # ---------------------------------------------------------
    # Nouchi
    # ---------------------------------------------------------
    "Wallah c'est trop bon",

    # ---------------------------------------------------------
    # Anglais
    # ---------------------------------------------------------
    "This drink is great",

    # ---------------------------------------------------------
    # Mixed
    # ---------------------------------------------------------
    "How much coûte le bissap ?",

    # ---------------------------------------------------------
    # Produit
    # ---------------------------------------------------------
    "J'adore le bissap",
    "Le gingembre est trop fort",
    "J'aime le bissap et le bouye",

    # ---------------------------------------------------------
    # Sentiment
    # ---------------------------------------------------------
    "C'est délicieux",
    "C'est vraiment mauvais",
    "Ce n'est pas bon",

    # ---------------------------------------------------------
    # Thème
    # ---------------------------------------------------------
    "Combien coûte le bissap ?",
    "Vous avez encore du bouye ?",
    "La bouteille fuit",

    # ---------------------------------------------------------
    # Plusieurs dimensions
    # ---------------------------------------------------------
    "Le bissap est trop bon mais c'est cher",
    "Vous avez du gingembre ? J'adore cette boisson",
    "Le bouye est bon mais la bouteille fuit",

    # ---------------------------------------------------------
    # Commentaires courts
    # ---------------------------------------------------------
    "Bissap",
    "Bouye",
    "Bon",
    "Merci",
    "😍😍😍",
]


for text in TESTS:
    language = rule_language(text)
    product = rule_product(text)
    sentiment = rule_sentiment(text)
    theme = rule_theme(text)

    print("\n" + "=" * 80)
    print(text)
    print(f"language  : {language}")
    print(f"product   : {product}")
    print(f"sentiment : {sentiment}")
    print(f"theme     : {theme}")