WITH base_municipios AS (
    SELECT
        co_ibge AS sk_municipality,
        no_municipio,
        co_uf,
        no_uf,
        no_regiao,
        no_macrorregiao_saude,
        no_regiao_saude,
        populacao_estimada
    FROM "healthdata_dw"."dw_gold"."vw_stg_municipios"
),
missing_from_hospitais AS (
    SELECT DISTINCT
        h.co_ibge AS sk_municipality,
        h.no_municipio,
        h.sg_uf AS co_uf,
        h.sg_uf AS no_uf,
        h.no_regiao,
        'NÃO INFORMADO' AS no_macrorregiao_saude,
        'NÃO INFORMADO' AS no_regiao_saude,
        0 AS populacao_estimada
    FROM "healthdata_dw"."dw_gold"."vw_stg_hospitais_leitos" h
    LEFT JOIN base_municipios b ON h.co_ibge = b.sk_municipality
    WHERE b.sk_municipality IS NULL
),
missing_from_other_facts AS (
    SELECT DISTINCT
        f.co_ibge AS sk_municipality,
        'MUNICÍPIO IBGE ' || f.co_ibge AS no_municipio,
        SUBSTRING(f.co_ibge, 1, 2) AS co_uf,
        'UF ' || SUBSTRING(f.co_ibge, 1, 2) AS no_uf,
        'BRASIL' AS no_regiao,
        'NÃO INFORMADO' AS no_macrorregiao_saude,
        'NÃO INFORMADO' AS no_regiao_saude,
        0 AS populacao_estimada
    FROM (
        SELECT co_ibge FROM "healthdata_dw"."dw_gold"."vw_stg_estabelecimentos"
        UNION
        SELECT co_ibge FROM "healthdata_dw"."dw_gold"."vw_stg_leitos_historico"
        UNION
        SELECT co_ibge FROM "healthdata_dw"."dw_gold"."vw_stg_sih_producao"
    ) f
    LEFT JOIN base_municipios b ON f.co_ibge = b.sk_municipality
    LEFT JOIN missing_from_hospitais mh ON f.co_ibge = mh.sk_municipality
    WHERE b.sk_municipality IS NULL AND mh.sk_municipality IS NULL
),
unioned AS (
    SELECT * FROM base_municipios
    UNION ALL
    SELECT * FROM missing_from_hospitais
    UNION ALL
    SELECT * FROM missing_from_other_facts
),
deduped AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY sk_municipality ORDER BY populacao_estimada DESC) AS rn
    FROM unioned
)
SELECT
    sk_municipality,
    no_municipio,
    co_uf,
    no_uf,
    no_regiao,
    no_macrorregiao_saude,
    no_regiao_saude,
    populacao_estimada
FROM deduped
WHERE rn = 1