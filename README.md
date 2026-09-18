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
| Janvier | 17,65 M FCFA |
| Février | 16,12 M FCFA |
| Mars    | 20,73 M FCFA |
| Avril   | 6,55 M FCFA  |
| Mai     | 12,47 M FCFA |
| Juin    | 14,13 M FCFA |

CA net = CA brut diminué des retours (`net_revenue_fcfa` dans `mart_sales_monthly`). Les retours représentent 0,06 % à 0,3 % du CA brut selon les mois — un écart faible mais réel, qu'il n'est pas correct d'ignorer en affichant le brut sous l'étiquette « net ».

Avril comporte 14 jours sans données, du 13 au 26 avril, et ne doit donc pas être interprété comme un mois complet.

## 11. Allocation proposée — 15 M FCFA

| Canal              | Budget          | Part      |
| ------------------ | --------------- | --------- |
| Meta               | 5,55 M FCFA     | 37,0 %    |
| TikTok             | 3,10 M FCFA     | 20,7 %    |
| Radio              | 2,00 M FCFA     | 13,3 %    |
| Google             | 1,90 M FCFA     | 12,7 %    |
| Influenceurs       | 1,45 M FCFA     | 9,7 %     |
| Activation terrain | 1,00 M FCFA     | 6,7 %     |
| **Total**          | **15,0 M FCFA** | **100 %** |

Calcul (`dbt/models/marts/mart_budget_recommendation_15m.sql`) : un socle de 1 M FCFA par canal
finance l'instrumentation même des canaux les moins mesurés, puis le reliquat (9 M FCFA) est réparti
au prorata de `part de dépense observée × bonus de qualité d'evidence` (evidence_quality vient de la
complétude des données, pas de la performance commerciale). Cette allocation se recalcule donc si
les données du mois prochain changent — ce n'est ni un classement causal, ni un montant figé.

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

### 14.1 Données sources

Le fichier `data/raw/awale_boissons_starter_dataset.xlsx` (5 feuilles : `campaign_spend_export`,
`media_plan`, `pos_sales_daily`, `whatsapp_orders`, `social_comments`) n'est **pas** versionné dans
ce dépôt (voir `.gitignore`). Avant tout run :

1. Récupérer le fichier auprès de Kômian (starter dataset du challenge, ou export mensuel équivalent
   pour un run en production).
2. Le déposer tel quel dans `data/raw/awale_boissons_starter_dataset.xlsx` (le dossier est créé
   automatiquement si besoin par `ingestion/load_raw.py`).

Si le fichier est absent, `ingestion/load_raw.py` (et donc `run_pipeline.py`) s'arrête proprement
avec un `FileNotFoundError` explicite plutôt que d'échouer plus loin de façon obscure.

### 14.2 Installation

```bash
python -m venv .venv
# Windows : .venv\Scripts\activate | macOS/Linux : source .venv/bin/activate
pip install -r requirements.txt
```

### 14.3 Run complet

Depuis la racine du projet (aucun chemin codé en dur — fonctionne sur n'importe quelle machine) :

```bash
python run_pipeline.py
streamlit run app/app.py
```

`run_pipeline.py` enchaîne : ingestion des 5 sources → `dbt run` (hors modèles dépendants de l'IA) →
export du texte des commentaires → inférence IA → rechargement des prédictions dans DuckDB →
`dbt run` complet → `dbt test`. Options : `--skip-ai` (réutilise les prédictions déjà présentes),
`--skip-tests`.

**Validation actuelle :** 22/22 modèles dbt et 74/74 tests dbt, avec 0 erreur et 0 warning.

## 15. Structure du repository

```
awale_boissons/
├── app/
│   └── app.py
├── ai/
│   ├── classify_comments_hybrid.py
│   └── evaluation/
├── analysis/
│   ├── export_ai_input.py
│   └── create_ai_sample.py
├── data/
│   ├── raw/          (non versionné — voir §14.1)
│   └── processed/
├── dbt/
│   ├── models/staging/
│   ├── models/intermediate/
│   ├── models/marts/
│   ├── tests/
│   └── dbt_project.yml
├── docs/
├── ingestion/
│   ├── load_raw.py
│   └── load_predictions.py
├── requirements.txt
├── run_pipeline.py
└── README.md
```

## 16. Run mensuel

Cible : environ 70 minutes en mois régulier — **encore au-dessus de l'heure visée par le brief**,
mais loin des ~302 min d'avant l'optimisation incrémentale (40 min de socle fixe estimé + 262 min
d'IA mesurés sur l'historique complet). `run_pipeline.py` (sans `--skip-ai`) a
été exécuté de bout en bout le 2026-09-18 ; les temps ci-dessous sont mesurés sur ce run, sauf
mention contraire :

| Étape                                    | Temps            | Nature |
| ------------------------------------------ | ---------------- | ------ |
| Préparation fichiers                        | 10 min           | Estimé — revue humaine, non mesurable par un run |
| Ingestion (`load_raw.py`)                   | **2,5 s mesurés**  | — |
| dbt run (1<sup>re</sup> passe, hors IA)     | **7 s mesurés**    | — |
| Export texte IA                             | **1,1 s mesuré**   | — |
| Inférence IA                                | ~45 min pour un mois type (~470 nouveaux commentaires, débit de 5,55 s/commentaire mesuré sur un échantillon de 120) ; **~262 min pour le tout premier run** — voir `docs/ai_documentation.ipynb` §8 | Mesuré et extrapolé |
| Rechargement prédictions                    | **2,3 s mesurés**  | — |
| dbt run (2<sup>e</sup> passe, complet)      | **13,8 s mesurés** | — |
| dbt test                                    | **10,2 s mesurés** | — |
| Contrôles qualité                            | 10 min           | Estimé — revue humaine |
| Dashboard                                    | 5 min            | Estimé — revue humaine |

Constat : dbt/DuckDB ne coûtent quasiment rien (~35 s cumulées, mesurées) — tout le temps du
cycle mensuel vient de l'IA (~45 min) et de la revue humaine (25 min, non compressible).
`classify_comments_hybrid.py` est incrémental : il ne classe que les `comment_id` absents de
`ai/evaluation/social_comments_predictions_v2_full.csv` (validé deux fois : retrait de 15 puis de
10 commentaires, relance, résultats bit-à-bit identiques aux prédictions d'origine). Piste
restante pour repasser sous l'heure : réduire `max_new_tokens` ou augmenter `BATCH_SIZE` côté
modèle — non implémenté.

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
