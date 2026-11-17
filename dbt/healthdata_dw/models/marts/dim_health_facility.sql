WITH cnes_base AS (
    SELECT
        co_cnes AS sk_facility,
        co_cnes,
        co_ibge AS fk_municipality,
        no_fantasia AS no_estabelecimento,
        no_razao_social,
        tp_gestao,
        COALESCE(ds_natureza_juridica, 'NÃO INFORMADO') AS ds_natureza_juridica,
        fl_atende_sus,
        fl_atendimento_hospitalar
    FROM {{ ref('vw_stg_estabelecimentos') }}
),
hospitais_snapshot AS (
    SELECT
        sk_hospital_natural AS sk_facility,
        SUBSTRING(sk_hospital_natural, 1, 7) AS co_cnes,
        co_ibge AS fk_municipality,
        no_hospital AS no_estabelecimento,
        COALESCE(no_razao_social, no_hospital) AS no_razao_social,
        COALESCE(tp_gestao, 'N/I') AS tp_gestao,
        COALESCE(ds_natureza_juridica, 'NÃO INFORMADO') AS ds_natureza_juridica,
        CASE WHEN qt_leitos_sus > 0 THEN 'SIM' ELSE 'NÃO' END AS fl_atende_sus,
        1 AS fl_atendimento_hospitalar
    FROM {{ ref('vw_stg_hospitais_leitos') }}
),
missing_from_facts AS (
    SELECT DISTINCT
        f.co_cnes AS sk_facility,
        f.co_cnes,
        f.co_ibge AS fk_municipality,
        f.no_fantasia AS no_estabelecimento,
        f.no_fantasia AS no_razao_social,
        'N/I' AS tp_gestao,
        COALESCE(f.ds_natureza_juridica, 'NÃO INFORMADO') AS ds_natureza_juridica,
        'SIM' AS fl_atende_sus,
        1 AS fl_atendimento_hospitalar
    FROM (
        SELECT co_cnes, co_ibge, 'ESTABELECIMENTO CNES ' || co_cnes AS no_fantasia, ds_natureza_juridica
        FROM {{ ref('vw_stg_leitos_historico') }}
        UNION
        SELECT co_cnes, co_ibge, no_fantasia, ds_natureza_juridica
        FROM {{ ref('vw_stg_sih_producao') }}
    ) f
    LEFT JOIN cnes_base c ON f.co_cnes = c.sk_facility
    WHERE c.sk_facility IS NULL
),
all_facilities AS (
    SELECT * FROM cnes_base
    UNION ALL
    SELECT * FROM hospitais_snapshot
    UNION ALL
    SELECT * FROM missing_from_facts
),
deduped AS (
    SELECT
        *,
        ROW_NUMBER() OVER (PARTITION BY sk_facility ORDER BY no_estabelecimento) AS rn
    FROM all_facilities
)
SELECT
    sk_facility,
    co_cnes,
    fk_municipality,
    no_estabelecimento,
    no_razao_social,
    tp_gestao,
    ds_natureza_juridica,
    fl_atende_sus,
    fl_atendimento_hospitalar
FROM deduped
WHERE rn = 1
