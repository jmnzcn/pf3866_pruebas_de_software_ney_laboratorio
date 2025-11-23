import json
from pathlib import Path
import requests

def load_repo_spec(path_candidates=("openapi.json","swagger.json")):
    for p in path_candidates:
        if Path(p).exists():
            return json.loads(Path(p).read_text(encoding="utf-8"))
    raise FileNotFoundError("No se encontró openapi.json en el repo")

def load_live_spec(base_url):
    for ep in ("/openapi.json","/swagger.json","/apispec_1.json","/docs/openapi.json"):
        try:
            r = requests.get(base_url+ep, timeout=5)
            if r.status_code==200 and "json" in r.headers.get("content-type",""):
                return r.json()
        except Exception:
            pass
    raise RuntimeError("No se pudo obtener el spec vivo")

def diff_required_fields(repo_spec, live_spec, path="/add_airplane", method="post"):
    def props(spec):
        try:
            s = spec["paths"][path][method]["requestBody"]["content"]["application/json"]["schema"]
            return set(s.get("required", []))
        except Exception:
            return set()
    return props(repo_spec) ^ props(live_spec)  # simétrica: cambios potencialmente rompientes
