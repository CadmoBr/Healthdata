import json
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import httpx
import pandas as pd
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from src.utils.db import log_pipeline_execution, safe_str_error
from src.utils.logger import get_logger

load_dotenv(override=True)
logger = get_logger("bronze_extractor")

SUS_API_BASE_URL = os.getenv("SUS_API_BASE_URL", "https://apidadosabertos.saude.gov.br")
DATA_BRONZE_PATH = os.getenv("DATA_BRONZE_PATH", "data/bronze")
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT_SECONDS", "45"))

BRONZE_DATASETS_CONFIG: Dict[str, Dict[str, Any]] = {
    "municipios_saude": {
        "endpoint": "/macrorregiao-e-regiao-de-saude/municipio",
        "json_key": "macrorregiao_regiao_saude_municipios",
        "default_params": {},
    },
    "cnes_estabelecimentos": {
        "endpoint": "/cnes/estabelecimentos",
        "json_key": "estabelecimentos",
        "default_params": {"codigo_uf": 23},
    },
    "hospitais_e_leitos": {
        "endpoint": "/assistencia-a-saude/hospitais-e-leitos",
        "json_key": "hospitais_leitos",
        "default_params": {},
    },
    "cnes_leitos_historico": {
        "endpoint": "/assistencia-a-saude/cnes-leitos",
        "json_key": "cnes_leitos",
        "default_params": {},
    },
    "sih_producao_hospitalar": {
        "endpoint": "/assistencia-a-saude/sih-procedimentos-hospitalares",
        "json_key": "sih_procedimentos_hospitalares",
        "default_params": {},
    },
}


@retry(
    stop=stop_after_attempt(4),
    wait=wait_exponential(multiplier=1, min=2, max=15),
    reraise=True,
)
def fetch_page(
    client: httpx.Client, endpoint: str, params: Dict[str, Any]
) -> Dict[str, Any] | List[Any]:
    response = client.get(endpoint, params=params)
    response.raise_for_status()
    return response.json()


def extract_dataset_to_bronze(
    dataset_name: str,
    max_pages: int = 3,
    page_size: int = 20,
    custom_params: Dict[str, Any] | None = None,
    partition_year: str | None = None,
    partition_month: str | None = None,
) -> Dict[str, Any]:
    if dataset_name not in BRONZE_DATASETS_CONFIG:
        raise ValueError(f"Dataset '{dataset_name}' não configurado.")

    cfg = BRONZE_DATASETS_CONFIG[dataset_name]
    endpoint = cfg["endpoint"]
    json_key = cfg["json_key"]

    execution_id = f"brz_{dataset_name}_{uuid.uuid4().hex[:8]}"
    start_time = datetime.now(timezone.utc)

    now_year = partition_year or start_time.strftime("%Y")
    now_month = partition_month or start_time.strftime("%m")

    query_base = {**cfg["default_params"], **(custom_params or {})}
    all_records: List[Dict[str, Any]] = []

    logger.info(f"Iniciando extração BRONZE | Dataset: {dataset_name} | Partição: ano={now_year}/mes={now_month} | Endpoint: {endpoint}")

    headers = {
        "Accept": "application/json",
        "User-Agent": "HealthData-Intelligence-Pipeline/1.0",
    }

    try:
        with httpx.Client(
            base_url=SUS_API_BASE_URL, timeout=HTTP_TIMEOUT, headers=headers, follow_redirects=True
        ) as client:
            for page_idx in range(max_pages):
                offset_val = page_idx + 1
                params = {**query_base, "limit": page_size, "offset": offset_val}

                payload = fetch_page(client, endpoint, params)

                if isinstance(payload, dict):
                    page_records = payload.get(json_key, [])
                elif isinstance(payload, list):
                    page_records = payload
                else:
                    page_records = []

                if not page_records:
                    logger.info(f"Página {page_idx + 1} sem novos registros para {dataset_name}.")
                    break

                all_records.extend(page_records)
                logger.info(
                    f"  -> Página {page_idx + 1}/{max_pages} extraída ({len(page_records)} registros | "
                    f"Acumulado: {len(all_records)})"
                )

        if not all_records:
            raise RuntimeError(f"Nenhum registro retornado pelo endpoint {endpoint}.")

        df = pd.DataFrame(all_records)
        df["_execution_id"] = execution_id
        df["_extracted_at_utc"] = start_time.isoformat()
        df["_source_endpoint"] = endpoint
        df["_query_params"] = json.dumps(query_base, ensure_ascii=False)

        partition_dir = (
            Path(DATA_BRONZE_PATH) / dataset_name / f"ano={now_year}" / f"mes={now_month}"
        )
        partition_dir.mkdir(parents=True, exist_ok=True)

        for old_file in partition_dir.glob("*.parquet"):
            old_file.unlink()

        file_stamp = start_time.strftime("%Y%m%d_%H%M%S")
        output_file = partition_dir / f"{dataset_name}_{file_stamp}_{execution_id[-4:]}.parquet"

        df.to_parquet(output_file, engine="pyarrow", compression="snappy", index=False)

        end_time = datetime.now(timezone.utc)
        metrics = {
            "execution_id": execution_id,
            "pipeline_name": "healthdata_bronze_ingestion",
            "layer": "BRONZE",
            "dataset_name": dataset_name,
            "start_time": start_time,
            "end_time": end_time,
            "execution_status": "SUCCESS",
            "records_extracted": len(df),
            "records_processed": len(df),
            "records_rejected": 0,
            "output_path": str(output_file),
            "error_message": None,
        }
        log_pipeline_execution(metrics)
        logger.info(f"[BRONZE OK] {dataset_name} ({now_year}/{now_month}): {len(df)} registros salvos em '{output_file}'.")
        return metrics

    except Exception as exc:
        end_time = datetime.now(timezone.utc)
        error_msg = safe_str_error(exc)
        logger.error(f"[BRONZE ERRO] Falha ao extrair {dataset_name} ({now_year}/{now_month}): {error_msg}")

        metrics = {
            "execution_id": execution_id,
            "pipeline_name": "healthdata_bronze_ingestion",
            "layer": "BRONZE",
            "dataset_name": dataset_name,
            "start_time": start_time,
            "end_time": end_time,
            "execution_status": "FAILED",
            "records_extracted": len(all_records),
            "records_processed": 0,
            "records_rejected": 0,
            "output_path": None,
            "error_message": error_msg[:500],
        }
        log_pipeline_execution(metrics)
        return metrics


def gerar_intervalo_competencias(ano_inicio: int = 2019, ano_fim: int = 2026, mes_fim: int = 10) -> List[tuple]:
    """Gera lista de tuplas (ano_str, mes_str) abrangendo o período desejado."""
    competencias = []
    for ano in range(ano_inicio, ano_fim + 1):
        limite_mes = mes_fim if ano == ano_fim else 12
        for mes in range(1, limite_mes + 1):
            competencias.append((str(ano), f"{mes:02d}"))
    return competencias


def run_historical_backfill(ano_inicio: int = 2019, ano_fim: int = 2026, mes_fim: int = 10) -> List[Dict[str, Any]]:
    """Executa a extração em lote para todas as competências no intervalo especificado."""
    results = []
    competencias = gerar_intervalo_competencias(ano_inicio, ano_fim, mes_fim)
    
    logger.info(f"Iniciando Backfill Histórico Bronze de {ano_inicio} a {ano_fim} ({len(competencias)} competências mensais).")

    for ano, mes in competencias:
        for ds_name in BRONZE_DATASETS_CONFIG.keys():
            res = extract_dataset_to_bronze(
                dataset_name=ds_name,
                max_pages=3,
                page_size=20,
                partition_year=ano,
                partition_month=mes
            )
            results.append(res)
            
    return results


if __name__ == "__main__":
    # Executa o backfill completo cobrindo de 2019 até outubro de 2026
    run_historical_backfill(ano_inicio=2019, ano_fim=2026, mes_fim=10)