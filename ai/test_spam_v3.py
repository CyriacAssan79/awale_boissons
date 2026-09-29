from classify_comments_hybrid import rule_spam


TESTS = [
    # ---------------------------------------------------------
    # Spam évident
    # ---------------------------------------------------------
    "Boostez vos followers",
    "Boostes vos followers",
    "Suis-moi",
    "Suis moi",
    "Je te suis",
    "Prêt d'argent sans garantie, contactez-moi",
    "DM moi pour les followers",
    "DM pour follow",
    "DM moi pour les abonnés",

    # ---------------------------------------------------------
    # Commentaires normaux
    # ---------------------------------------------------------
    "J'adore vos boissons",
    "Je te suis depuis longtemps",
    "Merci pour cette excellente boisson",
    "Vous avez du bissap ?",
    "Quel est le prix du bouye ?",
    "La bouteille est très jolie",

    # ---------------------------------------------------------
    # Cas ambigus
    # ---------------------------------------------------------
    "Je te suis sur TikTok",
    "Suis-moi pour voir la recette",
    "DM moi pour avoir le prix",
    "Contactez-moi pour une commande",
    "Je vous suis depuis hier",
]


for text in TESTS:
    result = rule_spam(text)
    print(f"{result!r:5} | {text}")