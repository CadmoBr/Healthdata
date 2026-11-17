"""
Processador da Camada Silver para o HealthData Intelligence.
Consolida os dados particionados da Bronze (2019-2026), aplica limpeza 
e carrega as tabelas limpas no PostgreSQL.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Tuple

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from src.utils.logger import get_logger
from src.validation.quality_rules import apply_quality_rules

load_dotenv(override=True)
logger = get_logger("silver_processor")

DATA_BRONZE_PATH = os.getenv("DATA_BRONZE_PATH", "data/bronze")
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/healthdata")

DATASETS = [
    "municipios_saude",
    "cnes_estabelecimentos",
    "hospitais_e_leitos",
    "cnes_leitos_historico",
    "sih_producao_hospitalar",
]


def get_db_engine():
    return create_engine(DATABASE_URL)


def clean_cnes_estabelecimentos(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Limpa e padroniza dados do CNES Estabelecimentos separando registros válidos e rejeitados."""
    df = df_raw.copy()
    if "codigo_cnes" in df.columns:
        df["codigo_cnes"] = (
            df["codigo_cnes"]
            .astype(str)
            .str.strip()
            .str.replace(r"\.0$", "", regex=True)
            .str.zfill(7)
        )
    if "codigo_municipio" in df.columns:
        df["codigo_municipio"] = (
            df["codigo_municipio"]
            .astype(str)
            .str.strip()
            .str.replace(r"\.0$", "", regex=True)
        )
    for col in ["nome_fantasia", "nome_razao_social", "tipo_gestao"]:
        if col in df.columns:
            df[col] = df[col].astype(str).str.strip().str.upper()

    return apply_quality_rules(
        df,
        required_columns=["codigo_cnes", "codigo_municipio"],
        unique_keys=["codigo_cnes"],
        ibge_column="codigo_municipio",
    )


def clean_hospitais_e_leitos(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Corrige erros de digitação do schema original do Ministério da Saúde e tipa colunas de leitos."""
    df = df_raw.copy()
    rename_map = {
        "nome_da_regiao_do_brasil_onde_fica_o_hospital": "regiao",
        "unidade_da_federacao_onde_fica_o_hospital": "uf",
        "nome_do_municipio_onde_fica_o_hospital": "nome_municipio",
        "nome_do_hospital": "nome_hospital",
        "nome_da_razao_social_do_hospital": "razao_social",
        "tipo_da_gestao_do_hospital": "tipo_gestao",
        "descricao_da_natureza_juridica_do_hosptial": "natureza_juridica",
        "enderco_do_hospital": "endereco_hospital",
        "numero_do_cep_do_hospital": "cep",
        "quantidade_total_de_leitos_do_hosptial": "qt_leitos_total",
        "quantidade_total_de_leitos_sus_do_hosptial": "qt_leitos_sus",
        "quantidade_de_leitos_de_uti_do_hosptial": "qt_leitos_uti",
        "codigo_ibge_do_municipio": "codigo_ibge",
    }
    df = df.rename(columns={k: v for k, v in rename_map.items() if k in df.columns})

    for num_col in ["qt_leitos_total", "qt_leitos_sus", "qt_leitos_uti"]:
        if num_col in df.columns:
            df[num_col] = pd.to_numeric(df[num_col], errors="coerce").fillna(0).astype(int)

    if "codigo_ibge" in df.columns:
        df["codigo_ibge"] = (
            df["codigo_ibge"]
            .astype(str)
            .str.strip()
            .str.replace(r"\.0$", "", regex=True)
        )

    for str_col in ["regiao", "uf", "nome_municipio", "nome_hospital", "endereco_hospital"]:
        if str_col in df.columns:
            df[str_col] = df[str_col].astype(str).str.strip().str.upper()

    non_neg = [c for c in ["qt_leitos_total", "qt_leitos_sus"] if c in df.columns]
    req_cols = [c for c in ["codigo_ibge", "nome_hospital"] if c in df.columns]
    uniq_cols = [c for c in ["codigo_ibge", "nome_hospital"] if c in df.columns]
    ibge_col = "codigo_ibge" if "codigo_ibge" in df.columns else None

    return apply_quality_rules(
        df,
        required_columns=req_cols,
        unique_keys=uniq_cols,
        non_negative_columns=non_neg,
        ibge_column=ibge_col,
    )


def clean_municipios_saude(df_raw: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Extrai o nome limpo do município e converte a população estimada para inteiro."""
    df = df_raw.copy()
    if "codigo_municipio" in df.columns:
        df["codigo_municipio"] = (
            df["codigo_municipio"]
            .astype(str)
            .str.strip()
            .str.replace(r"\.0$", "", regex=True)
        )
    if "municipio" in df.columns:
        df["nome_municipio"] = (
            df["municipio"]
            .astype(str)
            .str.split(" - ", n=1)
            .str[-1]
            .str.strip()
            .str.upper()
        )
    if "populacao_estimada_ibge_2022" in df.columns:
        df["populacao_estimada_ibge_2022"] = (
            pd.to_numeric(df["populacao_estimada_ibge_2022"], errors="coerce")
            .fillna(0)
            .astype(int)
        )

    req_cols = [c for c in ["codigo_municipio", "nome_municipio"] if c in df.columns]
    uniq_cols = ["codigo_municipio"] if "codigo_municipio" in df.columns else []
    non_neg = ["populacao_estimada_ibge_2022"] if "populacao_estimada_ibge_2022" in df.columns else []
    ibge_col = "codigo_municipio" if "codigo_municipio" in df.columns else None

    return apply_quality_rules(
        df,
        required_columns=req_cols,
        unique_keys=uniq_cols,
        non_negative_columns=non_neg,
        ibge_column=ibge_col,
    )


def clean_dataframe(df: pd.DataFrame, dataset_name: str) -> pd.DataFrame:
    """Padroniza nomes de colunas para snake_case, remove duplicatas e adiciona metadados."""
    if df.empty:
        return df

    df.columns = (
        df.columns.str.strip()
        .str.lower()
        .str.replace(r"[^\w\s]", "_", regex=True)
        .str.replace(r"\s+", "_", regex=True)
    )

    df = df.drop_duplicates()
    df["_silver_processed_at"] = datetime.now(timezone.utc).isoformat()
    df["_dataset_origin"] = dataset_name

    return df


def process_dataset_silver(dataset_name: str, ano_inicio: int = 2019, ano_fim: int = 2026) -> None:
    """Varre partições ano=YYYY/mes=MM na Bronze, consolida e persiste na Silver no PostgreSQL."""
    bronze_base = Path(DATA_BRONZE_PATH) / dataset_name

    if not bronze_base.exists():
        logger.warning(f"[SILVER AVISO] Diretório Bronze para '{dataset_name}' não encontrado em {bronze_base}.")
        return

    all_dfs: List[pd.DataFrame] = []

    for ano in range(ano_inicio, ano_fim + 1):
        ano_dir = bronze_base / f"ano={ano}"
        if not ano_dir.exists():
            continue

        for mes_dir in sorted(ano_dir.glob("mes=*")):
            parquet_files = list(mes_dir.glob("*.parquet"))
            for pfile in parquet_files:
                try:
                    df_partition = pd.read_parquet(pfile)
                    if "ano" not in df_partition.columns:
                        df_partition["ano_particao"] = str(ano)
                    if "mes" not in df_partition.columns:
                        df_partition["mes_particao"] = mes_dir.name.split("=")[-1]

                    all_dfs.append(df_partition)
                except Exception as e:
                    logger.error(f"[SILVER ERRO] Falha ao ler arquivo {pfile}: {e}")

    if not all_dfs:
        logger.warning(f"[SILVER AVISO] Nenhum dado encontrado nas partições de {ano_inicio} a {ano_fim} para '{dataset_name}'.")
        return

    df_consolidated = pd.concat(all_dfs, ignore_index=True)
    df_cleaned = clean_dataframe(df_consolidated, dataset_name)

    table_name = f"silver_{dataset_name}"
    engine = get_db_engine()

    logger.info(f"Gravando {len(df_cleaned)} registros consolidados na tabela Silver '{table_name}'...")

    try:
        with engine.begin() as connection:
            connection.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE;"))

            df_cleaned.to_sql(
                name=table_name,
                con=connection,
                if_exists="replace",
                index=False,
                method="multi",
                chunksize=5000,
            )
        logger.info(f"[SILVER OK] Tabela '{table_name}' populada com sucesso ({len(df_cleaned)} linhas).")
    except Exception as exc:
        logger.error(f"[SILVER ERRO] Falha ao gravar tabela '{table_name}' no PostgreSQL: {exc}")
        raise exc


def run_all_silver_processing() -> None:
    logger.info("Iniciando processamento da camada Silver para o período de 2019 a 2026...")
    for ds in DATASETS:
        process_dataset_silver(ds, ano_inicio=2019, ano_fim=2026)
    logger.info("Processamento da camada Silver concluído com sucesso!")


def run_all_silver_processors() -> None:
    """Alias compatível com a DAG e testes de integração."""
    run_all_silver_processing()


if __name__ == "__main__":
    run_all_silver_processing()