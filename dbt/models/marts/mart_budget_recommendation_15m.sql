{{ config(materialized='table') }}

-- ======================================================================
-- Allocation des 15 M FCFA — calculée, pas fixée en dur.
--
-- Principe : chaque canal reçoit un socle fixe pour financer son
-- instrumentation (même les canaux les moins mesurés), puis le reliquat
-- est réparti au prorata d'un score = part de dépense observée x bonus
-- de qualité d'evidence. Cette allocation recalcule donc différemment
-- si les données du mois prochain changent (spend_share, evidence_quality) ;
-- elle ne prétend pas mesurer un ROI causal par canal — c'est un budget
-- de test pondéré par ce qu'on peut honnêtement observer aujourd'hui.
-- ======================================================================

WITH decision AS (

    SELECT
        channel,
        campaign_spend_fcfa,
        planned_budget_fcfa,
        invoiced_fcfa,
        spend_share,
        planned_share,
        spend_vs_plan_ratio,
        impressions,
        clicks,
        cpc_fcfa,
        cpm_fcfa,
        data_quality_status,
        evidence_quality,
        measurement_profile,
        observed_spend_share
    FROM {{ ref('mart_decision_15m') }}

),

-- ----------------------------------------------------------------------
-- Score = part de dépense observée x bonus lié à la qualité d'evidence.
-- Le bonus récompense la robustesse des données disponibles pour un
-- canal (evidence_quality, déjà calculée dans mart_decision_15m à partir
-- de la complétude des données, pas de la performance commerciale) —
-- il ne récompense jamais un CPC/CPM plus bas, ce qui reviendrait à
-- confondre coût média et efficacité commerciale.
-- ----------------------------------------------------------------------
scored AS (

    SELECT
        channel,

        COALESCE(observed_spend_share, 0)
        * CASE evidence_quality
            WHEN 'high' THEN 1.5
            WHEN 'medium' THEN 1.3
            ELSE 1.0
        END AS raw_score

    FROM decision

),

normalized AS (

    SELECT
        channel,
        raw_score,

        CASE
            WHEN SUM(raw_score) OVER () > 0
                THEN raw_score / SUM(raw_score) OVER ()
            ELSE 1.0 / COUNT(*) OVER ()
        END AS score_share

    FROM scored

),

-- ----------------------------------------------------------------------
-- Budget total : 15 M FCFA. Socle fixe de 1 M FCFA par canal pour
-- financer l'instrumentation même des canaux les moins mesurés
-- (radio, influenceurs, activation terrain) ; le reliquat est réparti
-- au prorata du score ci-dessus.
-- ----------------------------------------------------------------------
budget_params AS (

    SELECT
        15000000.0 AS total_budget_fcfa,
        1000000.0 AS floor_per_channel_fcfa,
        (SELECT COUNT(*) FROM decision) AS n_channels

),

allocated AS (

    SELECT
        n.channel,
        n.score_share,

        bp.floor_per_channel_fcfa
        + n.score_share
          * (bp.total_budget_fcfa - bp.floor_per_channel_fcfa * bp.n_channels)
            AS raw_budget_fcfa

    FROM normalized AS n
    CROSS JOIN budget_params AS bp

),

-- Arrondi à 50 000 FCFA pour un budget lisible côté client ; le résidu
-- d'arrondi est absorbé par le canal au budget calculé le plus élevé
-- pour que le total retombe exactement sur 15 000 000 FCFA.
rounded AS (

    SELECT
        channel,
        raw_budget_fcfa,
        ROUND(raw_budget_fcfa / 50000.0) * 50000.0 AS rounded_budget_fcfa

    FROM allocated

),

reconciled AS (

    SELECT
        channel,
        raw_budget_fcfa,
        rounded_budget_fcfa

        + CASE
            WHEN raw_budget_fcfa = MAX(raw_budget_fcfa) OVER ()
                THEN (SELECT total_budget_fcfa FROM budget_params)
                     - SUM(rounded_budget_fcfa) OVER ()
            ELSE 0
        END AS proposed_budget_fcfa

    FROM rounded

),

recommendation AS (

    SELECT
        channel,

        CASE channel
            WHEN 'Meta' THEN
                'Mesure digitale disponible ; dépense historique élevée ; allocation à tester sans conclure à une causalité sur les ventes.'
            WHEN 'TikTok' THEN
                'Volume digital mesurable et dépense proche du plan ; allocation de test, sans assimiler CPC à performance commerciale.'
            WHEN 'Google' THEN
                'Mesure des clics disponible et dépense proche du plan ; allocation de test sur un canal digital distinct.'
            WHEN 'Radio' THEN
                'Canal historiquement planifié et facturé, mais mesure média limitée ; allocation volontairement limitée avec instrumentation à renforcer.'
            WHEN 'Influenceurs' THEN
                'Présence dans le plan et dépenses observées, mais mesure limitée ; allocation de test avec dispositif de suivi.'
            WHEN 'Activation terrain' THEN
                'Le plan indique une dépense facturée alors que l''export campagne indique 0 ; allocation conditionnée à une meilleure réconciliation.'
            ELSE
                'Canal non retenu dans la proposition.'
        END AS allocation_rationale,

        CASE channel
            WHEN 'Meta' THEN
                'Suivre impressions, clics et conversion mesurable.'
            WHEN 'TikTok' THEN
                'Suivre impressions, clics et conversion mesurable.'
            WHEN 'Google' THEN
                'Suivre clics et conversion mesurable.'
            WHEN 'Radio' THEN
                'Ajouter code, numéro ou mécanisme de suivi dédié.'
            WHEN 'Influenceurs' THEN
                'Ajouter lien, code ou mécanisme de suivi dédié.'
            WHEN 'Activation terrain' THEN
                'Réconcilier facturation et dépenses campagne avant extrapolation.'
            ELSE
                'Définir un mécanisme de mesure.'
        END AS test_condition

    FROM decision

)

SELECT
    d.channel,

    d.campaign_spend_fcfa,
    d.planned_budget_fcfa,
    d.invoiced_fcfa,

    d.spend_share,
    d.planned_share,
    d.spend_vs_plan_ratio,

    d.impressions,
    d.clicks,
    d.cpc_fcfa,
    d.cpm_fcfa,

    d.data_quality_status,
    d.evidence_quality,
    d.measurement_profile,

    r.proposed_budget_fcfa,

    r.proposed_budget_fcfa / (SELECT total_budget_fcfa FROM budget_params)
        AS proposed_share,

    rec.allocation_rationale,
    rec.test_condition

FROM decision AS d
JOIN reconciled AS r
    ON d.channel = r.channel
JOIN recommendation AS rec
    ON d.channel = rec.channel
