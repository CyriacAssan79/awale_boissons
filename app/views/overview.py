import streamlit as st

from common import integer, load_monthly, money, period_filter
from theme import banner, hero, month_label, question_card


active_months = period_filter()

monthly = load_monthly()
monthly_filtered = monthly[monthly["month"].isin(active_months)].copy()


# ---------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------

period_badge = (
    f"Abidjan · {month_label(min(active_months))} – {month_label(max(active_months))}"
    if active_months
    else "Abidjan"
)

hero(
    eyebrow="Awalé Boissons",
    title="Marketing Decision Cockpit",
    text=(
        "Vue décisionnelle mensuelle : données observées, qualité des données "
        "et signaux disponibles. Les résultats ne constituent pas une "
        "attribution causale des ventes aux canaux."
    ),
    pills=[
        ("verified", "Données observées", "Aucune projection"),
        ("rule", "Qualité des données", "Tests dbt automatisés"),
        ("hub", "Sans attribution causale", "Associations, pas causes"),
    ],
    badge=period_badge,
)


# ---------------------------------------------------------------------
# GLOBAL KPIs
# ---------------------------------------------------------------------

total_spend = monthly_filtered["campaign_spend_fcfa"].sum()
total_revenue = monthly_filtered["net_revenue_fcfa"].sum()
total_units = monthly_filtered["net_units_sold"].sum()

missing_days = monthly_filtered["missing_sales_days"].sum()

# Un mois sans information de couverture (NaN) ne doit jamais passer pour un
# mois complet : pandas ignore les NaN dans sum(), il faut donc le tester.
unknown_coverage_months = monthly_filtered.loc[
    monthly_filtered["missing_sales_days"].isna(), "month"
]

st.write("")

if missing_days > 0:
    incomplete = monthly_filtered.loc[
        monthly_filtered["missing_sales_days"].fillna(0) > 0, "month"
    ]
    banner(
        "warning",
        "Avertissement de complétude — " + ", ".join(month_label(m) for m in incomplete),
        "La période sélectionnée contient des jours sans données de ventes. "
        "Les comparaisons doivent tenir compte de cette couverture.",
        tag=f"{integer(missing_days)} j manquants",
    )

if not unknown_coverage_months.empty:
    banner(
        "warning",
        "Couverture des ventes inconnue",
        "Mois concernés : "
        + ", ".join(month_label(m) for m in unknown_coverage_months)
        + ". Ces mois ne doivent pas être lus comme complets.",
    )

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Dépenses marketing", money(total_spend))

with col2:
    st.metric("CA net observé", money(total_revenue))

with col3:
    st.metric("Unités vendues", integer(total_units))

with col4:
    st.metric("Jours de ventes manquants", integer(missing_days))


# ---------------------------------------------------------------------
# NAVIGATION PAR QUESTION MÉTIER
# ---------------------------------------------------------------------

st.markdown(
    '<div class="subsection"><span class="subsection-title">Exploration par question métier</span>'
    '<span class="subsection-sub">Chaque carte ouvre la page correspondante</span></div>',
    unsafe_allow_html=True,
)

QUESTIONS = [
    ("marketing", "views/marketing.py", "Où va l'argent ?", "Marketing",
     "Dépenses de campagne par canal, comparées au plan média.", ":material/payments:"),
    ("sales", "views/sales.py", "Que se passe-t-il côté ventes ?", "Ventes",
     "CA net, unités, couverture des données et mix produit.", ":material/trending_up:"),
    ("customers", "views/customers.py", "Que disent les clients ?", "Voix client",
     "Sentiment, thèmes, produits mentionnés et commandes WhatsApp.", ":material/forum:"),
    ("recommendation", "views/recommendation.py", "Que faire ensuite ?", "Recommandation",
     "Répartition proposée des 15 M FCFA et cadre de test.", ":material/lightbulb:"),
    ("report", "views/report.py", "Rapport mensuel IA", "Synthèse",
     "Bilan du mois : créer, mettre à jour, lire et télécharger.", ":material/auto_awesome:"),
    ("ask", "views/ask_data.py", "Demander à l'IA", "Ask the Data",
     "Posez une question en français sur les ventes ou les dépenses.", ":material/smart_toy:"),
]

for start in range(0, len(QUESTIONS), 3):
    columns = st.columns(3)

    for column, (key, page, question, tag, description, page_icon) in zip(
        columns, QUESTIONS[start:start + 3]
    ):
        with column:
            question_card(key, page, question, tag, description, page_icon)
