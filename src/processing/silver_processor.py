"""
Processador da Camada Silver para o HealthData Intelligence.
Consolida os dados particionados da Bronze (2019-2026), aplica limpeza 
e carrega as tabelas limpas no PostgreSQL.
"""

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text

from src.utils.logger import get_logger

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
            # Drop com CASCADE para evitar conflitos de dependência com views/tabelas da Gold
            connection.execute(text(f"DROP TABLE IF EXISTS {table_name} CASCADE;"))
            
            df_cleaned.to_sql(
                name=table_name,
                con=connection,
                if_exists="replace",
                index=False,
                method="multi",
                chunksize=5000
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


if __name__ == "__main__":
    run_all_silver_processing()