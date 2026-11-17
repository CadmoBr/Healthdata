WITH base_proc AS (
    SELECT
        co_procedimento AS sk_procedure,
        co_procedimento,
        ds_procedimento,
        COALESCE(ds_complexidade, 'NÃO INFORMADO') AS ds_complexidade,
        COALESCE(ds_financiamento, 'NÃO INFORMADO') AS ds_financiamento,
        ROW_NUMBER() OVER (PARTITION BY co_procedimento ORDER BY ds_procedimento) AS rn
    FROM "healthdata_dw"."dw_gold"."vw_stg_sih_producao"
)
SELECT
    sk_procedure,
    co_procedimento,
    ds_procedimento,
    ds_complexidade,
    ds_financiamento
FROM base_proc
WHERE rn = 1