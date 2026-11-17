# Resultados das Consultas Analíticas SQL — Camada Gold (`dw_gold`)

Consultas executadas diretamente sobre o Star Schema no PostgreSQL.

## [QUERY 1] Quantidade de leitos por município e indicador per capita (Top 10 Municípios)

```text
 ranking_nacional co_ibge          no_municipio co_uf no_regiao  total_leitos  total_leitos_sus  total_leitos_uti leitos_sus_por_1000_hab
                1  293461              SALVADOR    BA  NORDESTE          5062              4018                90                    None
                2  283289               ARACAJU    SE  NORDESTE          1634              1288                 0                    None
                3  269548                RECIFE    PE  NORDESTE           830               518                 0                    None
                4  355655                OSASCO    SP   SUDESTE           654               585                10                    None
                5  154392             CASTANHAL    PA     NORTE           296               296                 0                    None
                6  355136           SANTO ANDRE    SP   SUDESTE            12                12                 0                    None
                7  313270 MUNICÍPIO IBGE 313270    31    BRASIL             7                 5                 0                    None
                8  313300 MUNICÍPIO IBGE 313300    31    BRASIL             2                 1                 0                    None
                9  313240 MUNICÍPIO IBGE 313240    31    BRASIL             1                 0                 0                    None
```

## [QUERY 2] Distribuição de estabelecimentos e leitos por Região do Brasil

```text
no_regiao  total_estabelecimentos  total_leitos  total_leitos_sus  total_leitos_nao_sus  share_nacional_leitos_pct
 NORDESTE                      50          7526              5824                  1702                      88.56
  SUDESTE                       6           666               597                    69                       7.84
    NORTE                       4           296               296                     0                       3.48
   BRASIL                      66            10                 6                     4                       0.12
```

## [QUERY 3] Comparação entre Leitos SUS e Não-SUS por Classificação de Atendimento

```text
 ds_natureza_juridica  qtd_hospitais  leitos_totais  leitos_sus  leitos_nao_sus  percentual_dedicacao_sus         perfil_assistencial
     HOSPITAL_PÚBLICO             26           3513        3430              83                     97.64   PREDOMINÂNCIA SUS (>=70%)
HOSPITAL_FILANTRÓPICO             14           3129        1770            1359                     56.57           ATENDIMENTO MISTO
     HOSPITAL_PRIVADO             20           1846        1517             329                     82.18   PREDOMINÂNCIA SUS (>=70%)
  SEM FINS LUCRATIVOS              2              9           6               3                     66.67           ATENDIMENTO MISTO
              PRIVADO              1              1           0               1                      0.00 EXCLUSIVO PRIVADO / NÃO-SUS
```

## [QUERY 4] Evolução Mensal da Produção Hospitalar com Variação MoM (Window Function LAG)

```text
 competencia ano_mes  ano  trimestre  total_procedimentos  valor_total_aprovado proc_mes_anterior variacao_mensal_pct
      201701 2017-01 2017          1                    3                827.36              None                None
```

## [QUERY 5] Ranking de Municípios e Estabelecimentos por Produção Hospitalar e Ticket Médio

```text
 rank_financeiro          no_municipio co_uf                                        no_estabelecimento                                                                     ds_procedimento  qtd_procedimentos  valor_total_reais  ticket_medio_procedimento
               1 MUNICÍPIO IBGE 354160    35 HOSPITAL GERAL PREFEITO MIGUEL MARTIN GUALDA DE PROMISSAO                              0304100021 - TRATAMENTO CLÍNICO DE PACIENTE ONCOLÓGICO                  1             480.10                     480.10
               2 MUNICÍPIO IBGE 355540    35                     SANTA CASA DE MISERICORDIA DE UBATUBA 0303100010 - TRATAMENTO DE COMPLICACOES RELACIONADAS PREDOMINANTEMENTE AO PUERPERIO                  1             263.44                     263.44
               3 MUNICÍPIO IBGE 354340    35               HOSPITAL IMACULADA CONCEICAO RIBEIRAO PRETO             0301060088 - DIAGNOSTICO E/OU ATENDIMENTO DE URGENCIA EM CLINICA MEDICA                  1              83.82                      83.82
```

## [QUERY 6] Relação Oferta de Leitos vs. Volume de Produção Hospitalar por UF

```text
uf  leitos_totais  leitos_sus  procedimentos_aprovados  valor_aprovado
BA           5062        4018                        0            0.00
SE           1634        1288                        0            0.00
PE            830         518                        0            0.00
SP            666         597                        0            0.00
PA            296         296                        0            0.00
31             10           6                        0            0.00
35              0           0                        3          827.36
```

## [QUERY 7] Identificação de Variações Atípicas (Outliers de Capacidade Hospitalar Acima da Média)

```text
                            no_estabelecimento no_municipio co_uf  qt_leitos_total  qt_leitos_sus  qt_leitos_uti_total  media_leitos  desvio_padrao_leitos  z_score_capacidade
                 HOSPITAL GERAL ROBERTO SANTOS     SALVADOR    BA              569            569                    0        134.89                119.31                3.64
                         HOSPITAL SANTA ISABEL     SALVADOR    BA              445            291                   65        134.89                119.31                2.60
                            HOSPITAL PORTUGUES     SALVADOR    BA              424             53                    0        134.89                119.31                2.42
                          HOSPITAL DE CIRURGIA      ARACAJU    SE              395            395                    0        134.89                119.31                2.18
                         HOSPITAL SANTA IZABEL      ARACAJU    SE              334            328                    0        134.89                119.31                1.67
                       REAL HOSPITAL PORTUGUES       RECIFE    PE              322             90                    0        134.89                119.31                1.57
HOSPITAL UNIVERSITARIO PROFESSOR EDGARD SANTOS     SALVADOR    BA              276            276                    0        134.89                119.31                1.18
                      HOSPITAL GERAL DO ESTADO     SALVADOR    BA              265            265                    0        134.89                119.31                1.09
                           HOSPITAL SAO RAFAEL     SALVADOR    BA              254             55                    0        134.89                119.31                1.00
                               SANATORIO BAHIA     SALVADOR    BA              240            240                    0        134.89                119.31                0.88
```
