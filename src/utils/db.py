import os
from datetime import datetime
from typing import Any, Dict

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

from src.utils.logger import get_logger

load_dotenv(override=True)
logger = get_logger("db_utils")


def safe_str_error(exc: Exception) -> str:
    try:
        return str(exc)
    except UnicodeDecodeError:
        if hasattr(exc, "args") and exc.args:
            raw = exc.args[0]
            if isinstance(raw, bytes):
                return raw.decode("cp1252", errors="replace")
        return repr(exc)


def get_db_engine() -> Engine:
    user = os.getenv("POSTGRES_USER", "healthdata_user")
    password = os.getenv("POSTGRES_PASSWORD", "healthdata_pass_local")
    host = os.getenv("POSTGRES_HOST", "127.0.0.1")
    port = os.getenv("POSTGRES_PORT", "5433")
    db = os.getenv("POSTGRES_DB", "healthdata_dw")

    conn_url = f"postgresql+psycopg2://{user}:{password}@{host}:{port}/{db}"
    return create_engine(
        conn_url,
        pool_pre_ping=True,
        connect_args={"options": "-c client_encoding=utf8"},
    )


def ensure_audit_table_exists(engine: Engine) -> None:
    statements = [
        "CREATE SCHEMA IF NOT EXISTS raw_silver;",
        "CREATE SCHEMA IF NOT EXISTS dw_gold;",
        """
        CREATE TABLE IF NOT EXISTS public.pipeline_execution_log (
            execution_id VARCHAR(64) PRIMARY KEY,
            pipeline_name VARCHAR(120) NOT NULL,
            layer VARCHAR(30) NOT NULL,
            dataset_name VARCHAR(80) NOT NULL,
            start_time TIMESTAMP WITH TIME ZONE NOT NULL,
            end_time TIMESTAMP WITH TIME ZONE,
            duration_seconds NUMERIC(10, 2),
            execution_status VARCHAR(30) NOT NULL,
            records_extracted INTEGER DEFAULT 0,
            records_processed INTEGER DEFAULT 0,
            records_rejected INTEGER DEFAULT 0,
            output_path TEXT,
            error_message TEXT,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        """,
    ]
    with engine.begin() as conn:
        for stmt in statements:
            conn.execute(text(stmt))


def log_pipeline_execution(metrics: Dict[str, Any]) -> None:
    try:
        engine = get_db_engine()
        ensure_audit_table_exists(engine)

        start_time: datetime = metrics["start_time"]
        end_time: datetime = metrics["end_time"]
        duration = round((end_time - start_time).total_seconds(), 2)

        insert_sql = text(
            """
            INSERT INTO public.pipeline_execution_log (
                execution_id, pipeline_name, layer, dataset_name,
                start_time, end_time, duration_seconds, execution_status,
                records_extracted, records_processed, records_rejected,
                output_path, error_message
            ) VALUES (
                :execution_id, :pipeline_name, :layer, :dataset_name,
                :start_time, :end_time, :duration_seconds, :execution_status,
                :records_extracted, :records_processed, :records_rejected,
                :output_path, :error_message
            )
            ON CONFLICT (execution_id) DO UPDATE SET
                end_time = EXCLUDED.end_time,
                duration_seconds = EXCLUDED.duration_seconds,
                execution_status = EXCLUDED.execution_status,
                records_extracted = EXCLUDED.records_extracted,
                records_processed = EXCLUDED.records_processed,
                records_rejected = EXCLUDED.records_rejected,
                output_path = EXCLUDED.output_path,
                error_message = EXCLUDED.error_message;
            """
        )

        payload = {
            "execution_id": metrics["execution_id"],
            "pipeline_name": metrics.get("pipeline_name", "healthdata_pipeline"),
            "layer": metrics.get("layer", "BRONZE"),
            "dataset_name": metrics["dataset_name"],
            "start_time": start_time,
            "end_time": end_time,
            "duration_seconds": duration,
            "execution_status": metrics["execution_status"],
            "records_extracted": int(metrics.get("records_extracted", 0)),
            "records_processed": int(metrics.get("records_processed", 0)),
            "records_rejected": int(metrics.get("records_rejected", 0)),
            "output_path": metrics.get("output_path"),
            "error_message": metrics.get("error_message"),
        }

        with engine.begin() as conn:
            conn.execute(insert_sql, payload)

        logger.info(
            f"[AUDITORIA PG] {metrics['layer']} | {metrics['dataset_name']} | "
            f"Status: {metrics['execution_status']} | Extraídos: {payload['records_extracted']} | "
            f"Processados: {payload['records_processed']} | Rejeitados: {payload['records_rejected']}"
        )
    except Exception as exc:
        logger.warning(f"[AUDITORIA PG AVISO] Falha ao gravar log: {safe_str_error(exc)}")
