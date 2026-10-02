from ai.ask_data.intent import build_intent
from ai.ask_data.sql_builder import build_sql


def test_sql_spend_meta():
    intent = build_intent(
        question="Combien avons-nous dépensé sur Meta ?",
        metric="spend_marketing",
        channel="Meta",
    )

    sql = build_sql(intent)

    assert "mart_marketing_channel_monthly" in sql
    assert "SUM(campaign_spend_fcfa)" in sql
    assert "channel = 'Meta'" in sql


def test_sql_ca_net_juin():
    intent = build_intent(
        question="Quel est le CA net en juin 2026 ?",
        metric="ca_net",
        month="2026-06",
    )

    sql = build_sql(intent)

    assert "mart_sales_monthly" in sql
    assert "SUM(net_revenue_fcfa)" in sql
    assert "2026-06-01" in sql
    assert "2026-07-01" in sql


def test_sql_dimension_canal():
    intent = build_intent(
        question="Quel est le spend par canal ?",
        metric="spend_marketing",
        dimension="channel",
    )

    sql = build_sql(intent)

    assert "channel" in sql
    assert "GROUP BY channel" in sql


def test_sql_injection_channel_rejetee():
    intent = build_intent(
        question="test",
        metric="spend_marketing",
        channel="DROP TABLE mart_marketing_channel_monthly",
    )

    try:
        build_sql(intent)
        assert False, "L'injection SQL aurait dû être rejetée."
    except ValueError as exc:
        assert "Canal inconnu" in str(exc)


def test_sql_injection_month_rejetee():
    intent = build_intent(
        question="test",
        metric="ca_net",
        month="DROP TABLE",
    )

    try:
        build_sql(intent)
        assert False, "L'injection SQL aurait dû être rejetée."
    except ValueError as exc:
        assert "Mois invalide" in str(exc)

def test_sql_multi_dimensions():
    intent = build_intent(
        question="Quel est le mix produit par mois et par produit ?",
        metric="mix_produit",
        dimensions=["month", "product"],
    )

    sql = build_sql(intent)

    assert "mart_product_mix_monthly" in sql
    assert "SUM(net_revenue_fcfa)" in sql
    assert "month" in sql
    assert "product" in sql
    assert "GROUP BY month, product" in sql