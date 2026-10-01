import streamlit as st

from common import integer, load_monthly, money, period_filter
from theme import hero, month_label


active_months = period_filter()

monthly = load_monthly()
monthly_filtered = monthly[monthly["month"].isin(active_months)].copy()


# ---------------------------------------------------------------------
# HEADER
# ---------------------------------------------------------------------

hero(
    eyebrow="Awalé Boissons",
    title="Marketing Decision Cockpit",
    text=(
        "Vue décisionnelle mensuelle — données observées, qualité des données "
        "et signaux disponibles. Les résultats ne constituent pas une "
        "attribution causale des ventes aux canaux."
    ),
    pills=["Données observées", "Qualité des données", "Sans attribution causale"],
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

col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Dépenses marketing", money(total_spend))

with col2:
    st.metric("CA net observé", money(total_revenue))

with col3:
    st.metric("Unités vendues", integer(total_units))

with col4:
    st.metric("Jours de ventes manquants", integer(missing_days))


if missing_days > 0:
    st.warning(
        "Attention : la période sélectionnée contient des jours sans données "
        "de ventes. Les comparaisons doivent tenir compte de cette couverture."
    )

if not unknown_coverage_months.empty:
    st.warning(
        "Couverture des ventes inconnue pour : "
        + ", ".join(month_label(m) for m in unknown_coverage_months)
        + ". Ces mois ne doivent pas être lus comme complets."
    )


# ---------------------------------------------------------------------
# NAVIGATION RAPIDE
# ---------------------------------------------------------------------

st.write("")

col1, col2, col3 = st.columns(3)

with col1:
    st.page_link("views/marketing.py", label="Où va l'argent ?", icon=":material/payments:")
    st.page_link("views/sales.py", label="Que se passe-t-il côté ventes ?", icon=":material/trending_up:")

with col2:
    st.page_link("views/customers.py", label="Que disent les clients ?", icon=":material/forum:")
    st.page_link("views/recommendation.py", label="Que faire ensuite ?", icon=":material/lightbulb:")

with col3:
    st.page_link("views/report.py", label="Rapport mensuel IA", icon=":material/auto_awesome:")
