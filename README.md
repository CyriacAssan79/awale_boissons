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

Python 3.13 ou 3.14 (versions épinglées dans `requirements.txt`) · pandas · DuckDB · dbt Core + dbt-duckdb · openpyxl · modèle local + règles hybrides · Streamlit · Plotly · dbt tests.

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
- Identifiants de points de vente instables (4 magasins changent de `pos_id` le 1er mai), montants WhatsApp invraisemblables, quantités « Nx SKU », mois de ventes partiels

Le détail de chaque décision (constat, règle, conséquence sur les chiffres, point à confirmer) est dans `docs/data_quality.ipynb`.

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

**À lire avec les taux de référence.** Sur ces 50 commentaires, une réponse constante donnerait 72 % en langue, 54 % en sentiment, 22 % en thème, 42 % en produit et 94 % en spam. V1 n'égale que ces taux sur langue, sentiment et spam ; la version hybride progresse sur sentiment, thème et produit mais reste très en dessous en langue (22 % contre 72 %). L'échantillon ne compte que 3 spams. Le champ langue n'est pas utilisable en l'état et la détection de spam est à améliorer : le remplacement du modèle local est prévu (voir `docs/ai_documentation.ipynb` §5).

## 8. Customer Voice — janvier à juin 2026

**2 831 commentaires**, dont 513 détectés comme spam. **Hors spam (2 318)** : 1 186 positifs, 735 négatifs, 397 neutres.

Principaux thèmes (hors spam) :

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

## 10 bis. WhatsApp — livraison

| Indicateur | Valeur |
| --- | --- |
| Commandes | 1 066 (624 livrées, 296 annulées, 146 en cours) |
| Clients identifiés (téléphone normalisé) | 389, dont 313 avec au moins une commande livrée |
| Taux de réachat livraison | **57,5 %** (180 clients sur 313, commandes livrées) |
| Unités commandées (texte parsé) | 4 399 |
| Montants manquants | 131 commandes (dont 82 livrées) |
| Montants invraisemblables, exclus | 23 commandes (au-dessus de 100 000 FCFA) |
| Montant connu et plausible, commandes livrées | 3 135 400 FCFA |

Le montant des commandes livrées **n'est pas un revenu livraison** : 96 des 624 commandes livrées (15,4 %) n'ont pas de montant exploitable (82 sans montant, 14 avec un montant invraisemblable), et aucun total n'est extrapolé.

Le taux de réachat ne compte que les commandes livrées : une commande annulée ou en cours n'est pas un achat (l'ancienne définition, tous statuts confondus, donnait 74,3 %). Les montants invraisemblables (de 1,4 M à 11,55 M FCFA, soit ×111 le plus grand montant plausible) ressemblent à une erreur d'unité ×1 000, hypothèse non appliquée et à confirmer avec Kômian.

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
les données du mois prochain changent — ce n'est ni un classement causal, ni un montant figé. Le budget total et le socle par canal sont des paramètres (`total_test_budget_fcfa`, `test_budget_floor_per_channel_fcfa` dans `dbt/dbt_project.yml`).

**Limite de la base de calcul.** La répartition suit la dépense observée dans l'export campagne, qui sous-représente les canaux saisis à la main : la radio pèse 12,6 % de l'export contre 26,2 % du facturé (plan média), les influenceurs 5,7 % contre 8,3 %, l'activation terrain 0 % contre 13,8 %. L'allocation hérite de ce biais. Le choix de la base (dépense observée ou facturé) est à trancher avec Kômian : voir `docs/business_problem.ipynb` §6 bis.

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
- Le mix produit (`mart_product_mix_monthly`) couvre les points de vente ; la demande WhatsApp par produit est lue dans le texte des commandes, avec des formats parfois absents.
- Les 96 lignes POS identiques (toutes sur l'entrepôt `POS999`) sont conservées : si l'export contenait de vrais doublons, le CA net serait surévalué de 0,50 % (440 600 FCFA). À confirmer auprès du distributeur.
- Deux cas de points de vente ne sont pas fusionnés sans validation (`Avenue 16` / `Avenue 16 (nouveau)`, probablement un même magasin : 40 magasins au lieu de 41).
- Le "CA net observé" du dashboard est le CA des points de vente uniquement ; les commandes WhatsApp n'y sont pas incluses.
- Avec les versions de `requirements.txt` sur CPU, le vrai modèle a reproduit à l'identique les prédictions déjà enregistrées sur deux échantillons (12 et 24 commentaires), pas sur les 2 831 : un autre matériel ou d'autres versions peuvent produire des sorties légèrement différentes pour un même commentaire.

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
pip install -r requirements.txt        # cycle mensuel (pipeline, dashboard, IA locale)
pip install -r requirements-dev.txt    # en plus : tests, benchmark IA, notebooks
```

Toutes les versions sont **épinglées** (`==`) : ce sont celles installées et testées ensemble
(Python 3.13, environnement neuf créé depuis ces fichiers : `run_pipeline.py --skip-ai`, `dbt run`,
`dbt test`, dashboard, `pytest`, et modèle IA réel sur 24 commentaires). Pour en changer une, la modifier dans `requirements.txt`
puis rejouer `python run_pipeline.py --skip-ai` et `pytest`. Le pipeline mensuel n'a besoin
d'aucune clé API : `openai`, `tenacity` et `python-dotenv` ne servent qu'à la première version de
la classification (`ai/classify_comments.py`, non retenue) et sont dans `requirements-dev.txt`.

Première inférence IA : le modèle `Qwen/Qwen2.5-0.5B-Instruct` (~1 Go) est téléchargé une fois
depuis Hugging Face, puis relu depuis le cache local.

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

**Validation actuelle :** 26/26 modèles dbt et 96/96 tests dbt, avec 0 erreur et 0 warning ; `pytest` : 56/56 tests (voir §14.5).

Le chargement (`ingestion/load_raw.py`) valide les cinq feuilles et leurs colonnes **avant** d'écrire : une feuille absente, vide ou incomplète interrompt le run avec un message clair, sans modifier la base.

### 14.4 Reprise après interruption de l'IA

`ai/classify_comments_hybrid.py` sauvegarde ses prédictions toutes les 5 batches (~2 minutes de calcul), de
façon atomique. Un plantage ou un Ctrl+C ne fait perdre que le travail depuis la dernière sauvegarde :
relancer `python run_pipeline.py` reprend exactement où le run s'est arrêté, car seuls les `comment_id`
absents du fichier de prédictions sont classés. Un commentaire dont la sortie du modèle est illisible est
retenté seul, puis signalé ; il n'est **pas** enregistré (rien n'est deviné), le script se termine en erreur
et il sera retenté au lancement suivant. Les réponses hors vocabulaire ramenées à une valeur par défaut sont
comptées et affichées (`[ATTENTION]`).

Le prompt est un fichier versionné, `ai/prompts/comment_classifier_v2_hybrid.txt`. Le modifier passe par un
nouveau fichier (v3, …) et un nouveau passage du benchmark humain.

### 14.5 Tests automatiques

```bash
pytest
```

Quatre familles : reprise, garde-fou et prompt de l'IA (modèle simulé, sans téléchargement) ;
validation du chargement Excel (feuille absente, vide ou incomplète) ; couche sémantique (chaque
expression de `docs/semantic_layer.yml` est exécutée contre la base et ses définitions sont comparées
mot pour mot à celles de `docs/business_problem.ipynb`). Les tests qui lisent la base sont **ignorés,
non validés**, si `data/awale.duckdb` est absente ou verrouillée (fermer l'aperçu DuckDB de l'éditeur).

### 14.6 Ajouter un nouveau mois

Ajouter les lignes du mois aux feuilles du même fichier Excel, puis relancer `python run_pipeline.py`. Les mois du plan média, les mois de campagne et le calendrier des ventes sont lus dans les données : aucune date n'est écrite en dur. Un mois de ventes reçu incomplet apparaît avec ses jours manquants (et l'avertissement du dashboard) au lieu de passer pour un mois complet.

Les paramètres métier se modifient dans `dbt/dbt_project.yml`, section `vars` : taux EUR→FCFA (`eur_to_fcfa_rate`), budget de test et socle par canal, seuil de montant WhatsApp invraisemblable (`whatsapp_max_plausible_amount_fcfa`).

## 15. Structure du repository

```
awale_boissons/
├── .streamlit/
│   └── config.toml   (thème du dashboard)
├── app/
│   ├── app.py
│   └── theme.py      (palette, CSS, graphiques)
├── ai/
│   ├── classify_comments_hybrid.py
│   ├── prompts/      (prompts versionnés)
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
├── docs/             (business_problem, data_quality, ai_documentation,
│                      Dictionnaire_de_donnees, Client_Note, Runbook_Mensuel,
│                      Note_Adoption, semantic_layer.yml)
├── ingestion/
│   ├── load_raw.py
│   └── load_predictions.py
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt
├── run_pipeline.py
├── tests/            (pytest : IA, chargement, couche sémantique)
├── version.ipynb
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

Le détail figure dans `docs/Runbook_Mensuel.ipynb`.

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
- Client Note (recommandation, niveau de confiance, mesures à 90 jours)
- Runbook mensuel
- Note d'adoption interne (`docs/Note_Adoption.ipynb`)
- Couche sémantique (`docs/semantic_layer.yml`) et tests automatiques (`tests/`)
- Prompt de classification versionné (`ai/prompts/`)
