import pytest
pytest.importorskip("chromadb")

import os
from tests.ai.contracts import load_repo_spec, load_live_spec, diff_required_fields
from tests.ai.mcp_client import http_get, http_post
from gestionreservas_common import find_route_and_free_seat, make_add_reservation_body

GR = os.getenv("GR_BASE_URL", "http://localhost:5002")


@pytest.mark.order(1)
def test_gestionreservas_live_health_and_instance():
    sc, hdr, body = http_get(GR, "/health")
    assert sc == 200
    # Si GestiónReservas también expone X-Instance-Id:
    # (si no, puedes comentar esta línea)
    assert "X-Instance-Id" in hdr


@pytest.mark.order(2)
def test_gestionreservas_contract_repo_vs_live_add_reservation():
    """
    Compara campos 'required' de POST /add_reservation entre:
    - el spec del repo (openapi.json)
    - el spec vivo expuesto por GestiónReservas en /openapi.json
    """
    repo = load_repo_spec()
    live = load_live_spec(GR)
    breaking = diff_required_fields(repo, live, path="/add_reservation", method="post")
    assert not breaking, f"Breaking change en campos requeridos: {breaking}"


@pytest.mark.order(3)
def test_gestionreservas_add_reservation_basic_happy_path():
    """
    Caso simple: crear una reserva válida en GestiónReservas usando
    una combinación real (airplane_id, airplane_route_id, asiento Libre)
    obtenida desde GestiónVuelos.
    """
    pair = find_route_and_free_seat()
    if pair is None:
        pytest.skip(
            "[GR_AI_E2E] No se encontró combinación (ruta, asiento Libre) "
            "entre GestiónVuelos y GestiónReservas."
        )

    ruta, seat_libre = pair
    airplane_id = ruta["airplane_id"]
    route_id = ruta["airplane_route_id"]
    seat_number = seat_libre["seat_number"]

    payload = make_add_reservation_body(
        airplane_id=airplane_id,
        airplane_route_id=route_id,
        seat_number=seat_number,
        status="Reservado",
    )

    sc, hdr, body = http_post(GR, "/add_reservation", payload)
    assert sc in (200, 201), f"status={sc} body={body}"
