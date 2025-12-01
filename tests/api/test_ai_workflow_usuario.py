import pytest
pytest.importorskip("chromadb")

import os
from tests.ai.contracts import load_repo_spec, load_live_spec, diff_required_fields
from tests.ai.mcp_client import http_get, http_post

# Base URL del microservicio Usuario
USR = os.getenv("USR_BASE_URL", "http://localhost:5003")


def _as_json_list(body):
    # body puede venir como list o como string JSON
    if isinstance(body, str):
        try:
            data = json.loads(body)
        except Exception:
            return []
        return data if isinstance(data, list) else []
    if isinstance(body, list):
        return body
    return []


@pytest.mark.order(1)
def test_usuario_live_health_and_instance():
    """
    Smoke test: el microservicio Usuario responde en /health
    y opcionalmente expone X-Instance-Id.
    """
    sc, hdr, body = http_get(USR, "/health")
    assert sc == 200, f"status={sc} body={body}"
    # Si Usuario NO expone este header, puedes comentar esta línea:
    # assert "X-Instance-Id" in hdr

def _find_route_and_free_seat_via_usuario():
    sc_routes, _, routes_body = http_get(USR, "/get_all_airplanes_routes")
    assert sc_routes == 200, f"status={sc_routes} body={routes_body}"

    routes = _as_json_list(routes_body)
    for ruta in routes:
        if not isinstance(ruta, dict):
            continue
        airplane_id = ruta.get("airplane_id")
        route_id = ruta.get("airplane_route_id")
        if not isinstance(airplane_id, int) or not isinstance(route_id, int):
            continue

        sc_seats, _, seats_body = http_get(
            USR,
            f"/get_seats_by_airplane_id/{airplane_id}/seats",
        )
        if sc_seats != 200:
            continue

        seats = _as_json_list(seats_body)
        for seat in seats:
            if not isinstance(seat, dict):
                continue
            if seat.get("status") == "Libre":
                return ruta, seat

    return None


@pytest.mark.order(2)
def test_usuario_contract_repo_vs_live_add_reservation():
    """
    Compara campos 'required' de POST /usuario/add_reservation entre:
    - el spec del repo (openapi.json en la raíz)
    - el spec vivo expuesto por Usuario (p.ej. /openapi.json o /apispec_1.json)
    """
    repo = load_repo_spec()
    live = load_live_spec(USR)

    breaking = diff_required_fields(
        repo,
        live,
        path="/usuario/add_reservation",
        method="post",
    )

    assert not breaking, (
        "Breaking change en campos requeridos de /usuario/add_reservation: "
        f"{breaking}"
    )


@pytest.mark.order(3)
def test_usuario_add_reservation_basic_happy_path():
    pair = _find_route_and_free_seat_via_usuario()
    if pair is None:
        pytest.skip(
            "[USR_AI_E2E] No se encontró combinación (ruta, asiento Libre) vía Usuario."
        )

    ruta, seat_libre = pair
    airplane_id = ruta["airplane_id"]
    airplane_route_id = ruta["airplane_route_id"]
    seat_number = seat_libre["seat_number"]

    payload = {
        "passport_number": "USRWF12345",
        "full_name": "Reserva Usuario AI Workflow",
        "email": "ai.usuario.workflow@example.com",
        "phone_number": "+50670000002",
        "emergency_contact_name": "Contacto Usuario AI",
        "emergency_contact_phone": "+50671111113",
        "airplane_id": airplane_id,
        "airplane_route_id": airplane_route_id,
        "seat_number": seat_number,
        "status": "Reservado",
    }

    sc, hdr, body = http_post(USR, "/usuario/add_reservation", payload)
    assert sc in (200, 201), f"status={sc} body={body}"


