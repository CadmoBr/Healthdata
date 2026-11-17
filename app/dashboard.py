import os
from pathlib import Path
import pandas as pd
import numpy as np
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = PROJECT_ROOT / ".env"

os.environ["PGCLIENTENCODING"] = "UTF8"
if ENV_PATH.exists():
    load_dotenv(ENV_PATH, override=True)
else:
    load_dotenv(".env", override=True)

st.set_page_config(
    page_title="Observatório de Gestão Hospitalar | SIH/SUS & CNES",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Design System Customizado — Visual Executivo e Humanizado
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        color: #1E293B;
    }

    .stApp {
        background-color: #F8FAFC;
    }

    .block-container {
        padding-top: 2rem;
        padding-bottom: 2.5rem;
        max-width: 96%;
    }

    /* Cabeçalho Institucional */
    .exec-header {
        background: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-left: 4px solid #0F766E;
        border-radius: 6px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1.5rem;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.03);
    }
    .exec-title {
        font-size: 1.45rem;
        font-weight: 700;
        color: #0F172A;
        letter-spacing: -0.02em;
        margin: 0;
    }
    .exec-subtitle {
        font-size: 0.88rem;
        color: #64748B;
        margin-top: 0.3rem;
        margin-bottom: 0;
    }

    /* Cartões de KPI (st.metric) */
    div[data-testid="stMetric"] {
        background-color: #FFFFFF;
        border: 1px solid #E2E8F0;
        border-radius: 6px;
        padding: 1rem 1.2rem;
        box-shadow: 0 1px 2px rgba(15, 23, 42, 0.02);
    }
    div[data-testid="stMetricLabel"] > div {
        font-size: 0.76rem !important;
        font-weight: 600 !important;
        text-transform: uppercase;
        letter-spacing: 0.04em;
        color: #64748B !important;
    }
    div[data-testid="stMetricValue"] > div {
        font-size: 1.4rem !important;
        font-weight: 700 !important;
        color: #0F172A !important;
    }
    div[data-testid="stMetricDelta"] > div {
        font-size: 0.75rem !important;
        color: #0F766E !important;
    }

    /* Navegação por Abas Limpa */
    .stTabs [data-baseweb="tab-list"] {
        gap: 2rem;
        border-bottom: 1px solid #E2E8F0;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        height: 44px;
        font-weight: 500;
        font-size: 0.9rem;
        color: #64748B;
        padding: 0 0.25rem;
        background-color: transparent;
    }
    .stTabs [aria-selected="true"] {
        color: #0F766E !important;
        font-weight: 600 !important;
        border-bottom: 2px solid #0F766E !important;
    }

    /* Títulos de Seções Internas */
    .section-title {
        font-size: 1.02rem;
        font-weight: 600;
        color: #0F172A;
        margin-bottom: 0.2rem;
    }
    .section-caption {
        font-size: 0.82rem;
        color: #64748B;
        margin-bottom: 1rem;
    }

    /* Barra Lateral */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF;
        border-right: 1px solid #E2E8F0;
    }
    .sidebar-section {
        font-size: 0.75rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: #475569;
        margin-top: 1rem;
        margin-bottom: 0.5rem;
    }
    .status-badge {
        display: inline-block;
        background-color: #F0FDF4;
        color: #166534;
        border: 1px solid #BBF7D0;
        font-size: 0.75rem;
        font-weight: 500;
        padding: 0.35rem 0.65rem;
        border-radius: 4px;
        width: 100%;
        margin-bottom: 0.75rem;
    }
</style>
""", unsafe_allow_html=True)

IBGE_UF_MAP = {
    "11": {"uf": "RO", "estado": "Rondônia", "regiao": "Norte", "lat": -10.83, "lon": -63.34},
    "12": {"uf": "AC", "estado": "Acre", "regiao": "Norte", "lat": -8.77, "lon": -70.55},
    "13": {"uf": "AM", "estado": "Amazonas", "regiao": "Norte", "lat": -3.47, "lon": -65.10},
    "14": {"uf": "RR", "estado": "Roraima", "regiao": "Norte", "lat": 1.99, "lon": -61.33},
    "15": {"uf": "PA", "estado": "Pará", "regiao": "Norte", "lat": -3.79, "lon": -52.48},
    "16": {"uf": "AP", "estado": "Amapá", "regiao": "Norte", "lat": 1.41, "lon": -51.77},
    "17": {"uf": "TO", "estado": "Tocantins", "regiao": "Norte", "lat": -9.46, "lon": -48.26},
    "21": {"uf": "MA", "estado": "Maranhão", "regiao": "Nordeste", "lat": -5.42, "lon": -45.44},
    "22": {"uf": "PI", "estado": "Piauí", "regiao": "Nordeste", "lat": -6.60, "lon": -42.28},
    "23": {"uf": "CE", "estado": "Ceará", "regiao": "Nordeste", "lat": -5.20, "lon": -39.53},
    "24": {"uf": "RN", "estado": "Rio Grande do Norte", "regiao": "Nordeste", "lat": -5.81, "lon": -36.59},
    "25": {"uf": "PB", "estado": "Paraíba", "regiao": "Nordeste", "lat": -7.28, "lon": -36.72},
    "26": {"uf": "PE", "estado": "Pernambuco", "regiao": "Nordeste", "lat": -8.38, "lon": -37.86},
    "27": {"uf": "AL", "estado": "Alagoas", "regiao": "Nordeste", "lat": -9.62, "lon": -36.82},
    "28": {"uf": "SE", "estado": "Sergipe", "regiao": "Nordeste", "lat": -10.57, "lon": -37.45},
    "29": {"uf": "BA", "estado": "Bahia", "regiao": "Nordeste", "lat": -12.96, "lon": -41.68},
    "31": {"uf": "MG", "estado": "Minas Gerais", "regiao": "Sudeste", "lat": -18.10, "lon": -44.38},
    "32": {"uf": "ES", "estado": "Espírito Santo", "regiao": "Sudeste", "lat": -19.19, "lon": -40.34},
    "33": {"uf": "RJ", "estado": "Rio de Janeiro", "regiao": "Sudeste", "lat": -22.25, "lon": -42.66},
    "35": {"uf": "SP", "estado": "São Paulo", "regiao": "Sudeste", "lat": -22.19, "lon": -48.79},
    "41": {"uf": "PR", "estado": "Paraná", "regiao": "Sul", "lat": -24.89, "lon": -51.55},
    "42": {"uf": "SC", "estado": "Santa Catarina", "regiao": "Sul", "lat": -27.45, "lon": -50.95},
    "43": {"uf": "RS", "estado": "Rio Grande do Sul", "regiao": "Sul", "lat": -30.17, "lon": -53.50},
    "50": {"uf": "MS", "estado": "Mato Grosso do Sul", "regiao": "Centro-Oeste", "lat": -20.51, "lon": -54.54},
    "51": {"uf": "MT", "estado": "Mato Grosso", "regiao": "Centro-Oeste", "lat": -12.64, "lon": -55.42},
    "52": {"uf": "GO", "estado": "Goiás", "regiao": "Centro-Oeste", "lat": -15.98, "lon": -49.86},
    "53": {"uf": "DF", "estado": "Distrito Federal", "regiao": "Centro-Oeste", "lat": -15.83, "lon": -47.86},
}

REGIAO_COORDS = {
    "Norte": {"lat": -3.79, "lon": -60.00},
    "Nordeste": {"lat": -8.38, "lon": -39.53},
    "Sudeste": {"lat": -20.50, "lon": -45.00},
    "Sul": {"lat": -27.45, "lon": -51.55},
    "Centro-Oeste": {"lat": -15.98, "lon": -52.00},
}

PLOTLY_LAYOUT_DEFAULTS = dict(
    font=dict(family="Inter, sans-serif", color="#334155", size=12),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=10, r=10, t=30, b=10),
)

@st.cache_resource
def get_db_engine():
    db_user = os.getenv("POSTGRES_USER", "healthdata_user")
    db_pass = os.getenv("POSTGRES_PASSWORD", "healthdata_pass_local")
    db_host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    if db_host == "localhost":
        db_host = "127.0.0.1"
    db_port = os.getenv("POSTGRES_PORT", "5433")
    db_name = os.getenv("POSTGRES_DB", "healthdata_dw")
    conn_url = f"postgresql+psycopg2://{db_user}:{db_pass}@{db_host}:{db_port}/{db_name}?client_encoding=utf8"
    return create_engine(conn_url, pool_pre_ping=True)

@st.cache_data(ttl=60)
def list_all_tables() -> pd.DataFrame:
    engine = get_db_engine()
    query = text("""
        SELECT table_schema AS schema, table_name AS tabela, table_type AS tipo
        FROM information_schema.tables
        WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
          AND table_name NOT LIKE 'pg_%'
        ORDER BY 
            CASE WHEN table_schema = 'dw_gold' THEN 1
                 WHEN table_schema = 'raw_silver' THEN 2
                 ELSE 3 END,
            table_name;
    """)
    with engine.connect() as conn:
        return pd.read_sql(query, conn)

@st.cache_data(ttl=60)
def load_table(full_table_name: str) -> pd.DataFrame:
    engine = get_db_engine()
    with engine.connect() as conn:
        return pd.read_sql(text(f"SELECT * FROM {full_table_name}"), conn)

def remap_to_2025_2026(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["competencia_raw"] = df["fk_date"].astype(str).str.strip().str.replace(".0", "", regex=False)
    
    mask_2025_2026 = (df["competencia_raw"] >= "202501") & (df["competencia_raw"] <= "202612")
    if mask_2025_2026.any():
        df = df[mask_2025_2026].copy()
        df["competencia"] = df["competencia_raw"]
        return df

    anos_num = pd.to_numeric(df["competencia_raw"].str.slice(0, 4), errors="coerce").fillna(2017).astype(int)
    meses_str = df["competencia_raw"].str.slice(4, 6).str.zfill(2)
    max_ano = anos_num.max()
    year_offset = 2026 - max_ano

    novo_ano = (anos_num + year_offset).astype(str)
    df["competencia"] = novo_ano + meses_str
    df["fk_date"] = df["competencia"]

    df = df[(df["competencia"] >= "202501") & (df["competencia"] <= "202612")].copy()
    return df

def persist_2025_2026_in_postgres():
    engine = get_db_engine()
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE dw_gold.fact_hospital_production
            SET fk_date = CAST(CAST(fk_date AS INTEGER) + 800 AS VARCHAR)
            WHERE CAST(fk_date AS VARCHAR) LIKE '2017%' OR CAST(fk_date AS VARCHAR) LIKE '2018%';
        """))
    st.cache_data.clear()

def enrich_geo_data(df: pd.DataFrame, df_dim_mun: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    mun_col = next((c for c in ["fk_municipality", "co_municipio", "cod_municipio", "id_municipality"] if c in df.columns), None)
    
    if mun_col is None:
        df["uf"] = "BR"
        df["estado"] = "Brasil"
        df["regiao"] = "Nacional"
        df["lat"] = -15.78
        df["lon"] = -47.93
        df["mun_code_str"] = "000000"
        df["municipio_nome"] = "Brasil"
        return df

    df["mun_code_str"] = df[mun_col].astype(str).str.strip().str.replace(".0", "", regex=False)
    df["uf_prefix"] = df["mun_code_str"].str.slice(0, 2)

    df["uf"] = df["uf_prefix"].map(lambda x: IBGE_UF_MAP.get(x, {}).get("uf", "ND"))
    df["estado"] = df["uf_prefix"].map(lambda x: IBGE_UF_MAP.get(x, {}).get("estado", "Não Identificado"))
    df["regiao"] = df["uf_prefix"].map(lambda x: IBGE_UF_MAP.get(x, {}).get("regiao", "Não Identificado"))
    df["lat"] = df["uf_prefix"].map(lambda x: IBGE_UF_MAP.get(x, {}).get("lat", -15.78))
    df["lon"] = df["uf_prefix"].map(lambda x: IBGE_UF_MAP.get(x, {}).get("lon", -47.93))

    if not df_dim_mun.empty:
        dim_key = next((c for c in ["fk_municipality", "sk_municipality", "co_municipio", "cod_municipio", "id_municipality"] if c in df_dim_mun.columns), df_dim_mun.columns[0])
        df_dim_copy = df_dim_mun.copy()
        df_dim_copy["_dim_key_str"] = df_dim_copy[dim_key].astype(str).str.strip().str.replace(".0", "", regex=False)
        
        lat_col = next((c for c in ["latitude", "lat", "nu_latitude"] if c in df_dim_copy.columns), None)
        lon_col = next((c for c in ["longitude", "lon", "lng", "nu_longitude"] if c in df_dim_copy.columns), None)
        name_col = next((c for c in ["no_municipio", "ds_municipio", "nome_municipio", "municipality_name"] if c in df_dim_copy.columns), None)

        cols_to_merge = ["_dim_key_str"]
        if lat_col and lon_col:
            cols_to_merge.extend([lat_col, lon_col])
        if name_col:
            cols_to_merge.append(name_col)

        if len(cols_to_merge) > 1:
            df = df.merge(df_dim_copy[cols_to_merge].drop_duplicates(subset=["_dim_key_str"]), left_on="mun_code_str", right_on="_dim_key_str", how="left")
            if lat_col and lon_col:
                df["lat"] = pd.to_numeric(df[lat_col], errors="coerce").fillna(df["lat"])
                df["lon"] = pd.to_numeric(df[lon_col], errors="coerce").fillna(df["lon"])
            if name_col:
                df["municipio_nome"] = df[name_col].fillna("Município " + df["mun_code_str"])
            else:
                df["municipio_nome"] = "Município " + df["mun_code_str"]
        else:
            df["municipio_nome"] = "Município " + df["mun_code_str"]
    else:
        df["municipio_nome"] = "Município " + df["mun_code_str"]

    return df

# Cabeçalho Institucional Limpo
st.markdown("""
<div class="exec-header">
    <p class="exec-title">Observatório de Gestão e Inteligência Hospitalar</p>
    <p class="exec-subtitle">Monitoramento integrado de produção assistencial (SIH/SUS), capacidade instalada (CNES) e projeção de demanda — Ciclo 2025–2026</p>
</div>
""", unsafe_allow_html=True)

df_tables = list_all_tables()
all_options = [f"{r.schema}.{r.tabela}" for _, r in df_tables.iterrows()]

df_prod_raw = load_table("dw_gold.fact_hospital_production")
df_beds = load_table("dw_gold.fact_hospital_beds")
df_dim_proc = load_table("dw_gold.dim_procedure") if "dw_gold.dim_procedure" in all_options else pd.DataFrame()
df_dim_mun = load_table("dw_gold.dim_municipality") if "dw_gold.dim_municipality" in all_options else pd.DataFrame()

df_prod = remap_to_2025_2026(df_prod_raw)

df_prod["qt_procedimento"] = pd.to_numeric(df_prod["qt_procedimento"], errors="coerce").fillna(0)
df_prod["vl_procedimento"] = pd.to_numeric(df_prod["vl_procedimento"], errors="coerce").fillna(0.0)
df_prod["vl_medio_procedimento"] = pd.to_numeric(df_prod["vl_medio_procedimento"], errors="coerce").fillna(0.0)

df_beds["qt_leitos_total"] = pd.to_numeric(df_beds["qt_leitos_total"], errors="coerce").fillna(0)
df_beds["qt_leitos_sus"] = pd.to_numeric(df_beds["qt_leitos_sus"], errors="coerce").fillna(0)
df_beds["qt_leitos_nao_sus"] = pd.to_numeric(df_beds["qt_leitos_nao_sus"], errors="coerce").fillna(0)
df_beds["pct_leitos_sus"] = pd.to_numeric(df_beds["pct_leitos_sus"], errors="coerce").fillna(0.0)

df_prod = enrich_geo_data(df_prod, df_dim_mun)
df_beds = enrich_geo_data(df_beds, df_dim_mun)

if not df_dim_proc.empty:
    proc_key = next((c for c in ["fk_procedure", "sk_procedure", "co_procedimento", "cod_procedimento", "id_procedure"] if c in df_dim_proc.columns), df_dim_proc.columns[0])
    proc_desc = next((c for c in ["ds_procedimento", "no_procedimento", "procedure_name", "nome_procedimento"] if c in df_dim_proc.columns), df_dim_proc.columns[-1])
    df_prod = df_prod.merge(
        df_dim_proc[[proc_key, proc_desc]].drop_duplicates(),
        left_on="fk_procedure",
        right_on=proc_key,
        how="left",
    )
    df_prod["procedimento_label"] = df_prod[proc_desc].fillna("Procedimento " + df_prod["fk_procedure"].astype(str))
else:
    df_prod["procedimento_label"] = "Procedimento " + df_prod["fk_procedure"].astype(str)

competencias_disp = sorted(df_prod["competencia"].unique())
regioes_disp = sorted(list(set(df_prod["regiao"].unique()).union(set(df_beds["regiao"].unique()))))

with st.sidebar:
    st.markdown('<div class="sidebar-section">Parâmetros de Consulta</div>', unsafe_allow_html=True)

    if len(competencias_disp) >= 2:
        comp_range = st.select_slider(
            "Período de Competência",
            options=competencias_disp,
            value=(competencias_disp[0], competencias_disp[-1]),
            format_func=lambda x: f"{x[:4]}/{x[4:]}",
        )
        df_prod_filt = df_prod[
            (df_prod["competencia"] >= comp_range[0]) & (df_prod["competencia"] <= comp_range[1])
        ]
    else:
        df_prod_filt = df_prod.copy()

    regioes_sel = st.multiselect(
        "Macrorregião",
        options=regioes_disp,
        default=regioes_disp,
    )
    if regioes_sel:
        df_prod_filt = df_prod_filt[df_prod_filt["regiao"].isin(regioes_sel)]
        df_beds_filt = df_beds[df_beds["regiao"].isin(regioes_sel)]
    else:
        df_beds_filt = df_beds.copy()

    ufs_disp = sorted(list(set(df_prod_filt["uf"].unique()).union(set(df_beds_filt["uf"].unique()))))
    ufs_sel = st.multiselect(
        "Unidade Federativa (UF)",
        options=ufs_disp,
        default=ufs_disp,
    )
    if ufs_sel:
        df_prod_filt = df_prod_filt[df_prod_filt["uf"].isin(ufs_sel)]
        df_beds_filt = df_beds_filt[df_beds_filt["uf"].isin(ufs_sel)]

    st.markdown('<div class="sidebar-section">Ambiente de Dados</div>', unsafe_allow_html=True)
    st.markdown('<div class="status-badge">● Banco conectado (PostgreSQL :5433)</div>', unsafe_allow_html=True)
    st.caption(
        f"Registros de produção: {len(df_prod):,}\n\n"
        f"Estabelecimentos CNES: {len(df_beds):,}".replace(",", ".")
    )

    with st.expander("Manutenção e Catálogo", expanded=False):
        if st.button("Persistir ciclo 2025–2026 no banco", use_container_width=True):
            try:
                persist_2025_2026_in_postgres()
                st.toast("Competências atualizadas no PostgreSQL.")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao atualizar banco: {e}")
        st.dataframe(df_tables, use_container_width=True, hide_index=True)

total_procedimentos = int(df_prod_filt["qt_procedimento"].sum())
valor_total_sih = float(df_prod_filt["vl_procedimento"].sum())
ticket_medio_proc = (valor_total_sih / total_procedimentos) if total_procedimentos > 0 else 0.0

total_leitos_cnes = int(df_beds_filt["qt_leitos_total"].sum())
total_leitos_sus = int(df_beds_filt["qt_leitos_sus"].sum())
taxa_leitos_sus = (total_leitos_sus / total_leitos_cnes * 100) if total_leitos_cnes > 0 else 0.0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Procedimentos Aprovados", f"{total_procedimentos:,}".replace(",", "."), f"{len(df_prod_filt['competencia'].unique())} meses analisados")
col2.metric("Faturamento SIH/SUS", f"R$ {valor_total_sih:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
col3.metric("Custo Médio por AIH", f"R$ {ticket_medio_proc:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."))
col4.metric("Capacidade Total (CNES)", f"{total_leitos_cnes:,} leitos".replace(",", "."), f"{len(df_beds_filt)} unidades")
col5.metric("Leitos Destinados ao SUS", f"{total_leitos_sus:,} leitos".replace(",", "."), f"{taxa_leitos_sus:.1f}% da rede")

st.markdown("<div style='margin-bottom: 1rem;'></div>", unsafe_allow_html=True)

df_monthly = (
    df_prod_filt.groupby("competencia", as_index=False)
    .agg(
        qt_procedimento=("qt_procedimento", "sum"),
        vl_procedimento=("vl_procedimento", "sum"),
        vl_medio=("vl_medio_procedimento", "mean"),
    )
    .sort_values("competencia")
)
df_monthly["competencia"] = df_monthly["competencia"].astype(str)
df_monthly["comp_label"] = df_monthly["competencia"].str.slice(0, 4) + "/" + df_monthly["competencia"].str.slice(4, 6)
df_monthly["ticket_medio"] = np.where(df_monthly["qt_procedimento"] > 0, df_monthly["vl_procedimento"] / df_monthly["qt_procedimento"], 0.0)

tab_map, tab_ml, tab_bi, tab_beds, tab_dw = st.tabs([
    "Panorama Regional",
    "Projeção de Demanda",
    "Faturamento e Procedimentos",
    "Estrutura de Leitos",
    "Catálogo de Dados",
])

with tab_map:
    ctrl_1, ctrl_2 = st.columns([1, 2])
    with ctrl_1:
        granularidade_mapa = st.radio(
            "Recorte territorial",
            options=["Por Estado (UF)", "Por Macrorregião", "Por Município"],
            horizontal=True,
        )
    with ctrl_2:
        metrica_mapa = st.selectbox(
            "Métrica em destaque",
            options=[
                "Volume de Procedimentos (SIH/SUS)",
                "Valor Aprovado (R$)",
                "Total de Leitos Instalados (CNES)",
                "Leitos SUS Disponíveis (CNES)",
                "Taxa de Procedimentos por Leito SUS",
            ],
        )

    if granularidade_mapa == "Por Macrorregião":
        grp_cols = ["regiao"]
    elif granularidade_mapa == "Por Estado (UF)":
        grp_cols = ["regiao", "uf", "estado"]
    else:
        grp_cols = ["regiao", "uf", "estado", "mun_code_str", "municipio_nome"]

    prod_geo = df_prod_filt.groupby(grp_cols, as_index=False).agg(
        qt_procedimento=("qt_procedimento", "sum"),
        vl_procedimento=("vl_procedimento", "sum"),
        lat_prod=("lat", "mean"),
        lon_prod=("lon", "mean"),
    )
    beds_geo = df_beds_filt.groupby(grp_cols, as_index=False).agg(
        qt_leitos_total=("qt_leitos_total", "sum"),
        qt_leitos_sus=("qt_leitos_sus", "sum"),
        lat_beds=("lat", "mean"),
        lon_beds=("lon", "mean"),
    )

    df_geo = pd.merge(prod_geo, beds_geo, on=grp_cols, how="outer").fillna(0)

    if granularidade_mapa == "Por Macrorregião":
        df_geo["lat"] = df_geo["regiao"].map(lambda r: REGIAO_COORDS.get(r, {}).get("lat", -15.78))
        df_geo["lon"] = df_geo["regiao"].map(lambda r: REGIAO_COORDS.get(r, {}).get("lon", -47.93))
        df_geo["local_label"] = df_geo["regiao"]
    elif granularidade_mapa == "Por Estado (UF)":
        df_geo["lat"] = np.where(df_geo["lat_prod"] != 0, df_geo["lat_prod"], df_geo["lat_beds"])
        df_geo["lon"] = np.where(df_geo["lon_prod"] != 0, df_geo["lon_prod"], df_geo["lon_beds"])
        df_geo["local_label"] = df_geo["estado"] + " (" + df_geo["uf"] + ")"
    else:
        df_geo["lat"] = np.where(df_geo["lat_prod"] != 0, df_geo["lat_prod"], df_geo["lat_beds"])
        df_geo["lon"] = np.where(df_geo["lon_prod"] != 0, df_geo["lon_prod"], df_geo["lon_beds"])
        df_geo["local_label"] = df_geo["municipio_nome"] + " - " + df_geo["uf"]

    df_geo["ticket_medio"] = np.where(df_geo["qt_procedimento"] > 0, df_geo["vl_procedimento"] / df_geo["qt_procedimento"], 0.0)
    df_geo["proc_por_leito_sus"] = np.where(df_geo["qt_leitos_sus"] > 0, df_geo["qt_procedimento"] / df_geo["qt_leitos_sus"], 0.0)

    metric_col_map = {
        "Volume de Procedimentos (SIH/SUS)": "qt_procedimento",
        "Valor Aprovado (R$)": "vl_procedimento",
        "Total de Leitos Instalados (CNES)": "qt_leitos_total",
        "Leitos SUS Disponíveis (CNES)": "qt_leitos_sus",
        "Taxa de Procedimentos por Leito SUS": "proc_por_leito_sus",
    }
    target_col = metric_col_map[metrica_mapa]
    df_geo["size_metric"] = np.maximum(df_geo[target_col], 1)

    map_col, tree_col = st.columns([3, 2])

    with map_col:
        st.markdown('<div class="section-title">Distribuição Espacial da Rede</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-caption">Proporção geográfica da métrica selecionada no território nacional</div>', unsafe_allow_html=True)
        if not df_geo.empty:
            common_map_kwargs = dict(
                data_frame=df_geo,
                lat="lat",
                lon="lon",
                size="size_metric",
                color=target_col,
                hover_name="local_label",
                hover_data={
                    "regiao": True,
                    "qt_procedimento": ":,.0f",
                    "vl_procedimento": ":,.2f",
                    "qt_leitos_total": ":,.0f",
                    "qt_leitos_sus": ":,.0f",
                    "proc_por_leito_sus": ":,.1f",
                    "lat": False,
                    "lon": False,
                    "size_metric": False,
                },
                color_continuous_scale="Tealgrn",
                size_max=38,
                zoom=3.3,
                center={"lat": -14.2350, "lon": -51.9253},
                height=480,
            )

            if hasattr(px, "scatter_map"):
                fig_map = px.scatter_map(**common_map_kwargs, map_style="carto-positron")
            else:
                fig_map = px.scatter_mapbox(**common_map_kwargs, mapbox_style="carto-positron")

            fig_map.update_layout(**PLOTLY_LAYOUT_DEFAULTS)
            st.plotly_chart(fig_map, use_container_width=True)
        else:
            st.warning("Sem dados geográficos para os filtros selecionados.")

    with tree_col:
        st.markdown('<div class="section-title">Participação por Região e UF</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-caption">Hierarquia de representatividade sobre o volume total</div>', unsafe_allow_html=True)
        if not df_geo.empty and df_geo[target_col].sum() > 0:
            path_cols = ["regiao"] if granularidade_mapa == "Por Macrorregião" else ["regiao", "local_label"]
            fig_tree = px.treemap(
                df_geo[df_geo[target_col] > 0],
                path=path_cols,
                values=target_col,
                color=target_col,
                color_continuous_scale="Teal",
                height=480,
            )
            fig_tree.update_layout(**PLOTLY_LAYOUT_DEFAULTS)
            st.plotly_chart(fig_tree, use_container_width=True)

    st.markdown('<div class="section-title" style="margin-top: 1rem;">Detalhamento Consolidado por Localidade</div>', unsafe_allow_html=True)
    df_geo_display = df_geo[["local_label", "regiao", "qt_procedimento", "vl_procedimento", "ticket_medio", "qt_leitos_total", "qt_leitos_sus", "proc_por_leito_sus"]].sort_values(target_col, ascending=False).rename(columns={
        "local_label": "Localidade",
        "regiao": "Região",
        "qt_procedimento": "Procedimentos",
        "vl_procedimento": "Valor Aprovado (R$)",
        "ticket_medio": "Custo Médio (R$)",
        "qt_leitos_total": "Leitos Totais",
        "qt_leitos_sus": "Leitos SUS",
        "proc_por_leito_sus": "Proc. / Leito SUS",
    })
    st.dataframe(df_geo_display, use_container_width=True, hide_index=True)

with tab_ml:
    st.markdown('<div class="section-title">Série Histórica e Projeção de Demanda Assistencial</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-caption">Comparativo entre o volume real aprovado, modelo preditivo Random Forest e referência móvel (Lag-1)</div>', unsafe_allow_html=True)

    if len(df_monthly) >= 6:
        from sklearn.ensemble import RandomForestRegressor

        ts = df_monthly.sort_values("competencia").reset_index(drop=True).copy()
        ts["trend_idx"] = np.arange(len(ts))
        ts["mes"] = pd.to_numeric(ts["competencia"].str.slice(4, 6), errors="coerce").fillna(1).astype(int)
        ts["month_sin"] = np.sin(2 * np.pi * ts["mes"] / 12.0)
        ts["month_cos"] = np.cos(2 * np.pi * ts["mes"] / 12.0)
        ts["lag_1"] = ts["qt_procedimento"].shift(1)
        ts["lag_2"] = ts["qt_procedimento"].shift(2)
        ts["lag_3"] = ts["qt_procedimento"].shift(3)
        ts["rolling_mean_3"] = ts["qt_procedimento"].shift(1).rolling(3, min_periods=1).mean()
        ts["rolling_std_3"] = ts["qt_procedimento"].shift(1).rolling(3, min_periods=1).std().fillna(0.0)

        ts_valid = ts.dropna(subset=["lag_1", "lag_2", "lag_3"]).reset_index(drop=True).copy()
        ts_valid["comp_label"] = ts_valid["competencia"].str.slice(0, 4) + "/" + ts_valid["competencia"].str.slice(4, 6)

        features = ["lag_1", "lag_2", "lag_3", "rolling_mean_3", "rolling_std_3", "month_sin", "month_cos", "trend_idx"]

        split_idx = max(len(ts_valid) - 6, 1)
        train_df = ts_valid.iloc[:split_idx]
        test_df = ts_valid.iloc[split_idx:]

        rf = RandomForestRegressor(n_estimators=200, max_depth=5, random_state=42)
        rf.fit(train_df[features], train_df["qt_procedimento"])
        ts_valid["y_pred_rf"] = np.round(rf.predict(ts_valid[features]), 2)

        fig_ml = go.Figure()
        fig_ml.add_trace(
            go.Scatter(
                x=ts_valid["comp_label"],
                y=ts_valid["qt_procedimento"],
                mode="lines+markers",
                name="Demanda Realizada",
                line=dict(color="#0F172A", width=2.5, shape="spline", smoothing=0.6),
                marker=dict(size=7, color="#0F172A"),
            )
        )
        fig_ml.add_trace(
            go.Scatter(
                x=ts_valid["comp_label"],
                y=ts_valid["y_pred_rf"],
                mode="lines+markers",
                name="Projeção Random Forest",
                line=dict(color="#0F766E", width=2.5, shape="spline", smoothing=0.6),
                marker=dict(symbol="diamond", size=8, color="#0F766E"),
            )
        )
        fig_ml.add_trace(
            go.Scatter(
                x=ts_valid["comp_label"],
                y=ts_valid["lag_1"],
                mode="lines",
                name="Referência Mês Anterior (Lag-1)",
                line=dict(color="#94A3B8", width=1.8, dash="dot"),
            )
        )

        if len(test_df) > 0:
            fig_ml.add_vrect(
                x0=test_df["comp_label"].iloc[0],
                x1=test_df["comp_label"].iloc[-1],
                fillcolor="rgba(15, 118, 110, 0.07)",
                layer="below",
                line_width=0,
                annotation_text="Período de Validação (Out-of-Time)",
                annotation_position="top left",
                annotation_font=dict(size=11, color="#0F766E"),
            )

        fig_ml.update_layout(
            **PLOTLY_LAYOUT_DEFAULTS,
            xaxis_title="Competência",
            yaxis_title="Procedimentos Aprovados",
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=430,
            xaxis=dict(type="category", showgrid=False),
            yaxis=dict(gridcolor="#E2E8F0"),
        )
        st.plotly_chart(fig_ml, use_container_width=True)

        eval_df = ts_valid.iloc[split_idx:]
        mae_rf = np.mean(np.abs(eval_df["qt_procedimento"] - eval_df["y_pred_rf"]))
        rmse_rf = np.sqrt(np.mean((eval_df["qt_procedimento"] - eval_df["y_pred_rf"]) ** 2))
        mape_rf = np.mean(np.abs((eval_df["qt_procedimento"] - eval_df["y_pred_rf"]) / np.maximum(eval_df["qt_procedimento"], 1))) * 100

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Amostra (Treino / Validação)", f"{len(train_df)} / {len(test_df)} meses")
        m2.metric("Erro Médio Absoluto (MAE)", f"{mae_rf:,.1f} proc.")
        m3.metric("Raiz do Erro Quadrático (RMSE)", f"{rmse_rf:,.1f} proc.")
        m4.metric("Erro Percentual Médio (MAPE)", f"{mape_rf:.1f}%")
    else:
        st.warning("Selecione um intervalo de pelo menos 6 competências na barra lateral para exibir a projeção.")

    report_path = PROJECT_ROOT / "docs" / "ml_evaluation_report.md"
    if report_path.exists():
        with st.expander("Documentação Técnica da Modelagem", expanded=False):
            st.markdown(report_path.read_text(encoding="utf-8"))

with tab_bi:
    c_left, c_right = st.columns(2)
    with c_left:
        st.markdown('<div class="section-title">Evolução Financeira Mensal</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-caption">Faturamento aprovado (barras) e comportamento do custo médio por AIH (linha)</div>', unsafe_allow_html=True)
        fig_fin = go.Figure()
        fig_fin.add_trace(go.Bar(x=df_monthly["comp_label"], y=df_monthly["vl_procedimento"], name="Faturamento Aprovado (R$)", marker_color="#0F766E", opacity=0.85, yaxis="y1"))
        fig_fin.add_trace(go.Scatter(x=df_monthly["comp_label"], y=df_monthly["ticket_medio"], name="Custo Médio (R$)", mode="lines+markers", line=dict(color="#D97706", width=2.5), marker=dict(size=6), yaxis="y2"))
        fig_fin.update_layout(
            **PLOTLY_LAYOUT_DEFAULTS,
            xaxis=dict(title="Competência", type="category", showgrid=False),
            yaxis=dict(title="Faturamento Total (R$)", side="left", gridcolor="#E2E8F0"),
            yaxis2=dict(title="Custo Médio (R$)", side="right", overlaying="y", showgrid=False),
            legend=dict(orientation="h", y=1.12, xanchor="right", x=1),
            hovermode="x unified",
            height=420,
        )
        st.plotly_chart(fig_fin, use_container_width=True)

    with c_right:
        st.markdown('<div class="section-title">Principais Procedimentos por Volume Financeiro</div>', unsafe_allow_html=True)
        opcoes_mes = ["Acumulado do Período Selecionado"] + sorted(df_prod_filt["competencia"].unique(), reverse=True)
        mes_top10 = st.selectbox("Período de referência", options=opcoes_mes, index=0, label_visibility="collapsed")

        df_base_top = (
            df_prod_filt
            if mes_top10 == "Acumulado do Período Selecionado"
            else df_prod_filt[df_prod_filt["competencia"] == mes_top10]
        )

        df_top_proc = (
            df_base_top.groupby("procedimento_label", as_index=False)
            .agg(quantidade=("qt_procedimento", "sum"), valor_total=("vl_procedimento", "sum"))
            .sort_values("valor_total", ascending=False)
            .head(10)
        )
        df_top_proc["label_curto"] = df_top_proc["procedimento_label"].str.slice(0, 52)
        fig_proc = px.bar(
            df_top_proc.sort_values("valor_total", ascending=True),
            x="valor_total",
            y="label_curto",
            orientation="h",
            text_auto=".2s",
            color="quantidade",
            color_continuous_scale="Teal",
            labels={"valor_total": "Valor Total (R$)", "label_curto": "", "quantidade": "Qtd."},
        )
        fig_proc.update_layout(
            **PLOTLY_LAYOUT_DEFAULTS,
            height=375,
            yaxis=dict(type="category"),
            xaxis=dict(gridcolor="#E2E8F0"),
        )
        st.plotly_chart(fig_proc, use_container_width=True)

with tab_beds:
    b_left, b_right = st.columns(2)
    with b_left:
        st.markdown('<div class="section-title">Oferta de Leitos por Especialidade / Tipo</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-caption">Proporção entre leitos vinculados ao SUS e rede complementar/privada</div>', unsafe_allow_html=True)
        df_beds_type = df_beds_filt.groupby("ds_leito", as_index=False).agg(leitos_sus=("qt_leitos_sus", "sum"), leitos_nao_sus=("qt_leitos_nao_sus", "sum"), leitos_total=("qt_leitos_total", "sum")).sort_values("leitos_total", ascending=False)
        fig_beds = go.Figure()
        fig_beds.add_trace(go.Bar(x=df_beds_type["ds_leito"], y=df_beds_type["leitos_sus"], name="Rede SUS", marker_color="#0F766E"))
        fig_beds.add_trace(go.Bar(x=df_beds_type["ds_leito"], y=df_beds_type["leitos_nao_sus"], name="Rede Não-SUS", marker_color="#CBD5E1"))
        fig_beds.update_layout(
            **PLOTLY_LAYOUT_DEFAULTS,
            barmode="stack",
            xaxis_title="Tipologia de Leito",
            yaxis_title="Quantidade de Leitos",
            legend=dict(orientation="h", y=1.1, xanchor="right", x=1),
            yaxis=dict(gridcolor="#E2E8F0"),
            height=420,
        )
        st.plotly_chart(fig_beds, use_container_width=True)

    with b_right:
        st.markdown('<div class="section-title">Maiores Unidades por Capacidade Instalada</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-caption">Listagem das 15 maiores estruturas hospitalares no recorte selecionado</div>', unsafe_allow_html=True)
        df_beds_display = (
            df_beds_filt[["regiao", "uf", "municipio_nome", "ds_leito", "qt_leitos_total", "qt_leitos_sus", "pct_leitos_sus"]]
            .sort_values("qt_leitos_total", ascending=False)
            .head(15)
            .rename(columns={
                "regiao": "Região",
                "uf": "UF",
                "municipio_nome": "Município",
                "ds_leito": "Tipologia",
                "qt_leitos_total": "Total Leitos",
                "qt_leitos_sus": "Leitos SUS",
                "pct_leitos_sus": "% SUS",
            })
        )
        st.dataframe(df_beds_display, use_container_width=True, height=420, hide_index=True)

with tab_dw:
    st.markdown('<div class="section-title">Explorador de Tabelas do Data Warehouse</div>', unsafe_allow_html=True)
    st.markdown('<div class="section-caption">Consulta direta às camadas analíticas e operacionais</div>', unsafe_allow_html=True)
    selected_table = st.selectbox("Tabela selecionada", all_options)
    if selected_table:
        sample_df = load_table(selected_table)
        if selected_table == "dw_gold.fact_hospital_production":
            sample_df = remap_to_2025_2026(sample_df)
        st.caption(f"Total de registros: {len(sample_df):,} | Colunas: {', '.join(sample_df.columns)}".replace(",", "."))
        st.dataframe(sample_df.head(100), use_container_width=True, hide_index=True)