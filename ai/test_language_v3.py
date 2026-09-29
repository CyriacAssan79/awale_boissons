from classify_comments_hybrid import rule_language


TESTS = [
    "Merci beaucoup pour cette boisson",
    "Thank you very much",
    "How much coûte le bissap ?",
    "Wallah c'est trop bon",
    "Le bissap est délicieux",
    "This drink is great",
    "😍😍😍",
    "Bissap",
    "Bonjour",
    "No drap, c'est bon",
    "Hello friend",
]


for text in TESTS:
    result = rule_language(text)
    print(f"{result!r:10} | {text}")