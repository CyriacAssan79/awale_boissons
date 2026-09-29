from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
from pathlib import Path

import pandas as pd
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer


MODEL_NAME = "Qwen/Qwen2.5-0.5B-Instruct"

INPUT_FILE = Path("data/processed/social_comments_for_ai.csv")
OUTPUT_FILE = Path(
    "ai/evaluation/social_comments_predictions_v2_full.csv"
)
# Benchmark humain (--test / --bench) et prédictions lues par
# ai/evaluation/evaluate_classifier.py --model hybrid.
LABELED_FILE = Path("ai/evaluation/labeled_sample.csv")
BENCH_OUTPUT_FILE = Path("ai/evaluation/model_predictions_hybrid.csv")

BATCH_SIZE = 4
LANGUAGES = {"fr", "nouchi", "en", "mixed", "other"}

SENTIMENTS = {"positive", "negative", "neutral"}

THEMES = {
    "taste",
    "price",
    "availability",
    "delivery",
    "packaging",
    "health",
    "service",
    "promotion",
    "product_question",
    "other",
}

PRODUCTS = {
    "bissap",
    "gingembre",
    "bouye",
    "multiple",
    "none",
    "unknown",
}


# Le prompt vit dans un fichier versionné (ai/prompts/), pas dans le code : on
# le relit, on le compare et on le fait évoluer sans toucher au script. Toute
# modification du prompt doit passer par un nouveau fichier (v5, ...) et par un
# nouveau passage du benchmark humain (voir docs/ai_documentation.ipynb).
PROMPT_FILE = (
    Path(__file__).resolve().parent / "prompts" / "comment_classifier_v4_hybrid.txt"
)
PROMPT_TEXT = PROMPT_FILE.read_text(encoding="utf-8")
PROMPT_VERSION = PROMPT_FILE.stem
PROMPT_SHA256 = hashlib.sha256(PROMPT_TEXT.encode("utf-8")).hexdigest()[:12]

# Le fichier contient les consignes, puis après "=== EXEMPLES ===" des blocs
# "commentaire / JSON attendu" séparés par une ligne vide. Les exemples sont
# envoyés comme de vrais tours de conversation (few-shot). Aucun exemple ne
# doit venir de ai/evaluation/labeled_sample.csv, sinon le benchmark est biaisé.
_EXAMPLES_MARKER = "=== EXEMPLES ==="
SYSTEM_PROMPT, _examples_text = (
    part.strip() for part in PROMPT_TEXT.split(_EXAMPLES_MARKER)
)
FEW_SHOT_EXAMPLES = [
    tuple(block.strip().split("\n", 1))
    for block in re.split(r"\n\s*\n", _examples_text)
    if block.strip()
]

# À incrémenter à chaque changement des règles déterministes ou de la fusion.
RULES_VERSION = "v4.2"

# Enregistrée sur chaque ligne de OUTPUT_FILE : une ligne produite par une
# autre version (règles, prompt ou modèle) est reclassée au run suivant.
CLASSIFIER_VERSION = (
    f"rules-{RULES_VERSION}|{PROMPT_VERSION}@{PROMPT_SHA256}|{MODEL_NAME}"
)

# Sauvegarde intermédiaire : toutes les N batches (4 commentaires par batch,
# soit ~2 minutes de calcul pour 5 batches). Un plantage ou un Ctrl+C ne fait
# perdre que le travail depuis la dernière sauvegarde, jamais tout le run.
CHECKPOINT_EVERY_BATCHES = 5


# ---------------------------------------------------------------------
# Règles déterministes
# ---------------------------------------------------------------------

NOUCHI_TERMS = {
    "dèh",
    "deh",
    "wallah",
    "drap",
    "enjaillant",
    "enjaillé",
    "paa",
    "wê",
    "tchê",
    "cé",
    "gbê",
    "gbé",
    "kpakpato",
    "môgô",
}


SPAM_PATTERNS = [
    # ---------------------------------------------------------
    # Follow-for-follow / manipulation explicite
    # ---------------------------------------------------------
    r"\bboost(?:e|es|ez)\s+vos\s+followers\b",
    r"\bfollow\s*back\b",
    r"\bf4f\b",
    r"\bfollow\s+for\s+follow\b",
    r"\b(?:like|follow)\s+for\s+(?:like|follow)\b",
    r"\bsuis[- ]moi\b.*\bje te suis\b",
    r"\babonne[- ]toi\b",

    # ---------------------------------------------------------
    # Prêts / arnaques financières
    # ---------------------------------------------------------
    r"\bpr[êe]t\s+d[' ]argent\b.*\bsans\s+garantie\b",
    r"\bsans\s+garantie\b.*\b(?:contact|whatsapp|appel|dm)\b",
    r"\bformation\b.*\b(?:trading|crypto|forex)\b",
    r"\bperte\s+de\s+poids\b",

    # ---------------------------------------------------------
    # DM explicitement orienté vers followers / promotion
    # ---------------------------------------------------------
    r"\bdm\b.*\b(?:follow|followers|abonn[ée]s)\b",

    # ---------------------------------------------------------
    # Vente / promotion hors contexte, liens et numéros
    # ---------------------------------------------------------
    r"\b(?:gagnez|gagner)\b.*\b(?:argent|followers|abonn[ée]s)\b",
    r"\b(?:gagnez|gagner)\s+\d",
    r"\bcliquez\s+ici\b",
    r"\bbit\.ly\b",
    r"\bvends\b",
    r"\b0\d(?:\s?\d{2}){4}\b",
]


POSITIVE_PATTERNS = [
    # Appréciation explicite
    r"\bj'adore\b",
    r"\bj aime\b",
    r"\bj'aime\b",
    r"\bj'apprécie\b",
    r"\bj apprécie\b",
    r"\badore(?:nt|z)?\b",
    r"\bne regrette pas\b",
    r"\bbravo\b",
    r"\bfélicitations\b",

    # Qualificatifs positifs
    r"\bbon\b",
    r"\bbonne\b",
    r"\bexcellent\b",
    r"\bexcellente\b",
    r"\bdelicieux\b",
    r"\bdelicieuse\b",
    r"\bdélicieux\b",
    r"\bdélicieuse\b",
    r"\bsavoureux\b",
    r"\bsavoureuse\b",
    r"\bsuper\b",
    r"\bparfait\b",
    r"\bparfaite\b",
    r"\btop\b",
    r"\bmeilleure?s?\b",
    r"\bnickel\b",
    r"\bjolie?s?\b",
    r"\bbelle\b",
    r"\bdr[ôo]le\b",
    r"\bdoux\b",
    r"\brapide\b",
    r"\bbien\s+(?:fait|plac[ée]e?|organis[ée]e?)\b",
    r"\bc(?:'est|é)?\s+(?:propre|frais)\b",

    # Nouchi : "enjaillant" = qui fait plaisir, "(y a) pas drap" = pas de souci
    r"\benjaill\w*",
    r"\b(?:no|pas)\s+drap\b",
    r"\bgb[êé]\b",           # "c'est gbê ça" = approbation

    # Anglais
    r"\bgreat\b",
    r"\blove\b",
    r"\bamazing\b",

    # Expressions positives
    r"\btres bon\b",
    r"\btrès bon\b",
    r"\btres bonne\b",
    r"\btrès bonne\b",
    r"\btrop bon\b",
    r"\btrop bonne\b",
    r"\btrès délicieux\b",
]


NEGATIVE_PATTERNS = [
    # Rejet explicite
    r"\bje n'aime pas\b",
    r"\bje n aime pas\b",
    r"\bje déteste\b",
    r"\bje deteste\b",
    r"\barr[êe]tez\b",

    # Qualificatifs négatifs
    r"\bmauvais\b",
    r"\bmauvaise\b",
    r"\bcher\b",
    r"\bchere\b",
    r"\bchère\b",
    r"\bcheres\b",
    r"\bchères\b",
    r"\bdegoutant\b",
    r"\bdégoutant\b",
    r"\bdegoutante\b",
    r"\bdégoutante\b",
    r"\blente?\b",
    r"\bdifficile\b",
    r"\br[ée]p[ée]titi\w*",
    r"\bc(?:'est|é)\s+chaud\b",

    # Prix à la hausse / demande de baisse
    r"\bbaisser\b",
    r"\bdiminuez\b",
    r"\bencore\s+mont[ée]\b",

    # Problèmes explicites
    r"\bfuit\b",
    r"\bfuite\b",
    r"\bcassé\b",
    r"\bcassee\b",
    r"\bcassée\b",
    r"\bprobleme\b",
    r"\bproblème\b",
    r"\bplainte\b",
    r"\bannul[ée]e?\b",
    r"\bne\s+r[ée]pond\s+pas\b",
    r"\btoujours\s+rien\b",
    r"\bd[ée]coll\w*",

    # Indisponibilité
    r"\bintrouvable\b",
    r"\brupture\b",
    r"\bstock\s+fini\b",
    r"\bplus\s+rien\b",
    r"\bne\s+trouve\s+plus\b",
    r"\bpas\s+au\s+ma(?:qu|k)is\b",
    r"\bplus\s+de\s+(?:bissap|gingembre|bouye)\b",
    r"\bbouti(?:que|ke)s?,?\s+rien\b",
]


# Formules de conversation sans contenu sur Awalé ("bonjour", "+1",
# "je confirme") : aucun avis, aucun thème. Le modèle les classait au hasard
# ("exact !" → product_question).
CONVERSATIONAL_PATTERN = re.compile(
    r"^(?:bonjour|bonsoir|salut|slt|bjr|merci(?: pour l'info)?|je confirme"
    r"|exact|\+1|pareil(?: chez moi)?|mdr|ok|d'accord)\W*$"
)


# Emojis utilisés pour les commentaires composés uniquement d'emojis. Dans un
# commentaire avec du texte, les emojis sont souvent du bruit ajouté ("rupture
# partout 😤 😋") : ils ne sont donc pas utilisés comme signal.
POSITIVE_EMOJIS = {"❤", "😍", "😋", "👍", "👌", "💪", "🔥", "👏", "🥰", "😊", "🙏"}
NEGATIVE_EMOJIS = {"😡", "😤", "👎", "😒", "😭", "🤮", "😠"}


def normalize_text(text: str) -> str:
    return str(text).strip().lower()


def strip_fillers(text: str) -> str:
    """Retire les interjections de début de phrase ("bon", "mais", "eh") et
    la formule "qui est comme moi ?" ajoutée en fin de commentaire.

    "bon vous livrez sur Riviera ?" n'est ni un avis positif ni un commentaire
    sur le goût : sans ce nettoyage, "bon" déclenchait les deux règles. De même,
    le "?" de "bravo, c'est bien fait qui est comme moi ?" faisait passer un
    compliment pour une question.
    """
    t = re.sub(r"^(?:bon|mais|eh|hey)\b[\s,]*", "", normalize_text(text))
    return re.sub(r"\b(?:qui|ki) est comme moi\s*\?*", "", t).strip()


def contains_any(text: str, patterns: list[str]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def rule_language(text: str) -> str | None:
    """
    Détection déterministe prudente de la langue.

    Retourne :
    - "nouchi" si des marqueurs nouchi explicites sont présents ;
    - "mixed" si français et anglais sont clairement présents ;
    - "en" si l'anglais est suffisamment explicite ;
    - "fr" si le français est suffisamment explicite ;
    - None si la règle n'est pas suffisamment certaine.

    Important :
    une absence de détection ne signifie PAS automatiquement "other".
    Dans ce cas, le modèle local pourra intervenir.
    """
    t = normalize_text(text)

    if not t:
        return None

    # -------------------------------------------------------------
    # 1. Nouchi explicite
    # -------------------------------------------------------------
    has_nouchi = any(
        re.search(rf"\b{re.escape(term)}\b", t)
        for term in NOUCHI_TERMS
    )

    french_patterns = [
    # Articles / déterminants
    r"\ble\b", r"\bla\b", r"\bles\b", r"\bun\b", r"\bune\b", r"\bdes\b",
    r"\bdu\b", r"\bde\b", r"\bau\b", r"\baux\b", r"\bce\b", r"\bcet\b", r"\bcette\b", r"\bces\b",
    r"\bmon\b", r"\bma\b", r"\bmes\b", r"\bton\b", r"\bta\b", r"\btes\b", r"\bson\b", r"\bsa\b", r"\bses\b",
    r"\bnotre\b", r"\bnos\b",r"\bvotre\b",r"\bvos\b",r"\bleur\b",r"\bleurs\b",

    # Pronoms
    r"\bje\b",r"\btu\b",r"\bil\b",r"\belle\b",r"\bnous\b",r"\bvous\b",r"\bils\b",r"\belles\b",
    r"\bon\b",r"\bme\b",r"\bte\b",r"\bse\b",r"\blui\b",r"\bleur\b",r"\by\b",r"\ben\b",

    # Verbes / auxiliaires
    r"\best\b", r"\bsont\b",r"\bes\b",r"\bsuis\b",r"\bêtre\b",r"\bavoir\b",r"\bai\b", r"\bas\b",
    r"\ba\b", r"\bavons\b",r"\bavez\b",r"\bont\b",r"\bc'est\b",r"\bce sont\b",r"\bfaire\b",r"\bfait\b",

    # Prépositions / conjonctions
    r"\bpour\b",r"\bavec\b",r"\bdans\b",r"\bsur\b",r"\bsous\b",r"\bentre\b",r"\bchez\b",
    r"\bsans\b",r"\bcontre\b",r"\bvers\b",r"\bdepuis\b",r"\bpendant\b",r"\bavant\b",r"\baprès\b",
    r"\bcomme\b",r"\bmais\b",r"\bou\b",r"\bet\b",r"\bdonc\b",r"\bcar\b",r"\bparce que\b",
    r"\bque\b", r"\bqui\b",

    # Adverbes / interrogatifs
    r"\bplus\b",r"\bmoins\b",r"\bbien\b",r"\btrès\b",r"\btrop\b",r"\bassez\b",r"\bbeaucoup\b",r"\btoujours\b",
    r"\bjamais\b",r"\bsouvent\b",r"\bencore\b",r"\bdéjà\b",r"\bmaintenant\b",r"\bici\b",r"\blà\b",r"\bcomment\b",
    r"\bpourquoi\b",r"\bquand\b",r"\bquel\b",r"\bquelle\b",r"\bquels\b",r"\bquelles\b",r"\bquoi\b",

    # Marqueurs conversationnels
    r"\bbonjour\b",r"\bbonsoir\b",r"\bsalut\b",r"\bmerci\b",r"\bs'il vous plaît\b",r"\bs'il te plaît\b",
    r"\bsvp\b",r"\bfélicitations\b",r"\bbravo\b",

    # Vocabulaire français assez discriminant
    r"\bfrançais\b",r"\bfrançaise\b",r"\baujourd'hui\b",r"\bdemain\b",r"\bhier\b",r"\bbeau\b",r"\bbelle\b",
    r"\bbon\b",r"\bbonne\b",r"\bmauvais\b",r"\bmauvaise\b",r"\bchose\b",r"\bpersonne\b",r"\bproblème\b",
    r"\bquestion\b",r"\bréponse\b",r"\bbesoin\b",r"\bbeauté\b",r"\bboisson\b",r"\bgoût\b",r"\bproduit\b",r"\bacheter\b",
    r"\bachète\b",r"\bprix\b",r"\bcombien\b",
]

    french_matches = sum(
        bool(re.search(pattern, t))
        for pattern in french_patterns
    )

    has_french = french_matches >= 1

    # -------------------------------------------------------------
    # 3. Marqueurs anglais
    # -------------------------------------------------------------
    english_patterns = [

    # Uniquement des mots qui n'existent pas en français ni en nouchi :
    # "a" (il y a), "on", "me", "an", "or", "but", "no" (no drap), "hey"
    # (interjection courante) et "can" (la CAN) produisaient de faux "mixed",
    # ensuite imposés au modèle comme résultats définitifs.

    # Articles / déterminants
    r"\bthe\b", r"\bthis\b",r"\bthat\b", r"\bthese\b", r"\bthose\b",
    r"\bmy\b", r"\byour\b", r"\bhis\b", r"\bher\b", r"\bits\b", r"\bour\b", r"\btheir\b",
    r"\bsome\b", r"\bany\b", r"\beach\b", r"\bevery\b", r"\ball\b",

    # Pronoms
    r"\bi\b",r"\byou\b",r"\bhe\b",r"\bshe\b",r"\bit\b",r"\bwe\b",r"\bthey\b",
    r"\bhim\b",r"\bher\b",r"\bus\b",r"\bthem\b",

    # Auxiliaires / verbes fréquents
    r"\bam\b",r"\bis\b",r"\bare\b",r"\bwas\b",r"\bwere\b",r"\bbe\b",r"\bbeen\b",r"\bbeing\b",
    r"\bhave\b",r"\bhas\b",r"\bhad\b",r"\bdo\b",r"\bdoes\b",r"\bdid\b",r"\bcould\b",
    r"\bwill\b",r"\bwould\b",r"\bshall\b",r"\bshould\b",r"\bmay\b",r"\bmight\b",r"\bmust\b",

    # Prépositions / conjonctions
    r"\bwith\b",r"\bfor\b",r"\bfrom\b",r"\bto\b",r"\bin\b",r"\bat\b",r"\bby\b",
    r"\babout\b",r"\binto\b",r"\bover\b",r"\bunder\b",r"\bbetween\b",r"\bwithout\b",r"\band\b",
    r"\bbecause\b",r"\bif\b",r"\bthan\b",r"\bwhile\b",

    # Interrogatifs / adverbes
    r"\bwhat\b",r"\bwhy\b",r"\bwhen\b",r"\bwhere\b",r"\bwho\b",r"\bwhich\b",r"\bhow\b",
    r"\bhow\s+much\b",r"\bhow\s+many\b",r"\bvery\b",r"\bmore\b",r"\bmost\b",r"\bless\b",
    r"\balways\b",r"\bnever\b",r"\balready\b",r"\bstill\b",r"\bnow\b",r"\btoday\b",r"\btomorrow\b",
    r"\byesterday\b",

    # Marqueurs conversationnels
    r"\bplease\b",r"\bthanks\b",r"\bthank\s+you\b",r"\bhello\b",r"\bhi\b",
    r"\bgoodbye\b",r"\bwelcome\b",r"\bsorry\b",r"\bcongratulations\b",

    # Vocabulaire fréquent dans les commentaires
    r"\bgreat\b",r"\bsweet\b",r"\btasty\b",r"\bgood\b",r"\bdelicious\b",r"\bbad\b",
    r"\bbetter\b",r"\bbest\b",r"\bamazing\b",r"\bawesome\b",r"\bnice\b",r"\bbeautiful\b",
    r"\blove\b",r"\blike\b",r"\benjoy\b",r"\bwant\b",r"\bneed\b",r"\bprice\b",r"\bcost\b",
    r"\bdrink\b",r"\bjuice\b",r"\btaste\b",r"\bflavor\b",r"\bproduct\b",r"\bbuy\b",r"\bavailable\b",r"\bsugar\b",
    ]

    english_matches = sum(
        bool(re.search(pattern, t))
        for pattern in english_patterns
    )

    has_english = english_matches >= 1

    # -------------------------------------------------------------
    # 4. Nouchi prioritaire
    # -------------------------------------------------------------
    if has_nouchi:
        return "nouchi"

    # -------------------------------------------------------------
    # 5. Français + anglais
    # -------------------------------------------------------------
    if has_french and has_english:
        return "mixed"

    # -------------------------------------------------------------
    # 6. Anglais suffisamment explicite
    # -------------------------------------------------------------
    if english_matches >= 2:
        return "en"

    # Un seul marqueur anglais très fort peut suffire
    strong_english_patterns = [
        r"\bthank\s+you\b",
        r"\bhow\s+much\b",
        r"\bplease\b",
        r"\bdelicious\b",
        r"\btasty\b",
    ]

    if contains_any(t, strong_english_patterns):
        return "en"

    # -------------------------------------------------------------
    # 7. Français
    # -------------------------------------------------------------
    if has_french:
        return "fr"

    # -------------------------------------------------------------
    # 8. Cas ambigu
    # -------------------------------------------------------------
    # On ne force pas "other".
    # Le modèle local pourra décider.
    return None


def rule_spam(text: str) -> bool | None:
    """
    Détection déterministe du spam.

    Retourne :
    - True : motif de spam explicite ;
    - False : aucun motif de spam ET le commentaire parle d'un thème ou d'un
      produit Awalé identifié par les règles ;
    - None : la règle ne sait pas, le modèle décide.
    """
    t = normalize_text(text)

    if contains_any(t, SPAM_PATTERNS):
        return True

    if rule_theme(t) is not None or rule_product(t) is not None:
        return False

    return None


def rule_product(text: str) -> str | None:
    """
    Détection déterministe du produit uniquement lorsqu'il est
    explicitement mentionné.

    Retourne :
    - "bissap" si bissap/hibiscus est explicitement mentionné ;
    - "gingembre" si gingembre est explicitement mentionné ;
    - "bouye" si bouye est explicitement mentionné ;
    - "multiple" si plusieurs produits sont explicitement mentionnés ;
    - None si aucune mention explicite n'est trouvée.

    Important :
    None signifie "la règle ne sait pas", et non "aucun produit".
    Le modèle pourra donc encore déterminer "none" ou "unknown".
    """
    t = normalize_text(text)

    found = set()

    # -------------------------------------------------------------
    # Bissap
    # -------------------------------------------------------------
    if re.search(r"\b(?:bissap|hibiscus)\b", t):
        found.add("bissap")

    # -------------------------------------------------------------
    # Gingembre
    # -------------------------------------------------------------
    if re.search(r"\bgingembre\b", t):
        found.add("gingembre")

    # -------------------------------------------------------------
    # Bouye
    # -------------------------------------------------------------
    if re.search(r"\bbouye\b", t):
        found.add("bouye")

    # -------------------------------------------------------------
    # Plusieurs produits explicitement cités
    # -------------------------------------------------------------
    if len(found) > 1:
        return "multiple"

    # -------------------------------------------------------------
    # Un seul produit explicitement cité
    # -------------------------------------------------------------
    if len(found) == 1:
        return next(iter(found))

    # -------------------------------------------------------------
    # Aucun produit explicitement cité
    # -------------------------------------------------------------
    return None

THEME_PATTERNS = {
    "delivery": [
        r"\blivr\w*",          # livraison, livrez, livreur, livré
        r"\bcommand\w*",       # commande, commandé, commander
        r"\bship\b",
        r"\bdelivery\b",
    ],
    "availability": [
        r"\bstock\b",
        r"\brupture\b",
        r"\bplus\s+rien\b",
        r"\ben\s+rayon\b",
        r"\bdisponib\w*",
        r"\bavailable\b",
        r"\bintrouvable\b",
        r"\btrouve\b",         # où on trouve, on ne trouve plus
        r"\bsupermarch\w*",
        r"\bbouti(?:que|ke)s?\b",
        r"\bpas\s+au\s+ma(?:qu|k)is\b",
        r"\bplus\s+de\s+(?:bissap|gingembre|bouye)\b",
        r"\bc(?:'est|é)?\s+fini\b",
        r"\bwhere\s+can\s+i\s+buy\b",
        r"\bavez[- ]vous\b",
        r"\bvous avez\b.*\b(?:bissap|gingembre|bouye)\b",
    ],
    "price": [
        r"\bprix\b",
        r"\bch[èe]re?s?\b",
        r"\bco[uû]te?\b",
        r"\bcombien\b",
        r"\bfrancs?\b",
        r"\bfcfa\b",
        r"\bà\s+\d{3,}\b",     # "le 33cl à 500", "à 1500 francs"
        r"\bprice\b",
    ],
    "packaging": [
        r"\bbouteille\b",
        r"\bemballage\b",
        r"\bpackaging\b",
        r"\b[ée]tiquette\b",
        r"\bformat\b",
        r"\bfuit\b",
        r"\bfuite\b",
        r"\bbouchon\b",
        r"\bpacks?\b",
        r"\b\d+\s?(?:cl|l)\b",  # 33cl, 1l, 2l
    ],
    "health": [
        r"\bsucre\b",
        r"\bconservateurs?\b",
        r"\bsant[ée]\b",
        r"\bingr[ée]dients?\b",
        r"\bcalories?\b",
        r"\bdiab[ée]t\w*",
    ],
    "promotion": [
        r"\bpubs?\b",
        r"\bpublicit\w*",
        r"\bradio\b",
        r"\btiktok\b",
        r"\binfluenc\w*",
        r"\bstand\b",
        r"\bpromo(?:tion)?s?\b",
        r"\bcampagne\b",
        r"\bvid[ée]o\b",
        r"\bd[ée]gustation\b",
        r"\bvu\s+chez\s+@",    # "j'ai vu chez @influenceuse"
    ],
    "taste": [
        r"\bgo[uû]t\w*",       # goût, goûté
        r"\bsucr[ée]e?\b",
        r"\bfra[iî]s\b",
        r"\bfra[iî]che\b",
        r"\bd[ée]licieu\w*",
        r"\bsavoureu\w*",
        r"\bbon\b",
        r"\bbonne\b",
        r"\bdoux\b",
        r"\badore(?:nt|z)?\b",
        r"\bmeilleure?\b",
        r"\bqualit[ée]\b",
        r"\bkalit[ée]\b",
        r"\btasty\b",
        r"\bdelicious\b",
    ],
    "product_question": [
        r"\bquel produit\b",
        r"\bquel est ce produit\b",
        r"\bc'est quoi\b",
        r"\bcomposition\b",
        r"\bversion\b",
        r"\bsugar[- ]free\b",
        r"\bnaturel\b",
        r"\bconcentr[ée]\b",
    ],
    "service": [
        r"\bpayer\b",
        r"\bpaiement\b",
        r"\bservice\s+client\b",
    ],
}

# Quand plusieurs thèmes sont détectés, le plus spécifique l'emporte :
# "version sans sucre ?" → product_question (et non health),
# "sucre ajouté ?" → health (et non taste), "dégustation au stand" →
# promotion, "trop cher pour la qualité" → price, "le 33cl à 500 c'est
# correct mais le 1L non" → price, "le livreur ne répond pas" → delivery.
# Les autres combinaisons restent ambiguës et vont au modèle.
THEME_PRIORITY = {
    "product_question": {"health", "taste"},
    "health": {"taste"},
    "promotion": {"taste"},
    "price": {"taste", "packaging"},
    "delivery": {"service", "availability"},
}


def rule_theme(text: str) -> str | None:
    """
    Détection déterministe du thème principal.

    Retourne :
    - un thème si un signal suffisamment clair est détecté ;
    - None si aucun thème ou plusieurs thèmes concurrents sont détectés.
    """
    t = strip_fillers(text)

    matches = {
        theme
        for theme, patterns in THEME_PATTERNS.items()
        if any(re.search(pattern, t) for pattern in patterns)
    }

    # "enjaillant" ne parle du goût que s'il qualifie un produit nommé
    # ("le gingembre est enjaillant"), pas dans "c'est enjaillant, no drap".
    if re.search(r"\benjaill\w*", t) and rule_product(t) is not None:
        matches.add("taste")

    dominated = {
        loser
        for winner in matches
        for loser in THEME_PRIORITY.get(winner, set())
    }
    matches -= dominated

    if len(matches) == 1:
        return next(iter(matches))

    # Aucun thème, ou plusieurs thèmes concurrents :
    # on laisse le modèle déterminer le thème principal.
    return None


def has_negated_sentiment(text: str, patterns: list[str]) -> bool:
    """
    Détecte si un marqueur de sentiment est précédé
    d'une négation française simple.

    Exemples :
    - "pas bon"
    - "pas délicieux"
    - "pas mauvais"

    Retourne True si un pattern de sentiment est
    précédé d'une négation.
    """

    t = normalize_text(text)

    negations = [
        r"\bpas\b",
        r"\bplus\b",
        r"\bjamais\b",
        r"\baucunement\b",
        r"\bpas du tout\b",
    ]

    for sentiment_pattern in patterns:
        for negation in negations:

            pattern = rf"{negation}\s+(?:\w+\s+){{0,3}}?{sentiment_pattern}"

            if re.search(pattern, t):
                return True

    return False


def rule_sentiment(text: str) -> str | None:
    """
    Détection déterministe du sentiment lorsque le signal est clair.

    Gère également les négations simples.

    Retourne :
    - "positive"
    - "negative"
    - None si ambigu ou insuffisant
    """
    t = strip_fillers(text)
    # ---------------------------------------------------------
    # 0. Constructions linguistiques complexes
    # ---------------------------------------------------------

    complex_negation_patterns = [
        r"\bje ne dirais pas\b",
        r"\bje ne pense pas\b",
        r"\bje ne crois pas\b",
        r"\bon ne peut pas dire\b",
        r"\bpas vraiment\b",
        r"\bpas tellement\b",
        r"\bpas particulierement\b",
        r"\bpas particulièrement\b",
    ]

    if any(re.search(pattern, t) for pattern in complex_negation_patterns): return None


    has_positive = any(
        re.search(pattern, t)
        for pattern in POSITIVE_PATTERNS
    )

    has_negative = any(
        re.search(pattern, t)
        for pattern in NEGATIVE_PATTERNS
    )

    # ---------------------------------------------------------
    # 1. Négations explicites
    # ---------------------------------------------------------

    positive_negated = has_negated_sentiment(
        t,
        POSITIVE_PATTERNS
    )

    negative_negated = has_negated_sentiment(
        t,
        NEGATIVE_PATTERNS
    )

    # Un sentiment positif explicitement nié
    # devient négatif.
    if positive_negated and not negative_negated:
        return "negative"

    # Un sentiment négatif explicitement nié
    # devient positif.
    if negative_negated and not positive_negated:
        return "positive"

    # ---------------------------------------------------------
    # 2. Signaux non contradictoires
    # ---------------------------------------------------------

    if has_positive and not has_negative:
        return "positive"

    if has_negative and not has_positive:
        return "negative"

    # ---------------------------------------------------------
    # 3. Question sans aucun marqueur d'avis
    #    ("vous livrez à Bingerville ?", "quels sont les conservateurs ?")
    # ---------------------------------------------------------

    if not has_positive and not has_negative and "?" in t:
        return "neutral"

    # ---------------------------------------------------------
    # 4. Aucun signal ou signaux contradictoires
    # ---------------------------------------------------------

    return None


def emoji_only_classification(text: str) -> dict | None:
    """Commentaire sans aucune lettre ni chiffre (ex. "❤️❤️❤️").

    Tout est déterminable sans modèle : pas de langue, pas de thème, pas de
    produit ; le sentiment vient des emojis eux-mêmes.
    """
    t = str(text).strip()

    if not t or re.search(r"[^\W_]", t):
        return None

    positive = any(emoji in t for emoji in POSITIVE_EMOJIS)
    negative = any(emoji in t for emoji in NEGATIVE_EMOJIS)

    if positive and not negative:
        sentiment = "positive"
    elif negative and not positive:
        sentiment = "negative"
    else:
        sentiment = "neutral"

    return {
        "language": "other",
        "sentiment": sentiment,
        "theme": "other",
        "product": "none",
        "is_spam": False,
    }


def deterministic_classification(text: str) -> dict:
    emoji_only = emoji_only_classification(text)

    if emoji_only is not None:
        return emoji_only

    result = {
        "language": rule_language(text),
        "sentiment": rule_sentiment(text),
        "theme": rule_theme(text),
        "product": rule_product(text),
        "is_spam": rule_spam(text),
    }

    if CONVERSATIONAL_PATTERN.match(normalize_text(text)):
        result.update(
            sentiment="neutral", theme="other", product="none", is_spam=False
        )
        result["language"] = result["language"] or "fr"

    elif result["is_spam"]:
        # Convention du benchmark humain : un spam n'exprime pas d'avis sur
        # Awalé et ne porte sur aucun thème ni produit.
        result.update(sentiment="neutral", theme="other", product="none")

    elif (
        result["theme"] is None
        and result["product"] is None
        and result["sentiment"] is not None
        and "?" not in strip_fillers(text)
    ):
        # Avis général sans sujet identifiable ("bravo, c'est bien fait",
        # "c'est enjaillant, no drap") : thème other, et aucun motif de spam.
        result["theme"] = "other"
        result["is_spam"] = False

    return result


FIELDS = ["language", "sentiment", "theme", "product", "is_spam"]

# Champs que le modèle peut avoir à compléter (le produit ne lui est jamais
# demandé).
MODEL_FIELDS = ["language", "sentiment", "theme", "is_spam"]

# Thèmes qui portent sur la boisson elle-même. Convention du benchmark humain :
# un commentaire sur l'un de ces thèmes sans produit nommé vise quand même un
# produit ("la bouteille fuit", "c'est cher") → unknown. Les autres thèmes
# (promotion, delivery, service, other) ne visent pas de produit → none.
PRODUCT_THEMES = {
    "taste",
    "price",
    "availability",
    "packaging",
    "health",
    "product_question",
}


def derive_product(theme: str) -> str:
    """Produit quand aucun produit n'est explicitement nommé."""
    return "unknown" if theme in PRODUCT_THEMES else "none"


def is_complete(result: dict) -> bool:
    """
    Le modèle local n'est pas appelé si toutes les dimensions
    principales sont déterminables par les règles. Le produit n'est pas
    exigé : sans nom de produit, il est déduit du thème (merge_prediction).
    """
    return all(result[k] is not None for k in MODEL_FIELDS)


def merge_prediction(rules: dict, model_prediction: dict | None) -> dict:
    """Fusion finale : les règles priment, le modèle complète le reste.

    Le produit n'est jamais pris au modèle : soit la règle trouve un nom de
    produit, soit il est déduit du thème final (voir derive_product). Le
    modèle 0.5B inventait des produits absents du texte.
    """
    final = {
        field: (
            rules[field]
            if rules[field] is not None
            else model_prediction[field]
        )
        for field in MODEL_FIELDS
    }

    final["product"] = (
        rules["product"]
        if rules["product"] is not None
        else derive_product(final["theme"])
    )

    return {field: final[field] for field in FIELDS}


# ---------------------------------------------------------------------
# Modèle local
# ---------------------------------------------------------------------

def extract_json(text: str) -> dict:
    start = text.find("{")
    end = text.rfind("}")

    if start == -1 or end == -1:
        raise ValueError(f"JSON introuvable: {text}")

    return json.loads(text[start:end + 1])


def validate_model_prediction(pred: dict) -> dict:
    """Ramène la réponse du modèle à un vocabulaire fermé.

    Garde-fou : le modèle ne peut produire que des catégories connues, jamais un
    nombre ni un libellé libre. Une réponse absente ou hors vocabulaire est
    remplacée par une valeur par défaut, MAIS le champ concerné est listé dans
    "coerced" et le script en affiche le total : un remplacement n'est jamais
    silencieux.
    """
    coerced = []

    def pick(field: str, allowed: set, default: str) -> str:
        value = str(pred.get(field, default)).strip().lower()

        if field not in pred or value not in allowed:
            coerced.append(field)
            return default

        return value

    language = pick("language", LANGUAGES, "other")
    sentiment = pick("sentiment", SENTIMENTS, "neutral")
    theme = pick("theme", THEMES, "other")

    spam = pred.get("is_spam", False)

    if isinstance(spam, str):
        spam = spam.strip().lower() in {"true", "1", "yes"}

    return {
        "language": language,
        "sentiment": sentiment,
        "theme": theme,
        "is_spam": bool(spam),
        "coerced": coerced,
    }


def load_model():
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    tokenizer.padding_side = "left"

    # Pas de device_map="auto" : sur CPU, accelerate déchargeait une partie
    # des poids sur le disque ("offloaded to the disk"), ce qui ralentissait
    # fortement l'inférence.
    device = "cuda" if torch.cuda.is_available() else "cpu"

    model = AutoModelForCausalLM.from_pretrained(
        MODEL_NAME,
        dtype=torch.bfloat16 if device == "cuda" else torch.float32,
    ).to(device)

    model.eval()

    return tokenizer, model


def build_messages(text: str) -> list[dict]:
    """Prompt système, exemples few-shot en tours de conversation, puis le
    commentaire seul. Les résultats des règles ne sont pas transmis : la
    fusion (merge_prediction) les fait primer de toute façon, et un petit
    modèle suit mieux un message court."""
    messages = [{"role": "system", "content": SYSTEM_PROMPT}]

    for example_text, example_json in FEW_SHOT_EXAMPLES:
        messages.append({"role": "user", "content": example_text})
        messages.append({"role": "assistant", "content": example_json})

    messages.append({"role": "user", "content": text})

    return messages


def model_classification_batch(
    texts: list[str],
    tokenizer,
    model,
) -> list[dict]:

    prompts = [
        tokenizer.apply_chat_template(
            build_messages(text),
            tokenize=False,
            add_generation_prompt=True,
        )
        for text in texts
    ]

    device = next(model.parameters()).device

    inputs = tokenizer(
        prompts,
        return_tensors="pt",
        padding=True,
    ).to(device)

    with torch.inference_mode():

        outputs = model.generate(
            **inputs,
            max_new_tokens=60,
            do_sample=False,
            pad_token_id=tokenizer.pad_token_id,
        )

    predictions = []

    for i in range(len(texts)):

        generated = outputs[i][inputs["input_ids"].shape[1]:]

        response = tokenizer.decode(
            generated,
            skip_special_tokens=True,
        )

        predictions.append(
            validate_model_prediction(
                extract_json(response)
            )
        )

    return predictions


OUTPUT_COLUMNS = [
    "comment_id",
    "comment_text",
    "language_model",
    "sentiment_model",
    "theme_model",
    "product_model",
    "is_spam_model",
    "model_used",
    "rules_complete",
    "classifier_version",
]


def classify_with_fallback(texts, tokenizer, model):
    """
    Classe un lot avec le modèle local.

    Si la sortie du modèle est illisible pour le lot entier,
    retente chaque commentaire individuellement.

    Retourne deux listes alignées sur `texts` :
    - predictions : prédiction du modèle ou None en cas d'échec ;
    - errors : message d'erreur ou None.
    """

    try:
        predictions = model_classification_batch(texts, tokenizer, model)

        return predictions, [None] * len(texts)

    except (ValueError, KeyError, TypeError):
        # Un problème sur le batch entier ne doit pas faire échouer
        # définitivement le run.
        pass

    predictions = []
    errors = []

    for text in texts:

        try:
            prediction = model_classification_batch([text], tokenizer, model)[0]

            predictions.append(prediction)
            errors.append(None)

        except (ValueError, KeyError, TypeError) as error:

            predictions.append(None)
            errors.append(str(error)[:200])

    return predictions, errors


def write_predictions(existing: pd.DataFrame, new_predictions: pd.DataFrame) -> pd.DataFrame:
    """Fusionne l'existant et les nouvelles prédictions, puis écrit OUTPUT_FILE.

    L'écriture est atomique (fichier temporaire puis remplacement) : une
    interruption pendant l'écriture ne peut pas laisser un fichier tronqué. Comme
    le script ne classe que les comment_id absents de OUTPUT_FILE, relancer après
    une interruption reprend exactement où le run s'est arrêté.
    """
    output = (
        pd.concat([existing, new_predictions], ignore_index=True)
        .drop_duplicates(subset="comment_id", keep="last")
        .sort_values("comment_id")
        .reset_index(drop=True)
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    tmp_file = OUTPUT_FILE.with_suffix(OUTPUT_FILE.suffix + ".tmp")
    output.to_csv(tmp_file, index=False)
    os.replace(tmp_file, OUTPUT_FILE)

    return output


def load_existing_predictions() -> pd.DataFrame:
    """Prédictions déjà produites lors d'un run précédent, s'il y en a.

    Le traitement est incrémental : un commentaire déjà classé par la version
    courante (CLASSIFIER_VERSION) n'est jamais reclassé. Les lignes produites
    par une autre version (règles, prompt ou modèle différents) sont sauvegardées
    dans un fichier de backup puis reclassées : le fichier final ne mélange
    jamais deux versions du classifieur.
    """
    if not OUTPUT_FILE.exists():
        return pd.DataFrame(columns=OUTPUT_COLUMNS)

    existing = pd.read_csv(OUTPUT_FILE)

    if "classifier_version" not in existing.columns:
        existing["classifier_version"] = None

    stale = existing["classifier_version"] != CLASSIFIER_VERSION

    if stale.any():
        backup = OUTPUT_FILE.with_name(
            f"{OUTPUT_FILE.stem}.backup_{time.strftime('%Y%m%d_%H%M%S')}.csv"
        )
        existing.to_csv(backup, index=False)
        print(
            f"[INFO] {stale.sum()} prédiction(s) d'une autre version du classifieur "
            f"seront reclassées (ancien fichier sauvegardé : {backup.name})."
        )

    return existing[~stale].reset_index(drop=True)


# Réponses du modèle déjà obtenues pendant ce run, par texte normalisé.
# Le corpus contient ~45 % de doublons exacts : chaque texte n'est envoyé
# qu'une fois au modèle, et deux textes identiques reçoivent le même label.
_MODEL_CACHE: dict[str, dict] = {}


def classify_batch(texts: list[str], tokenizer, model) -> list[dict]:
    """Règles, puis modèle local pour les commentaires incomplets.

    Retourne, pour chaque texte, un dict aligné sur `texts` :
    - rules : sortie des règles déterministes ;
    - model : réponse validée du modèle, ou None s'il n'a pas été appelé ;
    - final : prédiction fusionnée, ou None si le modèle a échoué ;
    - error : message d'erreur du modèle, ou None.
    """
    outcomes = [
        {
            "rules": deterministic_classification(text),
            "model": None,
            "final": None,
            "error": None,
        }
        for text in texts
    ]

    model_indices = [
        i
        for i, outcome in enumerate(outcomes)
        if not is_complete(outcome["rules"])
    ]

    keys = {i: normalize_text(texts[i]) for i in model_indices}
    to_query = list(dict.fromkeys(
        keys[i] for i in model_indices if keys[i] not in _MODEL_CACHE
    ))

    if to_query:
        originals = {keys[i]: texts[i] for i in reversed(model_indices)}
        predictions, errors = classify_with_fallback(
            [originals[key] for key in to_query],
            tokenizer,
            model,
        )

        failed = {}

        for key, prediction, error in zip(to_query, predictions, errors):
            if prediction is None:
                failed[key] = error
            else:
                _MODEL_CACHE[key] = prediction

    else:
        failed = {}

    for i in model_indices:
        if keys[i] in failed:
            outcomes[i]["error"] = failed[keys[i]]
        else:
            outcomes[i]["model"] = _MODEL_CACHE[keys[i]]

    for outcome in outcomes:
        if outcome["error"] is None:
            outcome["final"] = merge_prediction(outcome["rules"], outcome["model"])

    return outcomes


def normalize_label(field: str, value):
    if field == "is_spam":
        return str(value).strip().lower() in {"true", "1", "yes"}

    return str(value).strip().lower()


def run_on_labeled_sample(limit: int | None = None) -> None:
    """Classe les commentaires du benchmark humain et compare aux labels.

    - limit=N (--test N) : les N premiers commentaires, avec le détail
      règles / Qwen / final / humain pour chacun. N'écrit aucun fichier.
    - limit=None (--bench) : tout le benchmark, et écrit BENCH_OUTPUT_FILE
      pour ai/evaluation/evaluate_classifier.py --model hybrid.

    Aucun des deux modes ne touche OUTPUT_FILE.
    """
    labeled = pd.read_csv(LABELED_FILE, encoding="utf-8-sig")
    verbose = limit is not None

    if verbose:
        labeled = labeled.head(limit)

    print("=" * 70)
    print(
        f"{'TEST' if verbose else 'BENCHMARK'} — {len(labeled)} commentaire(s) "
        f"annoté(s) | {CLASSIFIER_VERSION}"
    )
    print("=" * 70)

    tokenizer, model = load_model()

    rows = []
    correct = {field: 0 for field in FIELDS}
    evaluated = 0

    for start_idx in range(0, len(labeled), BATCH_SIZE):
        batch = labeled.iloc[start_idx:start_idx + BATCH_SIZE]
        texts = [str(text) for text in batch["comment_text"]]
        outcomes = classify_batch(texts, tokenizer, model)

        for (_, row), outcome in zip(batch.iterrows(), outcomes):
            human = {
                field: normalize_label(field, row[f"{field}_human"])
                for field in FIELDS
            }
            final = outcome["final"]

            if verbose:
                print("\n" + "-" * 70)
                print(f"{row['comment_id']} : {row['comment_text']}")
                print(f"  {'champ':<10} {'règle':<12} {'qwen':<17} {'final':<17} humain")

            if final is None:
                print(f"  ERREUR MODÈLE ({row['comment_id']}) : {outcome['error']}")
                continue

            evaluated += 1

            for field in FIELDS:
                ok = final[field] == human[field]
                correct[field] += ok

                if verbose:
                    qwen = (
                        "-"
                        if outcome["model"] is None or field == "product"
                        else outcome["model"][field]
                    )
                    print(
                        f"  {field:<10} {str(outcome['rules'][field]):<12} "
                        f"{str(qwen):<17} {str(final[field]):<17} "
                        f"{str(human[field]):<17} {'OK' if ok else 'XX'}"
                    )

            rows.append({
                "comment_id": row["comment_id"],
                "comment_text": row["comment_text"],
                **{f"{field}_model": final[field] for field in FIELDS},
                "model_used": outcome["model"] is not None,
                "rules_complete": is_complete(outcome["rules"]),
                "classifier_version": CLASSIFIER_VERSION,
            })

    print("\n" + "=" * 70)
    print(f"ACCURACY ({evaluated} commentaire(s) évalué(s))")
    print("=" * 70)

    for field in FIELDS:
        rate = correct[field] / evaluated if evaluated else 0
        print(f"  {field:<10}: {correct[field]:3}/{evaluated}  ({rate:.0%})")

    if not verbose:
        BENCH_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
        pd.DataFrame(rows, columns=OUTPUT_COLUMNS).to_csv(BENCH_OUTPUT_FILE, index=False)
        print(f"\nPrédictions écrites : {BENCH_OUTPUT_FILE}")
        print("Détail : python ai/evaluation/evaluate_classifier.py --model hybrid")


def main():

    df = pd.read_csv(INPUT_FILE)
    existing = load_existing_predictions()

    already_done = set(existing["comment_id"])
    df = df[~df["comment_id"].isin(already_done)].reset_index(drop=True)

    print(f"Commentaires source            : {len(existing) + len(df)}")
    print(f"Déjà classés (version courante): {len(existing)}")
    print(f"À classer ce run               : {len(df)}")

    if df.empty:
        print("\nRien à classer ce mois-ci — prédictions déjà à jour.")
        print(f"Output : {OUTPUT_FILE}")
        return

    print(f"Classifieur : {CLASSIFIER_VERSION}")

    tokenizer, model = load_model()

    results = []
    failed = []
    coerced_log = []

    total_batches = (len(df) + BATCH_SIZE - 1) // BATCH_SIZE

    try:

        for batch_number, start_idx in enumerate(range(0, len(df), BATCH_SIZE), start=1):

            batch = df.iloc[start_idx:start_idx + BATCH_SIZE]

            texts = [
                str(text)
                for text in batch["comment_text"]
            ]

            batch_start = time.perf_counter()

            outcomes = classify_batch(texts, tokenizer, model)

            for (_, row), outcome in zip(batch.iterrows(), outcomes):

                if outcome["error"] is not None:
                    # Le modèle n'a pas produit de sortie exploitable : on ne
                    # devine rien et on n'enregistre rien. Le commentaire n'est
                    # pas dans OUTPUT_FILE, il sera donc retenté au prochain run.
                    failed.append((row["comment_id"], outcome["error"]))
                    continue

                if outcome["model"] is not None and outcome["model"].get("coerced"):
                    coerced_log.append(
                        (row["comment_id"], outcome["model"]["coerced"])
                    )

                prediction = outcome["final"]

                results.append({
                    "comment_id": row["comment_id"],
                    "comment_text": row["comment_text"],
                    "language_model": prediction["language"],
                    "sentiment_model": prediction["sentiment"],
                    "theme_model": prediction["theme"],
                    "product_model": prediction["product"],
                    "is_spam_model": prediction["is_spam"],
                    "model_used": outcome["model"] is not None,
                    "rules_complete": is_complete(outcome["rules"]),
                    "classifier_version": CLASSIFIER_VERSION,
                })

            elapsed = time.perf_counter() - batch_start

            n_model = sum(
                not is_complete(outcome["rules"])
                for outcome in outcomes
            )

            print(
                f"[{start_idx + 1}/{len(df)}] "
                f"batch={len(batch)} | "
                f"model={n_model} | "
                f"{elapsed:.2f}s"
            )

            if batch_number % CHECKPOINT_EVERY_BATCHES == 0 and batch_number < total_batches:
                write_predictions(
                    existing,
                    pd.DataFrame(results, columns=OUTPUT_COLUMNS),
                )
                print(
                    f"    sauvegarde intermédiaire : {len(existing) + len(results)} "
                    f"commentaires enregistrés dans {OUTPUT_FILE.name}"
                )

    finally:
        # Sauvegarde finale, y compris après une erreur ou un Ctrl+C : ce qui a
        # déjà été classé n'est jamais perdu.
        new_predictions = pd.DataFrame(results, columns=OUTPUT_COLUMNS)
        output = write_predictions(existing, new_predictions)

    print("\n" + "=" * 70)
    print("RÉSULTAT HYBRIDE — INCRÉMENTAL")
    print("=" * 70)

    model_used = new_predictions["model_used"].astype(bool)

    print(f"Classés ce run       : {len(new_predictions)}")
    print(f"  dont règles seules  : {(~model_used).sum()}")
    print(f"  dont modèle local   : {model_used.sum()}")
    print(f"Total accumulé (fichier) : {len(output)}")
    print(f"Output                   : {OUTPUT_FILE}")

    if coerced_log:
        fields = sorted({f for _, fs in coerced_log for f in fs})
        print(
            f"\n[ATTENTION] {len(coerced_log)} commentaire(s) dont la réponse du modèle "
            f"était absente ou hors vocabulaire (champs : {', '.join(fields)}) ont reçu "
            "la valeur par défaut. À surveiller : une hausse signale un modèle ou un "
            "prompt qui dérive."
        )

    if failed:
        print(f"\n[ERREUR] {len(failed)} commentaire(s) sans sortie exploitable du modèle :")
        for comment_id, error in failed[:20]:
            print(f"  - {comment_id} : {error}")
        print(
            "Ils ne sont PAS enregistrés et seront retentés au prochain lancement. "
            "Le rapport ne doit pas être livré tant qu'ils manquent."
        )
        sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Classification hybride (règles + Qwen) des commentaires."
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--test",
        type=int,
        nargs="?",
        const=10,
        metavar="N",
        help=(
            "Contrôle rapide avant un run complet : classe les N premiers "
            "commentaires annotés (défaut 10) et affiche le détail. "
            "N'écrit aucun fichier."
        ),
    )
    mode.add_argument(
        "--bench",
        action="store_true",
        help=(
            "Classe tout le benchmark humain et écrit les prédictions pour "
            "evaluate_classifier.py --model hybrid."
        ),
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    if args.test is not None:
        run_on_labeled_sample(limit=args.test)
    elif args.bench:
        run_on_labeled_sample(limit=None)
    else:
        # Sans option : run complet, c'est ce qu'appelle run_pipeline.py.
        main()
