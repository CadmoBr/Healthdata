

SELECT
    CAST(codigo_cnes AS VARCHAR(7)) AS co_cnes,
    CAST(codigo_municipio AS VARCHAR(6)) AS co_ibge,
    CAST(codigo_uf AS VARCHAR(2)) AS co_uf,
    CAST(nome_fantasia AS VARCHAR(255)) AS no_fantasia,
    CAST(nome_razao_social AS VARCHAR(255)) AS no_razao_social,
    CAST(tipo_gestao AS VARCHAR(30)) AS tp_gestao,
    CAST(descricao_natureza_juridica_estabelecimento AS VARCHAR(120)) AS ds_natureza_juridica,
    CAST(estabelecimento_faz_atendimento_ambulatorial_sus AS VARCHAR(10)) AS fl_atende_sus,
    CAST(estabelecimento_possui_atendimento_hospitalar AS INTEGER) AS fl_atendimento_hospitalar
FROM "healthdata_dw"."raw_silver"."stg_cnes_estabelecimentos"