import pytest
pytest.importorskip("chromadb")

import os, json
from tests.ai.generators import gen_airplane_payloads
from tests.ai.contracts import load_repo_spec, load_live_spec, diff_required_fields
from tests.ai.mcp_client import http_get, http_post, sh
from tests.ai.triage import summarize_logs

GV = os.getenv("GV_BASE_URL", "http://localhost:5001")

@pytest.mark.order(1)
def test_live_health_and_instance():
    sc, hdr, body = http_get(GV, "/health")
    assert sc == 200
    assert "X-Instance-Id" in hdr

@pytest.mark.order(2)
def test_contract_repo_vs_live_add_airplane():
    repo = load_repo_spec()
    live = load_live_spec(GV)
    breaking = diff_required_fields(repo, live, path="/add_airplane", method="post")
    assert not breaking, f"Breaking change en campos requeridos: {breaking}"

@pytest.mark.order(3)
@pytest.mark.parametrize("payload", gen_airplane_payloads())
def test_add_airplane_generated(payload):
    sc, hdr, body = http_post(GV, "/add_airplane", payload)
    assert sc in (200,201), f"status={sc} body={body}"
    # chequeo id inmediato
    sc2, _, body2 = http_get(GV, f"/get_airplane_by_id/{payload['airplane_id']}")
    assert sc2 == 200, f"no se refleja el avión creado; posible multi-worker no sticky. hdr:{hdr}"

@pytest.mark.order(99)
def test_logs_triage_example():
    # ejemplo: si guardaste logs en tests/.logs/gestionvuelos.log
    p = "tests/.logs/gestionvuelos.log"
    if not os.path.exists(p):
        pytest.skip("sin logs")
    txt = open(p, encoding="utf-8", errors="ignore").read()
    s = summarize_logs(txt, hint="fallas intermitentes al consultar get_airplane_by_id")
    assert isinstance(s, str) and len(s) > 10
