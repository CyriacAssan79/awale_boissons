from __future__ import annotations


CHANNEL_ALIASES = {
    "meta": "Meta",
    "facebook": "Meta",
    "instagram": "Meta",
    "tiktok": "TikTok",
    "google": "Google",
    "google ads": "Google",
    "radio": "Radio",
    "influenceurs": "Influenceurs",
    "influenceur": "Influenceurs",
    "activation terrain": "Activation terrain",
}


ALLOWED_CHANNELS = tuple(
    sorted(set(CHANNEL_ALIASES.values()))
)


def resolve_channel(term: str) -> str:
    """Résout un alias vers un canal marketing autorisé."""

    normalized = term.strip().lower()

    if normalized not in CHANNEL_ALIASES:
        raise ValueError(
            f"Canal inconnu : '{term}'. "
            f"Canaux disponibles : {', '.join(ALLOWED_CHANNELS)}"
        )

    return CHANNEL_ALIASES[normalized]


PRODUCT_ALIASES = {
    "bissap": "bissap",
    "bouye": "bouye",
    "gingembre": "gingembre",
    "ginger": "gingembre",
}


ALLOWED_PRODUCTS = tuple(
    sorted(set(PRODUCT_ALIASES.values()))
)


def resolve_product(term: str) -> str:
    """Résout un alias vers un produit autorisé."""

    normalized = term.strip().lower()

    if normalized not in PRODUCT_ALIASES:
        raise ValueError(
            f"Produit inconnu : '{term}'. "
            f"Produits disponibles : {', '.join(ALLOWED_PRODUCTS)}"
        )

    return PRODUCT_ALIASES[normalized]


# Plateformes des commentaires clients (mart_social_monthly). « Meta »
# désigne Facebook et Instagram ensemble : il est traité par le parseur.
PLATFORM_ALIASES = {
    "facebook": "Facebook",
    "fb": "Facebook",
    "instagram": "Instagram",
    "insta": "Instagram",
    "tiktok": "TikTok",
    "tik tok": "TikTok",
}


ALLOWED_PLATFORMS = tuple(
    sorted(set(PLATFORM_ALIASES.values()))
)


def resolve_platform(term: str) -> str:
    """Résout un alias vers une plateforme de commentaires autorisée."""

    normalized = term.strip().lower()

    if normalized not in PLATFORM_ALIASES:
        raise ValueError(
            f"Plateforme inconnue : '{term}'. "
            f"Plateformes disponibles : {', '.join(ALLOWED_PLATFORMS)}"
        )

    return PLATFORM_ALIASES[normalized]


def is_valid_channel(channel: str) -> bool:
    """Vérifie qu'un canal est autorisé."""

    return channel in ALLOWED_CHANNELS


if __name__ == "__main__":
    print("Canaux autorisés :")
    print(ALLOWED_CHANNELS)

    print("\nTests :")

    tests = [
        "Meta",
        "facebook",
        "TikTok",
        "google ads",
        "Radio",
        "influenceur",
        "inconnu",
    ]

    for test in tests:
        try:
            result = resolve_channel(test)
            print(f"{test!r} -> {result!r}")
        except ValueError as exc:
            print(f"{test!r} -> ERREUR : {exc}")