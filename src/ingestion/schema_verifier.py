import json
import httpx
from src.utils.logger import get_logger

logger = get_logger("schema_verifier")
BASE_URL = "https://apidadosabertos.saude.gov.br"

TARGET_ENDPOINTS = [
    "/cnes/estabelecimentos",
    "/assistencia-a-saude/cnes-estabelecimentos",
    "/assistencia-a-saude/cnes-leitos",
    "/assistencia-a-saude/hospitais-e-leitos",
    "/assistencia-a-saude/sih-procedimentos-hospitalares",
    "/assistencia-a-saude/sia-procedimentos-ambulatoriais",
    "/macrorregiao-e-regiao-de-saude/municipio",
]

def verify_target_endpoints():
    with open("docs/openapi_full_spec.json", "r", encoding="utf-8") as f:
        spec = json.load(f)

    verified_report = {}

    with httpx.Client(base_url=BASE_URL, timeout=45.0, follow_redirects=True) as client:
        for ep in TARGET_ENDPOINTS:
            ep_spec = spec.get("paths", {}).get(ep, {}).get("get", {})
            params_spec = [
                {
                    "name": p.get("name"),
                    "in": p.get("in"),
                    "required": p.get("required", False),
                    "type": p.get("type") or p.get("schema", {}).get("type"),
                    "description": p.get("description", ""),
                }
                for p in ep_spec.get("parameters", [])
            ]

            print("\n=======================================================")
            print(f"ENDPOINT: {ep}")
            print(f"Parâmetros documentados no Swagger: {[p['name'] for p in params_spec]}")

            # Monta parâmetros básicos de teste (limit=5, offset=1 ou equivalentes)
            query_params = {"limit": 5, "offset": 1}
            try:
                resp = client.get(ep, params=query_params)
                print(f"Status HTTP: {resp.status_code}")

                if resp.status_code == 200:
                    data = resp.json()
                    records = []
                    data_key = None
                    if isinstance(data, dict):
                        for k, v in data.items():
                            if isinstance(v, list):
                                records = v
                                data_key = k
                                break
                    elif isinstance(data, list):
                        records = data
                        data_key = "<root_list>"

                    fields = list(records[0].keys()) if records else []
                    print(f"Chave da lista JSON: '{data_key}' | Registros recebidos: {len(records)}")
                    print(f"Colunas reais ({len(fields)}): {fields}")
                    if records:
                        print(f"Exemplo registro[0]: {json.dumps(records[0], ensure_ascii=False)[:300]}...")

                    verified_report[ep] = {
                        "http_status": resp.status_code,
                        "swagger_parameters": params_spec,
                        "json_data_key": data_key,
                        "fields": fields,
                        "sample_record": records[0] if records else None,
                    }
                else:
                    print(f"Resposta não-200: {resp.text[:250]}")
                    verified_report[ep] = {
                        "http_status": resp.status_code,
                        "swagger_parameters": params_spec,
                        "error_preview": resp.text[:250],
                    }
            except Exception as exc:
                print(f"Erro ao requisitar {ep}: {exc}")
                verified_report[ep] = {
                    "swagger_parameters": params_spec,
                    "exception": str(exc),
                }

    with open("docs/verified_endpoints_schema.json", "w", encoding="utf-8") as f:
        json.dump(verified_report, f, ensure_ascii=False, indent=2)
    print("\nRelatório detalhado salvo em: docs/verified_endpoints_schema.json")

if __name__ == "__main__":
    verify_target_endpoints()
