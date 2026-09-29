from classify_comments_hybrid import (
    POSITIVE_PATTERNS,
    NEGATIVE_PATTERNS,
    has_negated_sentiment,
)


TESTS = [
    ("Ce n'est pas bon", POSITIVE_PATTERNS),
    ("C'est pas bon", POSITIVE_PATTERNS),
    ("Ce n'est vraiment pas bon", POSITIVE_PATTERNS),
    ("Ce n'est pas délicieux", POSITIVE_PATTERNS),

    ("Ce n'est pas mauvais", NEGATIVE_PATTERNS),
    ("Ce n'est pas cher", NEGATIVE_PATTERNS),
]


for text, patterns in TESTS:
    result = has_negated_sentiment(text, patterns)
    print(f"{result!r:5} | {text}")