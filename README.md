# Awalé Boissons — Marketing Decision Pipeline

## 1. Contexte

Awalé Boissons commercialise notamment des boissons au bissap, gingembre et bouyé à travers plusieurs points de vente à Abidjan. Projet réalisé dans le cadre du challenge **Kômian AI Engineer**.

> **Question métier :** Où placer les prochains 15 M FCFA de budget marketing, et comment produire cette analyse chaque mois de manière reproductible en moins d'une heure, sans data engineer ?

## 2. Questions métier

Le pipeline répond à quatre questions :

1. Où va l'argent ?
2. Que se passe-t-il sur les ventes ?
3. Que dit la Customer Voice ?
4. Que tester avec les prochains 15 M FCFA ?

## 3. Architecture

```
RAW → STAGING → INTERMEDIATE → MARTS → DECISION → DASHBOARD
```

- **RAW** : Campaign Spend / Media Plan / POS Sales / Social Comments / WhatsApp Orders
- **STAGING** : nettoyage / déduplication / normalisation / quality flags
- **INTERMEDIATE** : réconciliation / calendrier / parsing / enrichissement
- **MARTS** : Marketing / Sales / WhatsApp / Social / Decision
- **AI + Decision Layer**
- **Streamlit Dashboard**

## 4. Stack technique

Python 3.11 · pandas · DuckDB · dbt Core + dbt-duckdb · openpyxl · modèle local + règles hybrides · Streamlit · Plotly · dbt tests.

## 5. Sources

- `raw_campaign_spend_export`
- `raw_media_plan`
- `raw_pos_sales_daily`
- `raw_social_comments`
- `raw_whatsapp_orders`
- `raw_social_comments_predictions_v2`

Campaign Spend et Media Plan restent distincts afin d'exposer leurs divergences.

## 6. Data Quality

Les valeurs manquantes ne sont jamais converties automatiquement en zéro. Les contrôles couvrent :

- Doublons, dates, retours, unités/CA négatifs, jours manquants
- Réconciliation marketing
- Montants WhatsApp manquants, `order_ref` répétés, parsing, produits inconnus
- Unicité des `comment_id`

> **Règle :** ne jamais déduire un catalogue de prix à partir de `amount_fcfa` / `quantity`.

## 7. IA — Customer Voice

Les commentaires sont enrichis avec `language`, `sentiment`, `theme`, `product` et `is_spam`. Le benchmark utilise **Qwen/Qwen2.5-0.5B-Instruct** sur 50 commentaires annotés humainement. Ces 50 annotations servent à l'évaluation et ne sont pas présentées comme un jeu de fine-tuning.

**Évaluation V1 → V2 Hybrid :**

| Dimension       | V1  | V2 Hybrid |
| --------------- | --- | --------- |
| Language        | 72% | 22%       |
| Sentiment       | 54% | 80%       |
| Theme           | 40% | 78%       |
| Product         | 58% | 52%       |
| Spam            | 94% | 88%       |
| Exact agreement | 8%  | 14%       |

## 8. Customer Voice — janvier à juin 2026

**2 831 commentaires** : 1 186 positifs, 735 négatifs, 513 spam.

Principaux thèmes :

| Thème        | Volume |
| ------------ | ------ |
| Taste        | 680    |
| Price        | 376    |
| Promotion    | 313    |
| Availability | 170    |
| Packaging    | 208    |
| Health       | 152    |
| Delivery     | 109    |

- Price : 347 mentions négatives
- Availability : 151 mentions négatives
- Taste : 578 positifs contre 14 négatifs

Ce sont des signaux, pas une preuve causale.

## 9. Marketing — janvier à juin 2026

Campaign export : environ **15,84 M FCFA**.

| Canal              | Dépense observée  |
| ------------------ | ----------------- |
| Meta               | 6,953 M FCFA      |
| TikTok             | 4,207 M FCFA      |
| Radio              | 2,000 M FCFA      |
| Google             | 1,783 M FCFA      |
| Influenceurs       | 0,900 M FCFA      |
| Activation terrain | 0 (dans l'export) |

Le media plan indique cependant 2,41 M FCFA facturés pour l'activation terrain : **divergence à réconcilier**.

## 10. Ventes — janvier à juin 2026

| Mois    | CA net       |
| ------- | ------------ |
| Janvier | 17,66 M FCFA |
| Février | 16,15 M FCFA |
| Mars    | 20,80 M FCFA |
| Avril   | 6,55 M FCFA  |
| Mai     | 12,49 M FCFA |
| Juin    | 14,16 M FCFA |

Avril comporte 14 jours sans données, du 13 au 26 avril, et ne doit donc pas être interprété comme un mois complet.

## 11. Allocation proposée — 15 M FCFA

| Canal              | Budget          |
| ------------------ | --------------- |
| Meta               | 5,0 M FCFA      |
| TikTok             | 4,0 M FCFA      |
| Google             | 2,5 M FCFA      |
| Radio              | 1,5 M FCFA      |
| Influenceurs       | 1,0 M FCFA      |
| Activation terrain | 1,0 M FCFA      |
| **Total**          | **15,0 M FCFA** |

Cette proposition est un budget de test et d'instrumentation, pas un classement causal.

## 12. Conditions de test

- **Meta / TikTok** : impressions, clics, conversion
- **Google** : clics, conversion
- **Radio** : code ou numéro dédié
- **Influenceurs** : lien ou code dédié
- **Activation terrain** : réconcilier facturation et dépenses campagne avant extrapolation

## 13. Limites méthodologiques

- Une association entre dépenses d'un canal et ventes observées ne démontre pas une relation de cause à effet.
- Ne pas utiliser `mart_channel_performance_monthly` pour attribuer le CA aux canaux : le CA mensuel total y est répété par canal.
- CPC, CPM, impressions et clics ne constituent pas à eux seuls une preuve d'efficacité commerciale.

## 14. Reproductibilité

```bash
cd /mnt/c/Users/KSOMS/Favorites/awale_boissons
cd dbt
dbt run
dbt test
cd ..
streamlit run app/app.py
```

**Validation actuelle :** 22/22 modèles dbt et 74/74 tests dbt, avec 0 erreur et 0 warning.

## 15. Structure du repository

```
awale_boissons/
├── app/
│   └── app.py
├── ai/
│   ├── classify_comments_hybrid.py
│   └── evaluation/
├── data/
│   ├── raw/
│   └── processed/
├── dbt/
│   ├── models/staging/
│   ├── models/intermediate/
│   ├── models/marts/
│   ├── tests/
│   └── dbt_project.yml
├── docs/
├── requirements.txt
└── README.md
```

## 16. Run mensuel

Cible : environ 50–55 minutes.

| Étape       | Cible     |
| ----------- | --------- |
| Préparation | 10 min    |
| DuckDB      | 5 min     |
| dbt run     | 5 min     |
| dbt test    | 5 min     |
| Qualité     | 10 min    |
| IA          | 10–15 min |
| Dashboard   | 5 min     |

Le détail figure dans `Awale_Boissons_Runbook_Mensuel.pdf`.

## 17. Principe de décision

```
Faits observés → qualité des données → observations → signaux → limites → hypothèses → test → décision
```

## 18. Livrables

- Pipeline DuckDB + dbt
- Tests qualité
- Réconciliation marketing
- Ventes
- WhatsApp
- Customer Voice IA
- Benchmark
- Dashboard Streamlit
- Allocation 15 M FCFA
- Client Note
- Runbook mensuel
