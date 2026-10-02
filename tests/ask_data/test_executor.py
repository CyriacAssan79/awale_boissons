from ai.ask_data.question_parser import parse_question
from ai.ask_data.executor import execute_intent


def test_question_ca_net_juin():
    question = "Quel est le CA net en juin 2026 ?"

    intent = parse_question(question)
    result = execute_intent(intent)

    assert not result.empty
    assert "ca_net" in result.columns
    assert result.iloc[0]["ca_net"] == 14125053.0


def test_question_spend_meta_juin():
    question = "Combien avons-nous dépensé sur Meta en juin 2026 ?"

    intent = parse_question(question)
    result = execute_intent(intent)

    assert not result.empty
    assert "spend_marketing" in result.columns
    assert result.iloc[0]["spend_marketing"] == 969900.0


def test_question_ca_net_par_mois():
    question = "Quel est le CA net par mois ?"

    intent = parse_question(question)
    result = execute_intent(intent)

    assert not result.empty
    assert "month" in result.columns
    assert "ca_net" in result.columns

    assert len(result) == 6