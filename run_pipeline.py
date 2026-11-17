"""
Orquestrador Completo do Pipeline HealthData Intelligence (2019-2026)
Executa em sequência: Ingestão Bronze -> Processamento Silver -> dbt (Gold) -> Machine Learning
"""

import os
import subprocess
import sys
from pathlib import Path
from src.utils.logger import get_logger

logger = get_logger("pipeline_orchestrator")

# Define a raiz do projeto
ROOT_DIR = Path(__file__).parent.resolve()
DBT_DIR = ROOT_DIR / "dbt"


def run_command(command: list[str], description: str, cwd: Path | None = None) -> None:
    logger.info(f"=== INICIANDO: {description} ===")
    
    env = os.environ.copy()
    python_path = str(ROOT_DIR)
    if "PYTHONPATH" in env:
        env["PYTHONPATH"] = f"{python_path}{os.pathsep}{env['PYTHONPATH']}"
    else:
        env["PYTHONPATH"] = python_path

    try:
        subprocess.run(command, check=True, text=True, capture_output=False, env=env, cwd=cwd)
        logger.info(f"=== SUCESSO: {description} ===")
    except subprocess.CalledProcessError as e:
        logger.error(f"=== FALHA em: {description} ===")
        sys.exit(1)


if __name__ == "__main__":
    logger.info("Iniciando execução completa do pipeline HealthData (2019-2026)...")

    # 1. Ingestão Bronze (Backfill Histórico SIH/SUS)
    run_command(
        [sys.executable, "src/ingestion/sih_historical_backfill.py"],
        "Backfill Histórico Bronze (SIH/SUS)",
        cwd=ROOT_DIR
    )

    # 2. Processamento Silver (Limpeza e Carga no PostgreSQL)
    run_command(
        [sys.executable, "src/processing/silver_processor.py"],
        "Processamento da Camada Silver",
        cwd=ROOT_DIR
    )

    # 3. Modelagem Gold via dbt (Star Schema) - Rodando dentro da pasta dbt
    run_command(
        ["dbt", "run", "--full-refresh", "--profiles-dir", ".."],
        "Atualização do Star Schema na Camada Gold (dbt)",
        cwd=DBT_DIR
    )

    # 4. Testes Automatizados do dbt
    run_command(
        ["dbt", "test", "--profiles-dir", ".."],
        "Validação de Integridade e Testes dbt",
        cwd=DBT_DIR
    )

    # 5. Treinamento do Modelo de Machine Learning (Forecasting)
    run_command(
        [sys.executable, "ml/src/demand_forecasting.py"],
        "Treinamento do Modelo de Forecasting (RandomForest)",
        cwd=ROOT_DIR
    )

    logger.info("🎉 Pipeline completo executado com sucesso de ponta a ponta!")