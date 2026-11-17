
  create view "healthdata_dw"."dw_gold"."vw_stg_leitos_historico__dbt_tmp"
    
    
  as (
    

SELECT
    CAST(nu_comp AS INTEGER) AS sk_date,
    CAST(co_ibge AS VARCHAR(6)) AS co_ibge,
    CAST(co_cnes AS VARCHAR(7)) AS co_cnes,
    CAST(tp_unidade AS VARCHAR(100)) AS ds_tipo_unidade,
    CAST(no_grupo_nat_jur AS VARCHAR(100)) AS ds_natureza_juridica,
    CAST(tp_leito AS VARCHAR(100)) AS tp_leito,
    CAST(ds_leito AS VARCHAR(150)) AS ds_leito,
    CAST(qt_existente AS INTEGER) AS qt_leitos_total,
    CAST(qt_sus AS INTEGER) AS qt_leitos_sus
FROM "healthdata_dw"."raw_silver"."stg_cnes_leitos_historico"
  );