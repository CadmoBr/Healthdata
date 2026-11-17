-- =========================================================================================
-- HEALTHDATA INTELLIGENCE - CONSULTAS ANALÍTICAS DO DATA WAREHOUSE (CAMADA GOLD)
-- Recursos utilizados: JOIN, GROUP BY, CTEs, Window Functions, Subqueries, CASE WHEN, Datas
-- =========================================================================================

-- [QUERY 1] Quantidade de leitos por município e indicador per capita (Top 10 Municípios)
-- Pergunta de Negócio 1: Quais municípios possuem maior disponibilidade de leitos hospitalares?
WITH leitos_municipio AS (
    SELECT
        m.sk_municipality AS co_ibge,
        m.no_municipio,
        m.co_uf,
        m.no_regiao,
        m.populacao_estimada,
        SUM(b.qt_leitos_total) AS total_leitos,
        SUM(b.qt_leitos_sus) AS total_leitos_sus,
        SUM(b.qt_leitos_uti_total) AS total_leitos_uti
    FROM dw_gold.fact_hospital_beds b
    INNER JOIN dw_gold.dim_municipality m
        ON b.fk_municipality = m.sk_municipality
    GROUP BY
        m.sk_municipality, m.no_municipio, m.co_uf, m.no_regiao, m.populacao_estimada
)
SELECT
    RANK() OVER (ORDER BY total_leitos DESC) AS ranking_nacional,
    co_ibge,
    no_municipio,
    co_uf,
    no_regiao,
    total_leitos,
    total_leitos_sus,
    total_leitos_uti,
    CASE
        WHEN populacao_estimada > 0
        THEN ROUND((total_leitos_sus::NUMERIC / populacao_estimada::NUMERIC) * 1000, 2)
        ELSE NULL
    END AS leitos_sus_por_1000_hab
FROM leitos_municipio
ORDER BY total_leitos DESC
LIMIT 10;

-- [QUERY 2] Distribuição de estabelecimentos e leitos por Região do Brasil
-- Pergunta de Negócio 3: Quais regiões apresentam maior concentração de estabelecimentos e leitos?
SELECT
    m.no_regiao,
    COUNT(DISTINCT f.sk_facility) AS total_estabelecimentos,
    COALESCE(SUM(b.qt_leitos_total), 0) AS total_leitos,
    COALESCE(SUM(b.qt_leitos_sus), 0) AS total_leitos_sus,
    COALESCE(SUM(b.qt_leitos_nao_sus), 0) AS total_leitos_nao_sus,
    ROUND(
        (COALESCE(SUM(b.qt_leitos_total), 0)::NUMERIC /
         NULLIF(SUM(COALESCE(SUM(b.qt_leitos_total), 0)) OVER (), 0)::NUMERIC) * 100,
        2
    ) AS share_nacional_leitos_pct
FROM dw_gold.dim_municipality m
LEFT JOIN dw_gold.dim_health_facility f
    ON m.sk_municipality = f.fk_municipality
LEFT JOIN dw_gold.fact_hospital_beds b
    ON f.sk_facility = b.fk_facility
GROUP BY m.no_regiao
ORDER BY total_leitos DESC;

-- [QUERY 3] Comparação entre Leitos SUS e Não-SUS por Classificação de Atendimento
-- Pergunta de Negócio: Qual a proporção de dedicação ao SUS na rede hospitalar?
SELECT
    f.ds_natureza_juridica,
    COUNT(DISTINCT f.sk_facility) AS qtd_hospitais,
    SUM(b.qt_leitos_total) AS leitos_totais,
    SUM(b.qt_leitos_sus) AS leitos_sus,
    SUM(b.qt_leitos_nao_sus) AS leitos_nao_sus,
    CASE
        WHEN SUM(b.qt_leitos_total) > 0
        THEN ROUND((SUM(b.qt_leitos_sus)::NUMERIC / SUM(b.qt_leitos_total)::NUMERIC) * 100, 2)
        ELSE 0.0
    END AS percentual_dedicacao_sus,
    CASE
        WHEN SUM(b.qt_leitos_sus) >= SUM(b.qt_leitos_total) * 0.70 THEN 'PREDOMINÂNCIA SUS (>=70%)'
        WHEN SUM(b.qt_leitos_sus) > 0 THEN 'ATENDIMENTO MISTO'
        ELSE 'EXCLUSIVO PRIVADO / NÃO-SUS'
    END AS perfil_assistencial
FROM dw_gold.fact_hospital_beds b
INNER JOIN dw_gold.dim_health_facility f
    ON b.fk_facility = f.sk_facility
GROUP BY f.ds_natureza_juridica
ORDER BY leitos_totais DESC;

-- [QUERY 4] Evolução Mensal da Produção Hospitalar com Variação MoM (Window Function LAG)
-- Pergunta de Negócio 4: Como evolui a produção hospitalar brasileira ao longo das competências?
WITH producao_mensal AS (
    SELECT
        d.sk_date AS competencia,
        d.ano_mes,
        d.ano,
        d.trimestre,
        SUM(p.qt_procedimento) AS total_procedimentos,
        SUM(p.vl_procedimento) AS valor_total_aprovado
    FROM dw_gold.fact_hospital_production p
    INNER JOIN dw_gold.dim_date d
        ON p.fk_date = d.sk_date
    GROUP BY d.sk_date, d.ano_mes, d.ano, d.trimestre
)
SELECT
    competencia,
    ano_mes,
    ano,
    trimestre,
    total_procedimentos,
    valor_total_aprovado,
    LAG(total_procedimentos) OVER (ORDER BY competencia) AS proc_mes_anterior,
    CASE
        WHEN LAG(total_procedimentos) OVER (ORDER BY competencia) > 0
        THEN ROUND(
            ((total_procedimentos - LAG(total_procedimentos) OVER (ORDER BY competencia))::NUMERIC /
             LAG(total_procedimentos) OVER (ORDER BY competencia)::NUMERIC) * 100,
            2
        )
        ELSE NULL
    END AS variacao_mensal_pct
FROM producao_mensal
ORDER BY competencia;

-- [QUERY 5] Ranking de Municípios e Estabelecimentos por Produção Hospitalar e Ticket Médio
-- Pergunta de Negócio 6: Quais municípios e hospitais lideram a produção hospitalar?
SELECT
    DENSE_RANK() OVER (ORDER BY SUM(p.vl_procedimento) DESC) AS rank_financeiro,
    m.no_municipio,
    m.co_uf,
    f.no_estabelecimento,
    pr.ds_procedimento,
    SUM(p.qt_procedimento) AS qtd_procedimentos,
    SUM(p.vl_procedimento) AS valor_total_reais,
    ROUND(AVG(p.vl_medio_procedimento), 2) AS ticket_medio_procedimento
FROM dw_gold.fact_hospital_production p
INNER JOIN dw_gold.dim_municipality m ON p.fk_municipality = m.sk_municipality
INNER JOIN dw_gold.dim_health_facility f ON p.fk_facility = f.sk_facility
INNER JOIN dw_gold.dim_procedure pr ON p.fk_procedure = pr.sk_procedure
GROUP BY m.no_municipio, m.co_uf, f.no_estabelecimento, pr.ds_procedimento
ORDER BY valor_total_reais DESC
LIMIT 10;

-- [QUERY 6] Relação Oferta de Leitos vs. Volume de Produção Hospitalar por UF
-- Pergunta de Negócio 5: Existe relação entre a disponibilidade de leitos e a produção hospitalar?
WITH oferta_uf AS (
    SELECT
        m.co_uf,
        SUM(b.qt_leitos_total) AS leitos_totais,
        SUM(b.qt_leitos_sus) AS leitos_sus
    FROM dw_gold.fact_hospital_beds b
    INNER JOIN dw_gold.dim_municipality m ON b.fk_municipality = m.sk_municipality
    GROUP BY m.co_uf
),
producao_uf AS (
    SELECT
        m.co_uf,
        SUM(p.qt_procedimento) AS procedimentos_aprovados,
        SUM(p.vl_procedimento) AS valor_aprovado
    FROM dw_gold.fact_hospital_production p
    INNER JOIN dw_gold.dim_municipality m ON p.fk_municipality = m.sk_municipality
    GROUP BY m.co_uf
)
SELECT
    COALESCE(o.co_uf, p.co_uf) AS uf,
    COALESCE(o.leitos_totais, 0) AS leitos_totais,
    COALESCE(o.leitos_sus, 0) AS leitos_sus,
    COALESCE(p.procedimentos_aprovados, 0) AS procedimentos_aprovados,
    COALESCE(p.valor_aprovado, 0.0) AS valor_aprovado
FROM oferta_uf o
FULL OUTER JOIN producao_uf p ON o.co_uf = p.co_uf
ORDER BY leitos_totais DESC, procedimentos_aprovados DESC;

-- [QUERY 7] Identificação de Variações Atípicas (Outliers de Capacidade Hospitalar Acima da Média)
-- Subquery + Desvio Padrão para detectar hospitais de alta complexidade / concentração atípica
SELECT
    f.no_estabelecimento,
    m.no_municipio,
    m.co_uf,
    b.qt_leitos_total,
    b.qt_leitos_sus,
    b.qt_leitos_uti_total,
    stats.media_leitos,
    stats.desvio_padrao_leitos,
    ROUND(
        (b.qt_leitos_total - stats.media_leitos) / NULLIF(stats.desvio_padrao_leitos, 0),
        2
    ) AS z_score_capacidade
FROM dw_gold.fact_hospital_beds b
INNER JOIN dw_gold.dim_health_facility f ON b.fk_facility = f.sk_facility
INNER JOIN dw_gold.dim_municipality m ON b.fk_municipality = m.sk_municipality
CROSS JOIN (
    SELECT
        ROUND(AVG(qt_leitos_total), 2) AS media_leitos,
        ROUND(STDDEV_POP(qt_leitos_total), 2) AS desvio_padrao_leitos
    FROM dw_gold.fact_hospital_beds
) stats
WHERE b.qt_leitos_total > stats.media_leitos
ORDER BY z_score_capacidade DESC
LIMIT 10;