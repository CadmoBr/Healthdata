import json
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import httpx
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential

from src.utils.logger import get_logger

load_dotenv()

logger = get_logger("api_discovery")

SUS_API_BASE_URL = os.getenv("SUS_API_BASE_URL", "https://apidadosabertos.saude.gov.br")
DATASUS_CKAN_API_URL = os.getenv(
    "DATASUS_CKAN_API_URL", "https://dadosabertos.saude.gov.br/api/3/action"
)
HTTP_TIMEOUT = int(os.getenv("HTTP_TIMEOUT_SECONDS", "30"))


@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    reraise=True,
)
def fetch_json_with_retry(
    client: httpx.Client, url: str, params: Dict[str, Any] | None = None
) -> httpx.Response:
    response = client.get(url, params=params)
    response.raise_for_status()
    return response


def inspect_payload_structure(payload: Any) -> Dict[str, Any]:
    if isinstance(payload, dict):
        top_keys = list(payload.keys())
        for key, value in payload.items():
            if isinstance(value, list) and len(value) > 0 and isinstance(value[0], dict):
                return {
                    "payload_type": "dict_with_list",
                    "root_keys": top_keys,
                    "data_key": key,
                    "sample_record_count": len(value),
                    "fields": list(value[0].keys()),
                    "sample_first_record": value[0],
                }
        return {
            "payload_type": "dict",
            "root_keys": top_keys,
            "sample_content": {k: str(v)[:120] for k, v in list(payload.items())[:5]},
        }
    elif isinstance(payload, list) and len(payload) > 0 and isinstance(payload[0], dict):
        return {
            "payload_type": "list_of_dicts",
            "sample_record_count": len(payload),
            "fields": list(payload[0].keys()),
            "sample_first_record": payload[0],
        }
    return {"payload_type": str(type(payload)), "raw_preview": str(payload)[:200]}


def discover_sus_rest_endpoints(client: httpx.Client) -> List[Dict[str, Any]]:
    candidate_endpoints = [
        {
            "name": "CNES - Estabelecimentos de Saúde",
            "path": "/cnes/estabelecimentos",
            "params": {"limit": 5, "offset": 1},
        },
        {
            "name": "CNES - Tipologias de Leitos / Leitos Hospitalares",
            "path": "/cnes/tipologias-leitos",
            "params": {"limit": 5, "offset": 1},
        },
        {
            "name": "CNES - Leitos",
            "path": "/cnes/leitos",
            "params": {"limit": 5, "offset": 1},
        },
    ]

    results = []
    for ep in candidate_endpoints:
        url = f"{SUS_API_BASE_URL.rstrip('/')}{ep['path']}"
        logger.info(f"Testando endpoint REST SUS: {ep['name']} -> {url}")
        start_time = time.perf_counter()

        try:
            response = fetch_json_with_retry(client, url, params=ep["params"])
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            payload = response.json()
            structure = inspect_payload_structure(payload)

            logger.info(
                f"[SUCESSO] {ep['path']} | HTTP {response.status_code} | "
                f"{elapsed_ms} ms | Campos detectados: {structure.get('fields', structure.get('root_keys'))}"
            )
            results.append(
                {
                    "endpoint_name": ep["name"],
                    "url": url,
                    "params_tested": ep["params"],
                    "status": "AVAILABLE",
                    "http_status": response.status_code,
                    "latency_ms": elapsed_ms,
                    "structure": structure,
                }
            )
        except Exception as exc:
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.warning(f"[FALHA/INDISPONÍVEL] {ep['path']} | Erro: {exc}")
            results.append(
                {
                    "endpoint_name": ep["name"],
                    "url": url,
                    "params_tested": ep["params"],
                    "status": "UNAVAILABLE_OR_ERROR",
                    "latency_ms": elapsed_ms,
                    "error": str(exc),
                }
            )

    return results


def discover_ckan_datasets(client: httpx.Client) -> List[Dict[str, Any]]:
    search_queries = ["cnes", "sih", "leitos", "producao hospitalar"]
    ckan_results = []

    for query in search_queries:
        url = f"{DATASUS_CKAN_API_URL.rstrip('/')}/package_search"
        params = {"q": query, "rows": 3}
        logger.info(f"Consultando catálogo CKAN Dados Abertos para termo: '{query}'")
        start_time = time.perf_counter()

        try:
            response = fetch_json_with_retry(client, url, params=params)
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            payload = response.json()

            packages = payload.get("result", {}).get("results", [])
            summarized_packages = []
            for pkg in packages:
                resources = [
                    {
                        "name": r.get("name"),
                        "format": r.get("format"),
                        "url": r.get("url"),
                    }
                    for r in pkg.get("resources", [])[:3]
                ]
                summarized_packages.append(
                    {
                        "id": pkg.get("id"),
                        "name": pkg.get("name"),
                        "title": pkg.get("title"),
                        "sample_resources": resources,
                    }
                )

            logger.info(
                f"[CKAN OK] Termo '{query}' retornou {len(summarized_packages)} pacotes ({elapsed_ms} ms)."
            )
            ckan_results.append(
                {
                    "search_term": query,
                    "status": "AVAILABLE",
                    "latency_ms": elapsed_ms,
                    "packages_found": summarized_packages,
                }
            )
        except Exception as exc:
            logger.warning(f"[CKAN AVISO] Falha ao consultar termo '{query}': {exc}")
            ckan_results.append(
                {
                    "search_term": query,
                    "status": "UNAVAILABLE_OR_ERROR",
                    "error": str(exc),
                }
            )

    return ckan_results


def run_discovery() -> Dict[str, Any]:
    logger.info("Iniciando Descoberta e Validação das Fontes de Dados Oficiais do SUS...")

    headers = {
        "Accept": "application/json",
        "User-Agent": "HealthData-Intelligence-DataEngineering/1.0",
    }

    with httpx.Client(timeout=HTTP_TIMEOUT, headers=headers, follow_redirects=True) as client:
        rest_report = discover_sus_rest_endpoints(client)
        ckan_report = discover_ckan_datasets(client)

    report = {
        "discovery_timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "sus_rest_api_base": SUS_API_BASE_URL,
        "ckan_api_base": DATASUS_CKAN_API_URL,
        "rest_endpoints_analysis": rest_report,
        "ckan_catalog_analysis": ckan_report,
    }

    output_path = Path("docs/api_discovery_report.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    logger.info(f"Relatório técnico de descoberta salvo com sucesso em: {output_path}")
    return report


if __name__ == "__main__":
    run_discovery()
