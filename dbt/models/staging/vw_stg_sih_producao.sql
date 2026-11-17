{{
    config(
        materialized='view'
    )
}}

SELECT
    CAST(nu_comp AS INTEGER) AS sk_date,
    CAST(nu_ano AS INTEGER) AS nu_ano,
    CAST(co_ibge AS VARCHAR(6)) AS co_ibge,
    CAST(co_cnes AS VARCHAR(7)) AS co_cnes,
    CAST(no_fantasia AS VARCHAR(255)) AS no_fantasia,
    CAST(ds_natureza_juridica AS VARCHAR(120)) AS ds_natureza_juridica,
    CAST(ds_grupo_nat_jur AS VARCHAR(80)) AS ds_grupo_nat_jur,
    CAST(co_proc_realizado AS VARCHAR(20)) AS co_procedimento,
    CAST(ds_procedimento AS VARCHAR(255)) AS ds_procedimento,
    CAST(ds_complex_procedimento AS VARCHAR(100)) AS ds_complexidade,
    CAST(ds_financiamento AS VARCHAR(120)) AS ds_financiamento,
    CAST(qt_procedimento AS INTEGER) AS qt_procedimento,
    CAST(nu_valor_procedimento AS NUMERIC(14, 2)) AS vl_procedimento
FROM {{ source('raw_silver', 'stg_sih_producao_hospitalar') }}
