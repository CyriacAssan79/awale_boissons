from classify_comments_hybrid import rule_theme


TESTS = [
    # Taste
    "Le bissap est délicieux",
    "C'est très bon",
    "Le goût est excellent",

    # Price
    "Quel est le prix ?",
    "Combien coûte le bissap ?",
    "C'est trop cher",

    # Availability
    "Vous avez du bissap ?",
    "Le produit est-il disponible ?",
    "Il n'y a plus de stock",

    # Delivery
    "Quand allez-vous livrer ma commande ?",
    "Ma commande n'est toujours pas livrée",

    # Packaging
    "La bouteille fuit",
    "L'étiquette est jolie",
    "Le format est trop petit",

    # Health
    "Est-ce qu'il y a beaucoup de sucre ?",
    "Quels sont les ingrédients ?",

    # Promotion
    "J'ai vu votre publicité sur TikTok",
    "Votre pub passe à la radio",

    # Product question
    "C'est quoi ce produit ?",
    "Quelle est la composition ?",

    # Ambigus / plusieurs thèmes
    "Le bissap est bon mais trop cher",
    "La bouteille est jolie mais le prix est trop élevé",
    "Le produit est bon mais il n'est plus disponible",

    # Aucun thème évident
    "Merci beaucoup",
    "😍😍😍",
]


for text in TESTS:
    result = rule_theme(text)
    print(f"{result!r:20} | {text}")