{{ config(materialized='table') }}

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
        measurement_profile
    FROM {{ ref('mart_decision_15m') }}

),

recommendation AS (

    SELECT
        channel,

        CASE channel
            WHEN 'Meta' THEN 5000000
            WHEN 'TikTok' THEN 4000000
            WHEN 'Google' THEN 2500000
            WHEN 'Radio' THEN 1500000
            WHEN 'Influenceurs' THEN 1000000
            WHEN 'Activation terrain' THEN 1000000
            ELSE 0
        END AS proposed_budget_fcfa,

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

    r.proposed_budget_fcfa / 15000000.0
        AS proposed_share,

    r.allocation_rationale,
    r.test_condition

FROM decision AS d
JOIN recommendation AS r
    ON d.channel = r.channel