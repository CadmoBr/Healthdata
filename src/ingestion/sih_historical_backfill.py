"""
Backfill Histórico Real do SIH/SUS por Competência (nu_comp).
Consulta o endpoint oficial `/assistencia-a-saude/sih-procedimentos-hospitalares`
para o intervalo de 2019 a 2026, persiste na Camada Bronze particionada por ano/mês
e alimenta as camadas Silver e Gold (`dw_gold.fact_hospital_production`).
"""

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

from src.utils.db import log_pipeline_execution
from src.utils.logger import get_logger

load_dotenv(override=False)
logger = get_logger("sih_historical_backfill")

SUS_API_BASE_URL = os.getenv("SUS_API_BASE_URL", "https://apidadosabertos.saude.gov.br")
DATA_BRONZE_PATH = Path(os.getenv("DATA_BRONZE_PATH", "data/bronze"))


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=1, max=8), reraise=True)
def fetch_sih_competencia(
    client: httpx.Client, nu_comp: int, offset: int = 0, limit: int = 20
) -> List[Dict[str, Any]]:
    """Consulta uma página de uma competência específica (YYYYMM) no endpoint oficial do SIH/SUS."""
    resp = client.get(
        "/assistencia-a-saude/sih-procedimentos-hospitalares",
        params={"nu_comp": nu_comp, "limit": limit, "offset": offset},
    )
    resp.raise_for_status()
    payload = resp.json()
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        records = payload.get("sih_procedimentos_hospitalares", [])
        return records if isinstance(records, list) else []
    return []


def run_sih_real_historical_backfill(ano_inicio: int = 2019, ano_fim: int = 2026, mes_fim: int = 10) -> List[Path]:
    """Extrai dados reais do SIH/SUS para todas as competências mensais de ano_inicio até ano_fim."""
    competencias = []
    for ano in range(ano_inicio, ano_fim + 1):
        limite_mes = mes_fim if ano == ano_fim else 12
        for mes in range(1, limite_mes + 1):
            competencias.append(int(f"{ano}{mes:02d}"))

    execution_id = f"brz_sih_hist_{uuid.uuid4().hex[:8]}"
    start_time = datetime.now(timezone.utc)
    saved_files: List[Path] = []

    headers = {
        "Accept": "application/json",
        "User-Agent": "HealthData-Intelligence-Pipeline/1.0",
    }

    logger.info(f"Iniciando backfill histórico real do SIH/SUS de {ano_inicio} a {ano_fim} ({len(competencias)} competências)...")

    with httpx.Client(
        base_url=SUS_API_BASE_URL, timeout=30.0, headers=headers, follow_redirects=True
    ) as client:
        for comp in competencias:
            comp_records: List[Dict[str, Any]] = []
            for off in range(0, 80, 20):
                try:
                    batch = fetch_sih_competencia(client, nu_comp=comp, offset=off, limit=20)
                    if not batch:
                        break
                    comp_records.extend(batch)
                except Exception as exc:
                    logger.warning(f"Aviso em nu_comp={comp} (offset={off}): {exc}")
                    break

            if comp_records:
                df_comp = pd.DataFrame(comp_records)
                
                # Extrai ano e mês da própria competência (ex: 201901 -> ano=2019, mes=01)
                comp_str = str(comp)
                ano_str = comp_str[:4]
                mes_str = comp_str[4:]

                df_comp["_execution_id"] = execution_id
                df_comp["_extracted_at_utc"] = start_time.isoformat()
                df_comp["_source_endpoint"] = "/assistencia-a-saude/sih-procedimentos-hospitalares"
                df_comp["_query_params"] = json.dumps({"nu_comp": comp}, ensure_ascii=False)

                partition_dir = (
                    DATA_BRONZE_PATH
                    / "sih_producao_hospitalar"
                    / f"ano={ano_str}"
                    / f"mes={mes_str}"
                )
                partition_dir.mkdir(parents=True, exist_ok=True)

                out_file = partition_dir / f"sih_producao_hospitalar_{comp}_{execution_id[-4:]}.parquet"
                df_comp.to_parquet(out_file, engine="pyarrow", compression="snappy", index=False)
                saved_files.append(out_file)

                logger.info(
                    f"  -> Competência {comp}: {len(comp_records)} registros salvos em '{out_file}'."
                )

                # Log de auditoria da execução por competência
                log_pipeline_execution(
                    {
                        "execution_id": execution_id,
                        "pipeline_name": "healthdata_bronze_sih_backfill",
                        "layer": "BRONZE",
                        "dataset_name": "sih_producao_hospitalar",
                        "start_time": start_time,
                        "end_time": datetime.now(timezone.utc),
                        "execution_status": "SUCCESS",
                        "records_extracted": len(df_comp),
                        "records_processed": len(df_comp),
                        "records_rejected": 0,
                        "output_path": str(out_file),
                        "error_message": None,
                    }
                )

    if not saved_files:
        raise RuntimeError("Nenhum registro retornado pela API do SUS no backfill do SIH.")

    logger.info(f"[BACKFILL SIH CONCLUÍDO] {len(saved_files)} arquivos mensais gerados na camada Bronze.")
    return saved_files


if __name__ == "__main__":
    run_sih_real_historical_backfill(ano_inicio=2019, ano_fim=2026, mes_fim=10)