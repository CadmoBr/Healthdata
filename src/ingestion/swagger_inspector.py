import re
import json
import httpx

BASE_URL = "https://apidadosabertos.saude.gov.br"

def extract_v1_swagger():
    with httpx.Client(base_url=BASE_URL, timeout=30.0, follow_redirects=True) as client:
        resp = client.get("/v1/")
        print("\n=== CONTEÚDO EXATO DE /v1/ (1359 BYTES) ===")
        print(resp.text)
        print("===========================================\n")

        # Procura qualquer URL .json ou .yaml ou configuração do SwaggerUIBundle dentro de /v1/
        matches = re.findall(r'["\']([^"\']+\.(?:json|yaml|yml))["\']', resp.text)
        for m in set(matches):
            target = m if m.startswith("http") or m.startswith("/") else f"/v1/{m}"
            print(f"Baixando especificação encontrada: {target}")
            spec_resp = client.get(target)
            print(f"Status: {spec_resp.status_code} | Size: {len(spec_resp.text)} bytes")
            if spec_resp.status_code == 200:
                spec = spec_resp.json()
                paths = list(spec.get("paths", {}).keys())
                print(f"\n=== TOTAL DE ENDPOINTS OFICIAIS NA API DO SUS: {len(paths)} ===")
                for p in sorted(paths):
                    methods = list(spec["paths"][p].keys())
                    print(f"  -> {p:<45} | Métodos: {methods}")

                with open("docs/openapi_full_spec.json", "w", encoding="utf-8") as f:
                    json.dump(spec, f, ensure_ascii=False, indent=2)
                print("\nEspecificação completa salva em: docs/openapi_full_spec.json")

if __name__ == "__main__":
    extract_v1_swagger()
