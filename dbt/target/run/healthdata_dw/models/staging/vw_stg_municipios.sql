
  create view "healthdata_dw"."dw_gold"."vw_stg_municipios__dbt_tmp"
    
    
  as (
    

SELECT
    CAST(codigo_municipio AS VARCHAR(6)) AS co_ibge,
    CAST(nome_municipio AS VARCHAR(150)) AS no_municipio,
    CAST(codigo_uf AS VARCHAR(2)) AS co_uf,
    CAST(uf AS VARCHAR(60)) AS no_uf,
    CAST(regiao_pais AS VARCHAR(40)) AS no_regiao,
    CAST(codigo_macrorregiao_saude AS VARCHAR(10)) AS co_macrorregiao_saude,
    CAST(macrorregiao_saude AS VARCHAR(150)) AS no_macrorregiao_saude,
    CAST(codigo_regiao_saude AS VARCHAR(10)) AS co_regiao_saude,
    CAST(regiao_saude AS VARCHAR(150)) AS no_regiao_saude,
    CAST(populacao_estimada_ibge_2022 AS INTEGER) AS populacao_estimada
FROM "healthdata_dw"."raw_silver"."stg_municipios_saude"
  );