from ai.ask_data.periods import extract_relative_months
from ai.ask_data.question_parser import parse_question
from ai.ask_data.sql_builder import build_sql


def test_extract_relative_months():
    assert extract_relative_months("3 derniers mois") == 3
    assert extract_relative_months("ces 3 derniers mois") == 3
    assert extract_relative_months("les 6 derniers mois") == 6
    assert extract_relative_months("le mois dernier") is None


def test_parse_relative_months():
    intent = parse_question(
        "Donne moi les dépenses publicitaires par canal ces 3 derniers mois"
    )

    assert intent.metric == "spend_marketing"
    assert intent.dimensions == ["channel"]
    assert intent.relative_months == 3


def test_sql_relative_months():
    intent = parse_question(
        "Donne moi les dépenses publicitaires par canal ces 3 derniers mois"
    )

    sql = build_sql(intent)

    assert "INTERVAL '2 months'" in sql
    assert "MAX(month)" in sql
    assert "GROUP BY channel" in sql