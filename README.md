
# Observatório de Gestão e Inteligência Hospitalar
### SIH/SUS • CNES • Engenharia de Dados • Business Intelligence • Machine Learning

Plataforma de dados ponta a ponta para análise da produção hospitalar do Sistema Único de Saúde (SUS), monitoramento da capacidade hospitalar instalada e previsão de demanda por internações no Brasil.

O projeto utiliza dados públicos do **SIH/SUS e CNES**, estruturando um Data Warehouse dimensional em PostgreSQL e disponibilizando indicadores estratégicos e análises preditivas por meio de um dashboard interativo.

**Período de análise:** Ciclo 2025–2026.

---

## 🎯 Objetivo do Projeto

A gestão eficiente da saúde pública depende da capacidade de transformar dados assistenciais em informações estratégicas.

O projeto propõe integrar os dados de produção hospitalar do SIH/SUS com os dados de infraestrutura hospitalar do CNES, permitindo analisar a relação entre internações, procedimentos aprovados, disponibilidade de leitos e recursos financeiros.

A plataforma busca responder a três questões principais:

1. **Pressão Assistencial Geográfica:** Quais macrorregiões, estados e municípios apresentam maior volume de procedimentos aprovados em relação à disponibilidade de leitos SUS?
2. **Previsibilidade de Demanda:** Qual é a tendência do volume de internações para os próximos meses? Como o modelo preditivo se comporta em dados não utilizados durante o treinamento?
3. **Análise Financeira:** Quais procedimentos concentram os maiores valores aprovados e como evolui o custo médio por AIH (Autorização de Internação Hospitalar)?

---

## 🏗️ Arquitetura da Solução

A solução foi estruturada com base em uma arquitetura de dados em camadas (Medallion Architecture), integrando processos de tratamento, modelagem dimensional, análise exploratória, Machine Learning e visualização de indicadores.

### 1. Engenharia de Dados e Data Warehouse

Implementação de uma estrutura analítica em PostgreSQL, utilizando modelagem dimensional baseada em Star Schema.

**Camadas de dados:**

- `raw_silver`: dados extraídos das bases públicas do DATASUS, submetidos a processos de limpeza, padronização e enriquecimento.
- `dw_gold`: camada analítica estruturada em modelo dimensional, preparada para consultas e geração de indicadores.

**Modelagem dimensional:**

- Tabelas fato:
  - `fact_hospital_production`
  - `fact_hospital_beds`
- Dimensões:
  - `dim_procedure`
  - `dim_municipality`
  - `dim_date`

### 2. Machine Learning e Previsão de Demanda

Desenvolvimento de um modelo preditivo utilizando `RandomForestRegressor`, da biblioteca Scikit-Learn, para estimar o volume mensal de internações hospitalares.

**Engenharia de atributos (Feature Engineering):**

- Defasagens temporais: `lag_1`, `lag_2` e `lag_3`.
- Estatísticas móveis de três meses: média e desvio-padrão.
- Codificação cíclica da sazonalidade: `month_sin` e `month_cos`.

**Estratégia de validação:**

Foi adotada uma divisão temporal estrita (*Out-of-Time Split*), preservando a ordem cronológica dos dados e evitando vazamento de informações futuras (*Data Leakage*).

O desempenho do modelo é comparado com um modelo de referência (*Baseline Naive Lag-1*), utilizando as seguintes métricas:

- MAE (Mean Absolute Error).
- RMSE (Root Mean Squared Error).
- MAPE (Mean Absolute Percentage Error).

### 3. Business Intelligence e Visualização

Desenvolvimento de uma aplicação analítica utilizando Streamlit e Plotly.

**Recursos do dashboard:**

- Indicadores executivos de produção hospitalar.
- Análise regional e geográfica da distribuição de procedimentos.
- Monitoramento da relação entre produção assistencial e leitos disponíveis.
- Projeção de demanda por internações.
- Análise de faturamento e procedimentos hospitalares.
- Filtros globais por competência, macrorregião e Unidade Federativa.
- Visualizações geográficas utilizando códigos IBGE.

---

## 🛠️ Tecnologias Utilizadas

| Categoria | Tecnologias |
|---|---|
| Linguagem | Python 3.10+ |
| Banco de Dados | PostgreSQL |
| Integração com Banco | SQLAlchemy, psycopg2 |
| Engenharia e Manipulação de Dados | Pandas, NumPy |
| Machine Learning | Scikit-Learn |
| Business Intelligence | Streamlit, Plotly |
| Visualização Geográfica | MapLibre |
| Configuração | Python-dotenv |
| Infraestrutura | Docker (opcional) |
| Versionamento | Git e GitHub |

---

## 📂 Estrutura do Repositório

```text
healthdata-intelligence/
│
├── app/
│   └── dashboard.py
│
├── docs/
│   └── ml_evaluation_report.md
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

**Principais diretórios e arquivos:**

- `app/`: aplicação principal do dashboard.
- `docs/`: documentação técnica e relatório de avaliação do modelo preditivo.
- `.env.example`: exemplo de configuração das variáveis de ambiente.
- `requirements.txt`: dependências necessárias para execução.
- `README.md`: documentação do projeto.

---

## 🚀 Como Executar Localmente

### Pré-requisitos

Antes de iniciar, certifique-se de possuir:

- Python 3.10 ou superior.
- PostgreSQL instalado e configurado.
- Git instalado.
- Banco de dados do projeto previamente criado e populado.

### 1. Clonar o repositório

```bash
git clone https://github.com/SEU-USUARIO/healthdata-intelligence.git

cd healthdata-intelligence
```

### 2. Criar e ativar o ambiente virtual

**Windows (PowerShell):**

```powershell
python -m venv .venv

.venv\Scripts\Activate.ps1
```

**Linux/macOS:**

```bash
python -m venv .venv

source .venv/bin/activate
```

### 3. Instalar as dependências

```bash
pip install -r requirements.txt
```

### 4. Configurar as variáveis de ambiente

Crie um arquivo `.env` na raiz do projeto, utilizando o `.env.example` como referência.

Exemplo:

```ini
POSTGRES_USER=healthdata_user
POSTGRES_PASSWORD=healthdata_pass_local
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5433
POSTGRES_DB=healthdata_dw
```

**Importante:** não compartilhe credenciais reais nem envie o arquivo `.env` para o GitHub.

### 5. Executar a aplicação

Com o banco de dados configurado e disponível, execute:

```bash
streamlit run app/dashboard.py
```

A aplicação será disponibilizada localmente, geralmente em:

```text
http://localhost:8501
```

---

## 📊 Telas do Projeto

O dashboard está organizado em três áreas analíticas:

### Panorama Regional
Análise da distribuição da produção hospitalar, indicadores assistenciais e capacidade instalada por região, estado e município.

### Projeção de Demanda
Visualização das séries históricas e previsões de internações, com acompanhamento do desempenho do modelo de Machine Learning.

### Faturamento e Procedimentos
Análise dos valores aprovados, volume de procedimentos e evolução do custo médio por AIH.

> **Demonstração visual:** adicione nesta seção capturas de tela das três áreas do dashboard para apresentar os resultados da aplicação.

---

## 📈 Avaliação do Modelo Preditivo

A avaliação do modelo está documentada em:

[`docs/ml_evaluation_report.md`](docs/ml_evaluation_report.md)

O relatório apresenta a estratégia de validação temporal, comparação com o modelo de referência e métricas de desempenho.

---

## 🔍 Fontes de Dados

O projeto utiliza bases públicas disponibilizadas pelo Departamento de Informática do Sistema Único de Saúde (DATASUS).

- [DATASUS](https://datasus.saude.gov.br/)
- [SIH/SUS – Sistema de Informações Hospitalares](https://datasus.saude.gov.br/acesso-a-informacao/morbidade-hospitalar-do-sus-sih-sus/)
- [CNES – Cadastro Nacional de Estabelecimentos de Saúde](https://cnes.datasus.gov.br/)

---

## 👨‍💻 Autor

**José Airton**

Desenvolvimento de projetos em Engenharia de Dados, Ciência de Dados, Machine Learning e Business Intelligence, com foco em aplicações analíticas para a gestão pública e saúde.

- GitHub: [@CadmoBr](https://github.com/CadmoBr)
- LinkedIn: [José Airton](https://www.linkedin.com/in/airtonsmarques/)

---

⭐ Se este projeto despertou seu interesse, considere deixar uma estrela no repositório!
