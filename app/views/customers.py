import pandas as pd
import plotly.express as px
import streamlit as st

from common import integer, load_query, period_filter, safe_query, table_exists, totals
from theme import GINGEMBRE_DARK, GRID, PRODUCT_COLORS, SENTIMENT_COLORS, card, card_title, section, show_chart, subsection


active_months = period_filter()

whatsapp = load_query(
    """
    SELECT *
    FROM mart_whatsapp_monthly
    ORDER BY month
    """
)

whatsapp_reachat = safe_query(
    """
    SELECT
        COUNT(*) FILTER (WHERE has_delivered_order) AS customers_with_delivery,
        COUNT(*) FILTER (WHERE is_repeat_customer) AS repeat_customers
    FROM mart_whatsapp_customers
    """
)

social_available = table_exists("mart_social_monthly")


if social_available:
    social = load_query(
        """
        SELECT *
        FROM mart_social_monthly
        ORDER BY month
        """
    )
else:
    social = pd.DataFrame()


section(
    3,
    "Que disent les clients ?",
    "Sentiment, thèmes et produits dans les commentaires, et commandes WhatsApp.",
)

if social_available and not social.empty:

    social_filtered = social[social["month"].isin(active_months)].copy()

    # -----------------------------------------------------------------
    # KPIs
    # -----------------------------------------------------------------

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Commentaires", integer(social_filtered["comments_count"].sum()))

    with col2:
        st.metric("Positifs", integer(social_filtered["positive_comments_count"].sum()))

    with col3:
        st.metric("Négatifs", integer(social_filtered["negative_comments_count"].sum()))

    with col4:
        st.metric("Spam détecté", integer(social_filtered["spam_comments_count"].sum()))

    st.write("")

    # -----------------------------------------------------------------
    # Sentiment + thèmes
    # -----------------------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:
        with card("sentiment"):
            sentiment = totals(
                social_filtered,
                {
                    "positive_comments_count": "Positif",
                    "neutral_comments_count": "Neutre",
                    "negative_comments_count": "Négatif",
                },
                "sentiment",
            )

            fig_sentiment = px.bar(
                sentiment,
                x="sentiment",
                y="comments",
                color="sentiment",
                color_discrete_map=SENTIMENT_COLORS,
                title="Sentiment des commentaires",
                labels={"sentiment": "", "comments": "Commentaires"},
                text="comments",
            )

            fig_sentiment.update_traces(
                textposition="outside",
                cliponaxis=False,
                marker_cornerradius=6,
            )
            fig_sentiment.update_layout(showlegend=False)
            fig_sentiment.update_yaxes(title=None)

            show_chart(fig_sentiment, height=340)

    with col2:
        with card("themes"):
            themes = totals(
                social_filtered,
                {
                    "taste_comments_count": "Goût",
                    "price_comments_count": "Prix",
                    "promotion_comments_count": "Promotion",
                    "availability_comments_count": "Disponibilité",
                    "packaging_comments_count": "Emballage",
                    "health_comments_count": "Santé",
                    "delivery_comments_count": "Livraison",
                    "service_comments_count": "Service",
                    "product_question_comments_count": "Question produit",
                    "other_theme_comments_count": "Autre",
                },
                "theme",
            ).sort_values("comments", ascending=False)

            fig_themes = px.bar(
                themes,
                x="comments",
                y="theme",
                orientation="h",
                title="Thèmes mentionnés",
                labels={"theme": "", "comments": "Commentaires"},
                text="comments",
                color_discrete_sequence=[GINGEMBRE_DARK],
            )

            fig_themes.update_traces(
                textposition="outside",
                cliponaxis=False,
                marker_cornerradius=6,
            )
            fig_themes.update_layout(showlegend=False)
            fig_themes.update_yaxes(
                autorange="reversed",
                showgrid=False,
                title=None,
            )
            fig_themes.update_xaxes(showgrid=True, gridcolor=GRID, title=None)

            show_chart(fig_themes, height=340)

    # -----------------------------------------------------------------
    # Produits + qualité IA
    # -----------------------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:
        with card("products"):
            card_title("Produits mentionnés")

            products = totals(
                social_filtered,
                {
                    "bissap_comments_count": "Bissap",
                    "gingembre_comments_count": "Gingembre",
                    "bouye_comments_count": "Bouye",
                    "multiple_product_comments_count": "Plusieurs produits",
                    "unknown_product_comments_count": "Produit inconnu",
                    "no_product_comments_count": "Aucun produit",
                },
                "product",
            ).sort_values("comments", ascending=False)

            st.dataframe(
                products,
                hide_index=True,
                width="stretch",
                column_config={
                    "product": "Produit",
                    "comments": st.column_config.ProgressColumn(
                        "Commentaires",
                        format="%d",
                        min_value=0,
                        max_value=max(1, int(products["comments"].max())),
                    ),
                },
            )

    with col2:
        with card("ai_quality"):
            card_title("Qualité de l'inférence IA")

            quality = pd.DataFrame(
                {
                    "Indicateur": [
                        "Commentaires analysés",
                        "Modèle local utilisé",
                        "Règles seules suffisantes",
                    ],
                    "Volume": [
                        social_filtered["comments_count"].sum(),
                        social_filtered["model_used_count"].sum(),
                        social_filtered["rules_complete_count"].sum(),
                    ],
                }
            )

            st.dataframe(
                quality,
                hide_index=True,
                width="stretch",
                column_config={
                    "Volume": st.column_config.NumberColumn(format="localized"),
                },
            )

            st.caption(
                "Le benchmark humain de 50 commentaires sert à évaluer "
                "le classifieur ; il ne constitue pas un jeu d'entraînement."
            )

else:

    st.warning(
        "La mart Customer Voice n'est pas disponible. "
        "Exécuter dbt pour construire mart_social_monthly."
    )


# -----------------------------------------------------------------
# Commandes WhatsApp (livraison)
# -----------------------------------------------------------------

subsection("Commandes WhatsApp", "Canal livraison : commandes, produits demandés, réachat")

whatsapp_filtered = whatsapp[whatsapp["month"].isin(active_months)].copy()

if whatsapp_filtered.empty:

    st.info("Aucune commande WhatsApp sur la période sélectionnée.")

else:

    orders = whatsapp_filtered["orders"].sum()
    delivered = whatsapp_filtered["delivered_orders"].sum()

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric("Commandes WhatsApp", integer(orders))

    with col2:
        st.metric("Commandes livrées", integer(delivered))

    with col3:
        st.metric("Unités commandées", integer(whatsapp_filtered["total_units"].sum()))

    with col4:
        if whatsapp_reachat is None or not whatsapp_reachat["customers_with_delivery"].iloc[0]:
            st.metric("Réachat (livrées)", "—")
        else:
            with_delivery = whatsapp_reachat["customers_with_delivery"].iloc[0]
            repeaters = whatsapp_reachat["repeat_customers"].iloc[0]
            st.metric(
                "Réachat (livrées)",
                f"{repeaters / with_delivery * 100:.1f} %",
                help=(
                    f"{integer(repeaters)} clients sur {integer(with_delivery)} ayant reçu au "
                    "moins une commande ont reçu au moins deux commandes. Calculé sur toute la "
                    "période, pas sur la sélection. Le client est un numéro de téléphone "
                    "normalisé, pas une identité vérifiée."
                ),
            )

    st.write("")

    col1, col2 = st.columns(2)

    with col1:
        with card("whatsapp_products"):
            wa_products = pd.DataFrame(
                {
                    "product": ["bissap", "gingembre", "bouye"],
                    "units": [
                        whatsapp_filtered["bissap_units"].sum(),
                        whatsapp_filtered["gingembre_units"].sum(),
                        whatsapp_filtered["bouye_units"].sum(),
                    ],
                }
            ).sort_values("units", ascending=False)

            fig_wa = px.bar(
                wa_products,
                x="product",
                y="units",
                color="product",
                color_discrete_map=PRODUCT_COLORS,
                title="Unités commandées par produit",
                labels={"product": "", "units": "Unités"},
                text="units",
            )

            fig_wa.update_traces(
                textposition="outside",
                cliponaxis=False,
                marker_cornerradius=6,
            )
            fig_wa.update_layout(showlegend=False)
            fig_wa.update_yaxes(title=None)

            show_chart(fig_wa, height=320)

            st.caption(
                "Unités lues dans le texte des commandes : le format n'est pas toujours précisé, "
                "et une commande sans produit reconnu n'est pas comptée dans un produit."
            )

    with col2:
        with card("whatsapp_amounts"):
            card_title("Montants des commandes livrées")

            needed = [
                "delivered_amount_missing_orders",
                "delivered_outlier_amount_orders",
            ]

            if all(c in whatsapp_filtered.columns for c in needed):
                missing_amount = whatsapp_filtered["delivered_amount_missing_orders"].sum()
                outlier_amount = whatsapp_filtered["delivered_outlier_amount_orders"].sum()

                amounts = pd.DataFrame(
                    {
                        "Commandes livrées": [
                            "Total",
                            "dont sans montant",
                            "dont montant invraisemblable (exclu)",
                            "dont montant exploitable",
                        ],
                        "Nombre": [
                            delivered,
                            missing_amount,
                            outlier_amount,
                            delivered - missing_amount - outlier_amount,
                        ],
                    }
                )

                st.dataframe(
                    amounts,
                    hide_index=True,
                    width="stretch",
                    column_config={
                        "Nombre": st.column_config.NumberColumn(format="localized"),
                    },
                )

                st.caption(
                    "Un montant absent ou invraisemblable n'est pas compté à zéro : il est "
                    "inconnu. Aucun revenu livraison n'est donc affiché, ce serait une "
                    "extrapolation."
                )
            else:
                st.info(
                    "Le détail des montants n'est pas encore dans la base. "
                    "Exécuter python run_pipeline.py pour le calculer."
                )

