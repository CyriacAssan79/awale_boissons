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

Chaque mois, ces réponses sont aussi rassemblées dans un **rapport mensuel** rédigé en français courant (voir 7 bis).

## 3. Architecture

```
RAW → STAGING → INTERMEDIATE → MARTS → DECISION → DASHBOARD
```

- **RAW** : Campaign Spend / Media Plan / POS Sales / Social Comments / WhatsApp Orders
- **STAGING** : nettoyage / déduplication / normalisation / quality flags
- **INTERMEDIATE** : réconciliation / calendrier / parsing / enrichissement
- **MARTS** : Marketing / Sales / WhatsApp / Social / Decision
- **AI + Decision Layer** : classification des commentaires (Customer Voice), rapport mensuel et questions en français sur les données (Ask the Data)
- **Streamlit Dashboard** : 7 pages regroupées par rubrique dans la barre latérale, dont le rapport mensuel et Ask the Data

## 4. Stack technique

Python 3.13 ou 3.14 (versions épinglées dans `requirements.txt`) · pandas · DuckDB · dbt Core + dbt-duckdb · openpyxl · modèles locaux Qwen2.5 (0.5B pour les commentaires, 1.5B pour le rapport et l'interprétation des questions libres d'Ask the Data) + règles hybrides · Streamlit · Plotly · dbt tests.

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

Les commentaires sont enrichis avec `language`, `sentiment`, `theme`, `product` et `is_spam`. La version en production (**V4**, 29/09/2026) combine des règles déterministes et **Qwen/Qwen2.5-0.5B-Instruct**, appelé pour ~13 % des commentaires (ceux que les règles ne tranchent pas). Le benchmark humain compte **108 commentaires** : les 50 d'origine et 58 cas que les règles envoient au modèle. Ces annotations servent à l'évaluation et ne sont pas présentées comme un jeu de fine-tuning.

**Évaluation V4 (108 commentaires annotés) :**

| Dimension       | Réponse constante | V4 — 50 d'origine | V4 — 58 cas « modèle » | V4 — total 108 |
| --------------- | ----------------- | ----------------- | ---------------------- | -------------- |
| Language        | 69 %              | 98 %              | 98 %                   | 98 %           |
| Sentiment       | 38 %              | 100 %             | 91 %                   | 95 %           |
| Theme           | 28 %              | 96 %              | 84 %                   | 90 %           |
| Product         | 44 %              | 98 %              | 97 %                   | 97 %           |
| Spam            | 97 %              | 100 %             | 100 %                  | 100 %          |
| Exact agreement | —                 | 94 %              | 78 %                   | 85 %           |

**À lire avec les taux de référence.** Sur les 50 commentaires d'origine, les règles tranchent presque tout : ce score mesure surtout les règles. Les 58 cas « modèle » mesurent la partie difficile, où se concentrent les erreurs (sentiment et thème). Le spam ne se juge pas sur ce score : une réponse constante « jamais spam » donne déjà 97 %. Les versions précédentes (V1 : 8 % d'accord exact, V2 hybride : 14 %, sur 50 commentaires) et le détail des erreurs sont dans `docs/ai_documentation.ipynb` 5.

## 7 bis. IA — Rapport mensuel

La page **Rapport IA** du dashboard (et la commande `python -m ai.reporting.generate_report`) produit le bilan d'un mois : synthèse, ventes, dépenses marketing, voix du client, produits, commandes WhatsApp, points d'attention, points positifs et conclusion.

```
marts DuckDB → query_marts.py (brief chiffré) → build_deterministic_report.py (sections chiffrées)
                                             → constats qualitatifs → Qwen2.5-1.5B (synthèse + conclusion) → contrôles → rapport
```

- **Les chiffres ne passent jamais par le modèle.** `ai/reporting/query_marts.py` calcule tout le brief en SQL/Python ; `build_deterministic_report.py` écrit les sections chiffrées.
- **Le modèle `Qwen/Qwen2.5-1.5B-Instruct` ne rédige que la synthèse et la conclusion**, à partir de constats qualitatifs sans aucun chiffre (« Le chiffre d'affaires est en baisse par rapport à la période précédente. », « Meta représente la plus grande part des dépenses marketing. », « Le bissap en format un litre… »). Les noms de canal et de produit sont transmis en toutes lettres : sans eux, le modèle écrivait « le canal » ou « le produit » et la phrase semblait incomplète.
- **Sa sortie est contrôlée** (`validate_narrative`) avant affichage. Elle est rejetée si elle contient :
  - un chiffre ou un `%` ;
  - une formulation causale (« grâce à », « à cause de »…) ;
  - une mention de l'enveloppe de 15 M FCFA ;
  - une phrase sans article (style télégraphique) ;
  - un sens d'évolution du CA contraire au calcul (par exemple « inférieur » alors que le mois précédent n'existe pas).

  Une sortie rejetée est remplacée par une **synthèse de secours** qui reprend les constats tels quels. Une faute d'accord récurrente du modèle (« certains commandes ») est corrigée automatiquement.
- **Ce que le contrôle ne garantit pas** : un modèle de cette taille peut encore reformuler un constat de façon maladroite. Relire la synthèse et la conclusion avant diffusion.
- Les rapports sont enregistrés dans `outputs/reports/rapport_AAAA_MM.md` et téléchargeables depuis le dashboard.

**Durées mesurées (CPU, 01/10/2026)** :

- rapport complet : **jusqu'à 10 min par mois**, chargement du modèle compris ;
- détail sur une machine où le modèle est déjà en cache : chargement ~12 s (~70–80 s à froid, une fois par session du dashboard), génération ~1 min 50 à 2 min 10 (avril, mai et juin) ;
- sans synthèse IA (interrupteur désactivé) : instantané.

Avril, mai et juin passent les contrôles. Janvier bascule sur la synthèse de secours : le modèle y invente une évolution du CA alors que décembre 2025 n'est pas dans les données.

## 7 ter. IA — Ask the Data

La page **Demander à l'IA** du dashboard répond en français à une question sur les ventes, les dépenses marketing, le mix produit ou les commentaires clients (« Le bissap a rapporté combien en mai ? », « Sur quoi avons-nous le plus dépensé ? », « Compare Meta et TikTok en juin 2026 », « Quelle plateforme génère le plus de retours négatifs ? »).

```
question → règles (question_parser) ──────────────┐
             └─ aucune métrique reconnue → Qwen2.5-1.5B (fiche JSON) → contrôles ─┤
                                                                                 → intention → SQL (semantic_layer.yml) → DuckDB → phrase rédigée en Python
```

- **Les règles comprennent la grande majorité des questions**, instantanément : métriques (CA net, dépenses marketing, mix produit, et pour la voix du client : répartition du sentiment, commentaires positifs, négatifs et neutres, parts de positifs et de négatifs, volume, commentaires exploitables, spam, thèmes), découpages (mois, canal, produit, format, plateforme), filtres (mois avec ou sans année, « depuis mars », « ces 3 derniers mois », « le mois dernier », « ce mois-ci », canaux, produits, plateformes Facebook / Instagram / TikTok), comparaisons (« le bissap et le gingembre ») et classements (« le canal qui dépense le plus »).
- **Le SQL est construit uniquement à partir de `docs/semantic_layer.yml`** : modèle, expression et découpages autorisés de chaque métrique. Mois, canaux et produits sont vérifiés sur des listes fermées avant d'entrer dans la requête (tests d'injection dans `tests/ask_data/`).
- **La réponse est rédigée par des phrases modèles en Python** (`ai/ask_data/narrative.py`), pas par le modèle : total, premier et dernier, part du total, tendance sur la période, comparaison au mois précédent. Elle décrit ce qui s'est passé, jamais pourquoi.
- **Refus volontaires** : questions causales (« quel canal a causé… »), prévisions, métriques non définies (ROI, coût par litre…) et découpages indisponibles (dépenses par produit) reçoivent un message clair avec une question à essayer. Ces refus ne sont jamais confiés au modèle.
- **Qwen n'intervient que si les règles ne reconnaissent aucune métrique** (interrupteur « Comprendre les questions libres (IA) », activé par défaut). Il ne remplit qu'une fiche JSON d'intention : métrique, découpages, classement, période récente, hors sujet. **Les produits, canaux, mois et années sont toujours lus dans la question par les règles** : lors des essais, le modèle ajoutait un canal absent de la question (« Meta ») ou lisait « depuis mars » comme « en mars ». Un classement proposé n'est gardé que si la question contient un mot de comparaison. Chaque valeur est vérifiée ; une fiche invalide garde le refus d'origine. Le modèle n'écrit jamais de SQL et ne voit aucune donnée.
- **L'interprétation retenue par l'IA est affichée** au-dessus de la réponse, pour que l'utilisateur puisse reformuler.

**Durées mesurées (CPU, 02/10/2026, 8 questions libres)** : questions comprises par les règles, instantanées ; questions confiées à Qwen, **25 à 38 s** chacune ; premier appel de la session, ~50 s de plus pour charger le modèle (partagé avec le rapport mensuel, chargé une seule fois).

Code : `ai/ask_data/` (point d'entrée `service.run_ask_data`). Tests : `tests/ask_data/` (247 tests, modèle simulé, sans téléchargement).

**Voix du client** (ajout du 03/10/2026) : les questions sur les commentaires utilisent `mart_social_monthly` via les métriques de `docs/semantic_layer.yml` (section « Voix du client »). La répartition du sentiment et les thèmes sont déclarés avec des `composantes` (positifs, neutres, négatifs ; goût, prix…) calculées dans la même requête. Pour une question sur les commentaires, Facebook, Instagram et TikTok sont des plateformes (« Meta » = Facebook + Instagram) ; Google, la radio ou les influenceurs sont refusés, faute de commentaires. Une question de synthèse (« résume-moi… », « qu'est-ce qui ressort… ») ajoute les thèmes au sentiment ; « les avis négatifs augmentent-ils ? » donne le nombre et la part, car le nombre dépend du volume du mois. Les réponses sur le sentiment rappellent que le classement est automatique.

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

| Indicateur                                    | Valeur                                              |
| --------------------------------------------- | --------------------------------------------------- |
| Commandes                                     | 1 066 (624 livrées, 296 annulées, 146 en cours)     |
| Clients identifiés (téléphone normalisé)      | 389, dont 313 avec au moins une commande livrée     |
| Taux de réachat livraison                     | **57,5 %** (180 clients sur 313, commandes livrées) |
| Unités commandées (texte parsé)               | 4 399                                               |
| Montants manquants                            | 131 commandes (dont 82 livrées)                     |
| Montants invraisemblables, exclus             | 23 commandes (au-dessus de 100 000 FCFA)            |
| Montant connu et plausible, commandes livrées | 3 135 400 FCFA                                      |

Le montant des commandes livrées **n'est pas un revenu livraison** : 96 des 624 commandes livrées (15,4 %) n'ont pas de montant exploitable (82 sans montant, 14 avec un montant invraisemblable), et aucun total n'est extrapolé.

Le taux de réachat ne compte que les commandes livrées : une commande annulée ou en cours n'est pas un achat (l'ancienne définition, tous statuts confondus, donnait 74,3 %). Les montants invraisemblables (de 1,4 M à 11,55 M FCFA, soit ×111 le plus grand montant plausible) ressemblent à une erreur d'unité ×1 000, hypothèse non appliquée et à confirmer avec Kômian.

## 11. Allocation proposée — 15 M FCFA

| Canal              | Budget décidé   | Part      | Calcul de référence |
| ------------------ | --------------- | --------- | ------------------- |
| Meta               | 5,50 M FCFA     | 36,7 %    | 5,55 M FCFA         |
| TikTok             | 3,00 M FCFA     | 20,0 %    | 3,10 M FCFA         |
| Radio              | 2,00 M FCFA     | 13,3 %    | 2,00 M FCFA         |
| Google             | 2,00 M FCFA     | 13,3 %    | 1,90 M FCFA         |
| Influenceurs       | 1,50 M FCFA     | 10,0 %    | 1,45 M FCFA         |
| Activation terrain | 1,00 M FCFA     | 6,7 %     | 1,00 M FCFA         |
| **Total**          | **15,0 M FCFA** | **100 %** | **15,0 M FCFA**     |

**Budget décidé (03/10/2026).** Les montants retenus sont le calcul de référence arrondi par tranches de 0,5 M FCFA. Ils sont fixés dans `dbt/dbt_project.yml` (`test_budget_allocation_fcfa`) et deviennent le budget proposé de `mart_budget_recommendation_15m` ; le calcul reste à côté (`computed_budget_fcfa`, colonne « Calcul de référence » du dashboard) pour que l'écart reste visible. Un test dbt vérifie que le total vaut toujours 15 M FCFA, un autre que chaque canal de la variable existe. Vider la variable (`{}`) fait revenir au budget calculé à chaque run.

**Calcul de référence** (`dbt/models/marts/mart_budget_recommendation_15m.sql`) : un socle de 1 M FCFA par canal
finance l'instrumentation même des canaux les moins mesurés, puis le reliquat (9 M FCFA) est réparti
au prorata de `part de dépense observée × bonus de qualité d'evidence` (evidence_quality vient de la
complétude des données, pas de la performance commerciale). Ce calcul change si les données du mois
prochain changent — ce n'est pas un classement causal. Le budget décidé, lui, ne bouge pas tant que la
variable n'est pas modifiée : le comparer au calcul à chaque cycle. Le budget total et le socle par canal sont des paramètres (`total_test_budget_fcfa`, `test_budget_floor_per_channel_fcfa` dans `dbt/dbt_project.yml`).

**Limite de la base de calcul.** La répartition suit la dépense observée dans l'export campagne, qui sous-représente les canaux saisis à la main : la radio pèse 12,6 % de l'export contre 26,2 % du facturé (plan média), les influenceurs 5,7 % contre 8,3 %, l'activation terrain 0 % contre 13,8 %. L'allocation hérite de ce biais. Le choix de la base (dépense observée ou facturé) est à trancher avec Kômian : voir `docs/business_problem.ipynb` 6 bis.

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
- Ask the Data couvre le CA net, les dépenses marketing, le mix produit et les commentaires clients ; le sentiment n'est pas disponible par produit (le mart ne croise pas sentiment et produit). « Le produit le plus vendu » est classé par chiffre d'affaires, pas par unités (`unites_vendues` n'est pas encore prise en charge). Le CA par canal n'existe pas dans la couche sémantique (`ca_net` ne se découpe que par mois). Un mois sans année (« en mai ») désigne le plus récent présent dans les données, « le mois dernier » le dernier mois disponible ; la réponse annonce toujours le mois utilisé. Les comparaisons au mois précédent ne signalent pas encore un mois incomplet (avril).
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
depuis Hugging Face, puis relu depuis le cache local. Le premier rapport mensuel avec synthèse IA,
ou la première question libre posée dans Ask the Data, télécharge de même `Qwen/Qwen2.5-1.5B-Instruct` (~2,9 Go).

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

Le dashboard s'organise en 7 pages, regroupées par rubrique dans la barre latérale :

| Rubrique | Page | Contenu |
| --- | --- | --- |
| Tableau de bord | Vue d'ensemble | Indicateurs globaux, avertissements de couverture, cartes d'accès aux autres pages |
| Tableau de bord | Marketing | Dépense de l'export, budget planifié et facturé ; dépenses par canal comparées au plan |
| Tableau de bord | Ventes | CA net, couverture des données, mix produit |
| Tableau de bord | Voix client | Sentiment, thèmes, produits mentionnés, commandes WhatsApp |
| Décision | Recommandation | Répartition proposée des 15 M FCFA et cadre de test |
| Intelligence artificielle | Rapport IA | Rapport mensuel : créer, mettre à jour, lire et télécharger |
| Intelligence artificielle | Demander à l'IA | Questions en français sur les ventes, les dépenses et les commentaires clients (Ask the Data, voir 7 ter) |

Le filtre de période (barre latérale, sous la navigation) s'applique aux pages Vue d'ensemble, Ventes et Voix client, et se conserve d'une page à l'autre.

**Identité visuelle.** Le dashboard suit le design system « Ivorian Terroir & Analytic Rigor », issu de maquettes Google Stitch et adapté au desktop : fond écru, cartes à filet fin, bissap (`#7A123A`) en couleur principale, Epilogue pour les titres, Hanken Grotesk pour le texte, JetBrains Mono pour les chiffres. Couleurs et polices sont dans `.streamlit/config.toml` ; les composants (bandeau d'accueil, cartes de navigation, bandeaux de qualité des données, barres par canal, bulles de conversation) dans `app/theme.py`. Les maquettes contenaient des chiffres d'exemple inventés : le dashboard n'affiche que les données de la base.

Le rapport mensuel peut aussi être produit en ligne de commande :

```bash
python -m ai.reporting.generate_report --year 2026 --month 6 --save   # → outputs/reports/rapport_2026_06.md
```

**Validation actuelle :** 26/26 modèles dbt et 96/96 tests dbt, avec 0 erreur et 0 warning (avant l'ajout, le 03/10/2026, du budget décidé et du test `mart_budget_recommendation_15m_decided_channels`, à rejouer avec `dbt run` puis `dbt test`) ; `pytest` : 335/335 tests, dont 247 pour Ask the Data (03/10/2026, voir 14.5).

Le chargement (`ingestion/load_raw.py`) valide les cinq feuilles et leurs colonnes **avant** d'écrire : une feuille absente, vide ou incomplète interrompt le run avec un message clair, sans modifier la base.

### 14.4 Reprise après interruption de l'IA

`ai/classify_comments_hybrid.py` sauvegarde ses prédictions toutes les 5 batches (~2 minutes de calcul), de
façon atomique. Un plantage ou un Ctrl+C ne fait perdre que le travail depuis la dernière sauvegarde :
relancer `python run_pipeline.py` reprend exactement où le run s'est arrêté, car seuls les `comment_id`
absents du fichier de prédictions sont classés. Un commentaire dont la sortie du modèle est illisible est
retenté seul, puis signalé ; il n'est **pas** enregistré (rien n'est deviné), le script se termine en erreur
et il sera retenté au lancement suivant. Les réponses hors vocabulaire ramenées à une valeur par défaut sont
comptées et affichées (`[ATTENTION]`).

Le prompt est un fichier versionné, `ai/prompts/comment_classifier_v4_hybrid.txt` (règles v4.2). Le modifier passe par un
nouveau fichier (v5, …) et un nouveau passage du benchmark humain.

### 14.5 Tests automatiques

```bash
pytest
```

Cinq familles : reprise, garde-fou et prompt de l'IA (modèle simulé, sans téléchargement) ;
validation du chargement Excel (feuille absente, vide ou incomplète) ; couche sémantique (chaque
expression de `docs/semantic_layer.yml` est exécutée contre la base et ses définitions sont comparées
mot pour mot à celles de `docs/business_problem.ipynb`) ; Ask the Data (`tests/ask_data/` :
formulations libres, refus volontaires, SQL et injections, phrases rédigées, interprétation par le
modèle simulé et repli sur les règles). Les tests qui lisent la base sont **ignorés,
non validés**, si `data/awale.duckdb` est absente ou verrouillée (fermer l'aperçu DuckDB de l'éditeur).

### 14.6 Ajouter un nouveau mois

Ajouter les lignes du mois aux feuilles du même fichier Excel, puis relancer `python run_pipeline.py`. Les mois du plan média, les mois de campagne et le calendrier des ventes sont lus dans les données : aucune date n'est écrite en dur. Un mois de ventes reçu incomplet apparaît avec ses jours manquants (et l'avertissement du dashboard) au lieu de passer pour un mois complet.

Les paramètres métier se modifient dans `dbt/dbt_project.yml`, section `vars` : taux EUR→FCFA (`eur_to_fcfa_rate`), budget de test et socle par canal, budget décidé par canal (`test_budget_allocation_fcfa`, voir 11), seuil de montant WhatsApp invraisemblable (`whatsapp_max_plausible_amount_fcfa`).

## 15. Structure du repository

```
awale_boissons/
├── .streamlit/
│   └── config.toml   (thème du dashboard : couleurs et polices)
├── app/
│   ├── app.py        (point d'entrée : navigation par rubrique dans la barre latérale)
│   ├── common.py     (connexion DuckDB, formats, filtre de période, chargement du modèle Qwen partagé)
│   ├── theme.py      (identité visuelle : palette, CSS, composants, graphiques)
│   └── views/        (une page par fichier : overview, marketing, sales,
│                      customers, recommendation, report, ask_data)
├── ai/
│   ├── classify_comments_hybrid.py
│   ├── prompts/      (prompts versionnés)
│   ├── evaluation/
│   ├── reporting/    (rapport mensuel : query_marts, build_deterministic_report,
│   │                  generate_report, prompts/)
│   └── ask_data/     (Ask the Data : question_parser, llm_parser, sql_builder,
│                      executor, narrative, service…)
├── analysis/
│   ├── export_ai_input.py
│   └── create_ai_sample.py
├── data/
│   ├── raw/          (non versionné — voir 14.1)
│   └── processed/
├── dbt/
│   ├── models/staging/
│   ├── models/intermediate/
│   ├── models/marts/
│   ├── tests/
│   └── dbt_project.yml
├── docs/             (business_problem, data_quality, ai_documentation,
│                      dictionnaire_de_donnees, Client_Note, Runbook_Mensuel,
│                      note_adoption, semantic_layer.yml)
├── ingestion/
│   ├── load_raw.py
│   └── load_predictions.py
├── outputs/
│   └── reports/      (rapports mensuels générés : rapport_AAAA_MM.md)
├── pytest.ini
├── requirements.txt
├── requirements-dev.txt
├── run_pipeline.py
├── tests/            (pytest : IA, chargement, couche sémantique, ask_data/)
├── version.ipynb
└── README.md
```

## 16. Run mensuel

Durées mesurées le 01/10/2026 sur un cycle complet (pipeline, classification des commentaires,
rapport mensuel) ; les étapes humaines sont estimées.

| Étape | Temps | Nature |
| --- | --- | --- |
| Préparation fichiers | 10 min | Estimé — revue humaine |
| Pipeline hors classification (`run_pipeline.py` : ingestion, `dbt run` ×2, export, rechargement, `dbt test`) | **2 à 3 min** | Mesuré, sans supervision |
| Classification des commentaires (`classify_comments_hybrid.py`) | **~40 min** | Mesuré, sans supervision |
| Contrôles qualité | 10 min | Estimé — revue humaine |
| Dashboard | 5 min | Estimé — revue humaine |
| Rapport mensuel (synthèse IA) | **jusqu'à 10 min**, chargement du modèle compris — voir 7 bis | Mesuré, sans supervision |
| Relecture du rapport | 5 min | Estimé — revue humaine |
| **Total** | **≈ 1 h 25** (dont 30 min de présence active) | |

**Le cycle complet dépasse l'heure visée par le brief.** La classification des commentaires en
représente près de la moitié : 40 min correspondent au reclassement complet de l'historique
(2 831 commentaires, déjà mesuré à ~40 min le 29/09/2026). Lorsqu'elle ne classe que les
commentaires du mois, elle a été mesurée à 7,2 min (juin, 453 nouveaux commentaires, 29/09/2026) :
le cycle tombe alors à **≈ 50 min**. Le reclassement complet a lieu au premier lancement et après
chaque changement de règles, de prompt ou de modèle.

`classify_comments_hybrid.py` est incrémental : il ne classe que les `comment_id` absents de
`ai/evaluation/social_comments_predictions_v2_full.csv` (validé deux fois : retrait de 15 puis de
10 commentaires, relance, résultats bit-à-bit identiques aux prédictions d'origine). Chaque ligne
porte une colonne `classifier_version` (règles + prompt + modèle) : après un changement de
version, les anciennes lignes sont sauvegardées dans un fichier `.backup_<date>.csv` puis reclassées.

Avant un run complet :

```bash
python ai/classify_comments_hybrid.py --test 10   # 10 commentaires annotés, détail règle/Qwen/humain
python ai/classify_comments_hybrid.py --bench     # tout le benchmark (108 commentaires annotés) → model_predictions_hybrid.csv
python ai/evaluation/evaluate_classifier.py --model hybrid
python ai/classify_comments_hybrid.py             # run complet (appelé par run_pipeline.py)
```

`ai/evaluation/labeled_sample_draft.csv` contient des commentaires que les règles ne tranchent
pas (ils partent au modèle), avec des labels **proposés**. Après relecture humaine (colonne
`validated` = `oui`), les fusionner dans le benchmark :

```bash
python ai/evaluation/merge_validated_draft.py            # aperçu
python ai/evaluation/merge_validated_draft.py --apply    # ajoute les lignes validées à labeled_sample.csv
```

Pistes pour repasser sous l'heure lors d'un reclassement complet : réduire `max_new_tokens` ou
augmenter `BATCH_SIZE` côté modèle de classification — non implémenté.

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
- Dashboard Streamlit (7 pages, navigation par rubrique dans la barre latérale)
- Rapport mensuel IA (page du dashboard et `ai/reporting/`, rapports dans `outputs/reports/`)
- Ask the Data : questions en français sur les données (page « Demander à l'IA » et `ai/ask_data/`)
- Allocation 15 M FCFA
- Client Note (recommandation, niveau de confiance, mesures à 90 jours)
- Runbook mensuel
- Note d'adoption interne (`docs/note_adoption.ipynb`)
- Couche sémantique (`docs/semantic_layer.yml`) et tests automatiques (`tests/`)
- Prompt de classification versionné (`ai/prompts/`)
