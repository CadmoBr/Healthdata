
      
  
    

  create  table "healthdata_dw"."dw_gold"."fact_hospital_beds__dbt_tmp"
  
  
    as
  
  (
    

WITH snapshot_hospitais AS (
    SELECT
        md5(sk_hospital_natural || '_202611_GERAL') AS sk_fact_beds,
        202611 AS fk_date,
        co_ibge AS fk_municipality,
        sk_hospital_natural AS fk_facility,
        'CAPACIDADE HOSPITALAR CONSOLIDADA' AS tp_leito,
        COALESCE(ds_tipo_unidade, 'HOSPITAL GERAL') AS ds_leito,
        qt_leitos_total,
        qt_leitos_sus,
        GREATEST(qt_leitos_total - qt_leitos_sus, 0) AS qt_leitos_nao_sus,
        qt_leitos_uti_total,
        qt_leitos_uti_sus,
        CASE
            WHEN qt_leitos_total > 0
            THEN ROUND((qt_leitos_sus::NUMERIC / qt_leitos_total::NUMERIC) * 100, 2)
            ELSE 0.0
        END AS pct_leitos_sus
    FROM "healthdata_dw"."dw_gold"."vw_stg_hospitais_leitos"
),
historico_cnes AS (
    SELECT
        md5(co_cnes || '_' || CAST(sk_date AS TEXT) || '_' || tp_leito || '_' || ds_leito) AS sk_fact_beds,
        sk_date AS fk_date,
        co_ibge AS fk_municipality,
        co_cnes AS fk_facility,
        tp_leito,
        ds_leito,
        qt_leitos_total,
        qt_leitos_sus,
        GREATEST(qt_leitos_total - qt_leitos_sus, 0) AS qt_leitos_nao_sus,
        0 AS qt_leitos_uti_total,
        0 AS qt_leitos_uti_sus,
        CASE
            WHEN qt_leitos_total > 0
            THEN ROUND((qt_leitos_sus::NUMERIC / qt_leitos_total::NUMERIC) * 100, 2)
            ELSE 0.0
        END AS pct_leitos_sus
    FROM "healthdata_dw"."dw_gold"."vw_stg_leitos_historico"
)
SELECT * FROM snapshot_hospitais
UNION ALL
SELECT * FROM historico_cnes
  );
  
  