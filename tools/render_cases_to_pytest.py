# tools/render_cases_to_pytest.py
import json
import argparse
from pathlib import Path
import textwrap

TEMPLATE_HEADER = '''"""
Tests AI-sugeridos para {endpoint}
Archivo generado automáticamente a partir de {source_json}
"""

import os
import random
import json
import pytest
import requests

BASE_URL = os.getenv("GV_BASE_URL", "http://localhost:5001")

@pytest.mark.ai_generated
class TestAiGenerated{class_suffix}:

    def _resolve_dynamic_values(self, payload):
        if isinstance(payload, dict):
            return {k: self._resolve_dynamic_values(v) for k, v in payload.items()}
        if isinstance(payload, list):
            return [self._resolve_dynamic_values(v) for v in payload]
        if isinstance(payload, str):
            if payload == "RANDOM_INT_800_899":
                return random.randint(800, 899)
            if payload == "RANDOM_INT_900_999":
                return random.randint(900, 999)
        return payload

'''

TEMPLATE_CASE = '''
    @pytest.mark.endpoint("{method} {path}")
    @pytest.mark.case_id("{case_id}")
    def test_{func_name}(self):
        """
        {name}
        Reglas de negocio: {business_rules}
        """
        method = "{method}"
        path = "{path}"
        input_payload = {input_payload}
        expected = {expected}

        input_payload = self._resolve_dynamic_values(input_payload)

        url = f"{{BASE_URL}}{{path}}"
        if method in ("POST", "PUT"):
            r = requests.request(method, url, json=input_payload, timeout=10)
        else:
            r = requests.request(method, url, timeout=10)

        assert r.status_code == expected["status_code"], f"Status inesperado: {{r.status_code}} - {{r.text}}"

        try:
            body = r.json()
        except Exception:
            body = None

        if body is not None and "json_contains" in expected and expected["json_contains"]:
            for k, v in expected["json_contains"].items():
                assert body.get(k) == v, f"Se esperaba body['{{k}}'] == {{v}}, obtuvo {{body.get(k)}}"

        if body is not None and "json_contains_text" in expected and expected["json_contains_text"]:
            serialized = json.dumps(body, ensure_ascii=False)
            for t in expected["json_contains_text"]:
                assert t in serialized, f"Se esperaba encontrar '{{t}}' en la respuesta"
'''

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases-json", required=True,
                        help="Ruta al archivo JSON con casos generados")
    parser.add_argument("--output-py", required=True,
                        help="Ruta de salida del archivo .py de tests")
    args = parser.parse_args()

    data = json.loads(Path(args.cases_json).read_text(encoding="utf-8"))
    endpoint = data.get("endpoint", "UNKNOWN")
    cases = data.get("cases", [])

    # class_suffix para que el nombre de la clase sea amigable
    class_suffix = endpoint.upper().replace(" ", "_").replace("/", "_")

    header = TEMPLATE_HEADER.format(
        endpoint=endpoint,
        source_json=args.cases_json,
        class_suffix=class_suffix,
    )

    case_blocks = []
    for case in cases:
        func_name = case["id"].lower().replace("-", "_")
        case_block = TEMPLATE_CASE.format(
            method=case["method"],
            path=case["path"],
            case_id=case["id"],
            func_name=func_name,
            name=case["name"].replace('"', '\\"'),
            business_rules="; ".join(case.get("business_rules", [])),
            input_payload=json.dumps(case.get("input", {}), ensure_ascii=False, indent=2),
            expected=json.dumps(case.get("expected", {}), ensure_ascii=False, indent=2),
        )
        case_blocks.append(textwrap.dedent(case_block))

    out_code = header + "\n".join(case_blocks)

    out_path = Path(args.output_py)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out_code, encoding="utf-8")
    print(f"Tests generados en {out_path}")

if __name__ == "__main__":
    main()
