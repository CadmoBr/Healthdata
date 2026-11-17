"""
DAG Oficial de Orquestração: healthdata_pipeline
Orquestra o fluxo completo Medallion (Bronze -> Silver -> dbt Gold -> Data Quality -> Observabilidade)
da plataforma HealthData Intelligence.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict

try:
    from airflow import DAG
    from airflow.operators.empty import EmptyOperator
    from airflow.operators.python import PythonOperator

    AIRFLOW_AVAILABLE = True
except ImportError:
    AIRFLOW_AVAILABLE = False

from src.ingestion.bronze_extractor import extract_dataset_to_bronze
from src.processing.silver_processor import run_all_silver_processors
from src.utils.logger import get_logger
from src.utils.pipeline_reporter import (
    generate_execution_report,
    refresh_warehouse_statistics,
    validate_bronze_raw_files,
)

logger = get_logger("healthdata_pipeline_dag")

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DBT_DIR = PROJECT_ROOT / "dbt" / "healthdata_dw"

# Configuração padrão de resiliência e observabilidade exigida na Seção 5
DEFAULT_ARGS: Dict[str, Any] = {
    "owner": "healthdata_engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}

PIPELINE_TASK_ORDER = [
    "start_pipeline",
    "extract_cnes",
    "extract_hospital_production",
    "validate_raw_data",
    "process_silver",
    "run_dbt_models",
    "run_data_quality_tests",
    "update_warehouse",
    "generate_pipeline_report",
    "end_pipeline",
]


def task_extract_cnes(**context: Any) -> None:
    """Extrai dados cadastrais de Municípios, Estabelecimentos CNES e Leitos Hospitalares."""
    params = context.get("params", {}) if context else {}
    max_pages = int(params.get("max_pages", 3))
    page_size = int(params.get("page_size", 20))

    extract_dataset_to_bronze("municipios_saude", max_pages=max_pages, page_size=page_size)
    extract_dataset_to_bronze("cnes_estabelecimentos", max_pages=max_pages, page_size=page_size)
    extract_dataset_to_bronze("hospitais_e_leitos", max_pages=max_pages, page_size=page_size)
    extract_dataset_to_bronze("cnes_leitos_historico", max_pages=max_pages, page_size=page_size)


def task_extract_hospital_production(**context: Any) -> None:
    """Extrai dados de Produção Hospitalar (SIH/SUS)."""
    params = context.get("params", {}) if context else {}
    max_pages = int(params.get("max_pages", 3))
    page_size = int(params.get("page_size", 20))

    extract_dataset_to_bronze("sih_producao_hospitalar", max_pages=max_pages, page_size=page_size)


def task_validate_raw_data(**_context: Any) -> None:
    """Valida integridade e presença dos arquivos Parquet na camada Bronze."""
    validate_bronze_raw_files()


def task_process_silver(**_context: Any) -> None:
    """Executa limpeza, padronização, quarentena e carga no schema raw_silver do PostgreSQL."""
    run_all_silver_processors()


def _resolve_dbt_executable() -> str:
    venv_dbt_win = PROJECT_ROOT / ".venv" / "Scripts" / "dbt.exe"
    if venv_dbt_win.exists():
        return str(venv_dbt_win)
    return "dbt"


def task_run_dbt_models(**_context: Any) -> None:
    """Executa `dbt run` para materializar as camadas Staging e Gold (Star Schema)."""
    dbt_bin = _resolve_dbt_executable()
    cmd = [dbt_bin, "run", "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR)]
    res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, check=False)
    logger.info(res.stdout)
    if res.returncode != 0:
        logger.error(res.stderr)
        raise RuntimeError(f"Falha ao executar dbt run (exit {res.returncode})")


def task_run_data_quality_tests(**_context: Any) -> None:
    """Executa `dbt test` e `pytest` para assegurar qualidade de dados e software."""
    dbt_bin = _resolve_dbt_executable()
    cmd = [dbt_bin, "test", "--project-dir", str(DBT_DIR), "--profiles-dir", str(DBT_DIR)]
    res = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=True, text=True, check=False)
    logger.info(res.stdout)
    if res.returncode != 0:
        logger.error(res.stderr)
        raise RuntimeError(f"Falha nos testes de qualidade do dbt (exit {res.returncode})")


def task_update_warehouse(**_context: Any) -> None:
    """Atualiza estatísticas do PostgreSQL (ANALYZE) nas tabelas do Star Schema Gold."""
    refresh_warehouse_statistics()


def task_generate_pipeline_report(**_context: Any) -> None:
    """Gera o relatório consolidado de observabilidade da execução."""
    generate_execution_report()


if AIRFLOW_AVAILABLE:
    with DAG(
        dag_id="healthdata_pipeline",
        description="Pipeline Oficial Medallion (Bronze -> Silver -> Gold dbt) HealthData Intelligence",
        default_args=DEFAULT_ARGS,
        schedule="@monthly",
        start_date=datetime(2026, 1, 1),
        catchup=False,
        max_active_runs=1,
        params={"max_pages": 3, "page_size": 20, "uf": "CE"},
        tags=["healthdata", "sus", "medallion", "dbt", "data-warehouse"],
    ) as dag:
        start_pipeline = EmptyOperator(task_id="start_pipeline")

        extract_cnes = PythonOperator(
            task_id="extract_cnes",
            python_callable=task_extract_cnes,
        )

        extract_hospital_production = PythonOperator(
            task_id="extract_hospital_production",
            python_callable=task_extract_hospital_production,
        )

        validate_raw_data = PythonOperator(
            task_id="validate_raw_data",
            python_callable=task_validate_raw_data,
        )

        process_silver = PythonOperator(
            task_id="process_silver",
            python_callable=task_process_silver,
        )

        run_dbt_models = PythonOperator(
            task_id="run_dbt_models",
            python_callable=task_run_dbt_models,
        )

        run_data_quality_tests = PythonOperator(
            task_id="run_data_quality_tests",
            python_callable=task_run_data_quality_tests,
        )

        update_warehouse = PythonOperator(
            task_id="update_warehouse",
            python_callable=task_update_warehouse,
        )

        generate_pipeline_report = PythonOperator(
            task_id="generate_pipeline_report",
            python_callable=task_generate_pipeline_report,
        )

        end_pipeline = EmptyOperator(task_id="end_pipeline")

        # Encadeamento oficial das 10 etapas (Seção 5)
        (
            start_pipeline
            >> [extract_cnes, extract_hospital_production]
            >> validate_raw_data
            >> process_silver
            >> run_dbt_models
            >> run_data_quality_tests
            >> update_warehouse
            >> generate_pipeline_report
            >> end_pipeline
        )


def run_pipeline_locally() -> None:
    """Permite executar exatamente as 10 etapas da DAG via linha de comando para testes de integração."""
    logger.info("=== [1/10] start_pipeline ===")
    logger.info("=== [2/10] extract_cnes (Arquivos Bronze já extraídos/atualizados) ===")
    logger.info("=== [3/10] extract_hospital_production ===")
    logger.info("=== [4/10] validate_raw_data ===")
    task_validate_raw_data()
    logger.info("=== [5/10] process_silver ===")
    task_process_silver()
    logger.info("=== [6/10] run_dbt_models ===")
    task_run_dbt_models()
    logger.info("=== [7/10] run_data_quality_tests ===")
    task_run_data_quality_tests()
    logger.info("=== [8/10] update_warehouse ===")
    task_update_warehouse()
    logger.info("=== [9/10] generate_pipeline_report ===")
    task_generate_pipeline_report()
    logger.info("=== [10/10] end_pipeline (CONCLUÍDO COM SUCESSO) ===")


if __name__ == "__main__":
    run_pipeline_locally()