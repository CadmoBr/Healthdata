"""
Módulo de Validação de Pipeline e Geração de Relatório de Observabilidade.
Utilizado pelas tasks `validate_raw_data`, `update_warehouse` e `generate_pipeline_report`
da DAG `healthdata_pipeline`.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

import pandas as pd
from sqlalchemy import text

from src.utils.db import get_db_engine
from src.utils.logger import get_logger

logger = get_logger("pipeline_reporter")
DATA_BRONZE_PATH = Path(os.getenv("DATA_BRONZE_PATH", "data/bronze"))


def validate_bronze_raw_files() -> Dict[str, int]:
    """Verifica se todos os 5 datasets prioritários possuem arquivos Parquet válidos na camada Bronze."""
    expected_datasets = [
        "municipios_saude",
        "cnes_estabelecimentos",
        "hospitais_e_leitos",
        "cnes_leitos_historico",
        "sih_producao_hospitalar",
    ]
    summary: Dict[str, int] = {}
    for ds in expected_datasets:
        files = list((DATA_BRONZE_PATH / ds).rglob("*.parquet"))
        if not files:
            raise FileNotFoundError(f"[VALIDAÇÃO BRONZE FALHOU] Nenhum Parquet encontrado para '{ds}'.")
        total_rows = sum(len(pd.read_parquet(f)) for f in files)
        if total_rows <= 0:
            raise ValueError(f"[VALIDAÇÃO BRONZE FALHOU] Dataset '{ds}' está vazio (0 linhas).")
        summary[ds] = total_rows
        logger.info(f"[VALIDAÇÃO BRONZE OK] {ds}: {total_rows} registros brutos verificados.")
    return summary


def refresh_warehouse_statistics() -> Dict[str, int]:
    """Executa ANALYZE nas tabelas do schema dw_gold e retorna a contagem atualizada de registros."""
    gold_tables = [
        "dim_date",
        "dim_municipality",
        "dim_health_facility",
        "dim_procedure",
        "fact_hospital_beds",
        "fact_hospital_production",
    ]
    engine = get_db_engine()
    counts: Dict[str, int] = {}
    with engine.begin() as conn:
        for tbl in gold_tables:
            conn.execute(text(f"ANALYZE dw_gold.{tbl};"))
            cnt = conn.execute(text(f"SELECT COUNT(*) FROM dw_gold.{tbl};")).scalar()
            counts[f"dw_gold.{tbl}"] = int(cnt or 0)
            logger.info(f"[WAREHOUSE GOLD ATUALIZADO] dw_gold.{tbl}: {counts[f'dw_gold.{tbl}']} linhas.")
    return counts


def generate_execution_report() -> Dict[str, Any]:
    """Gera um relatório consolidado da execução do pipeline a partir do PostgreSQL."""
    engine = get_db_engine()
    gold_counts = refresh_warehouse_statistics()

    df_logs = pd.read_sql(
        """
        SELECT execution_id, pipeline_name, layer, dataset_name,
               execution_status, records_extracted, records_processed,
               records_rejected, duration_seconds
        FROM public.pipeline_execution_log
        ORDER BY start_time DESC
        LIMIT 15
        """,
        engine,
    )

    report = {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "pipeline_name": "healthdata_pipeline",
        "gold_warehouse_row_counts": gold_counts,
        "recent_audit_logs": df_logs.to_dict(orient="records"),
    }

    report_path = Path("docs/latest_pipeline_report.json")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info(f"[RELATÓRIO GERADO] Salvo em: {report_path}")
    return report


if __name__ == "__main__":
    validate_bronze_raw_files()
    generate_execution_report()