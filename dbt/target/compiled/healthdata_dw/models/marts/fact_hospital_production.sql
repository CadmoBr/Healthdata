

SELECT
    md5(CAST(sk_date AS TEXT) || '_' || co_cnes || '_' || co_procedimento || '_' || co_ibge) AS sk_fact_production,
    sk_date AS fk_date,
    co_ibge AS fk_municipality,
    co_cnes AS fk_facility,
    co_procedimento AS fk_procedure,
    qt_procedimento,
    vl_procedimento,
    CASE
        WHEN qt_procedimento > 0
        THEN ROUND(vl_procedimento / qt_procedimento, 2)
        ELSE 0.0
    END AS vl_medio_procedimento
FROM "healthdata_dw"."dw_gold"."vw_stg_sih_producao"