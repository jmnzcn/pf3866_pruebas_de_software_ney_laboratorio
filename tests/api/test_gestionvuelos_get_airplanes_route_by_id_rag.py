import pytest

from gestionvuelos_common import _get, _post, _build_valid_route_payload, service_up


@pytest.mark.parametrize(
    "case_id, scenario, expected_status, expected_msg_sub",
    [
        ("GET_ROUTE_OK_EXISTENTE", "existing", 200, None),
        ("GET_ROUTE_ID_INVALIDO", "id_invalid", 400, "entero positivo"),
        ("GET_ROUTE_ID_NO_EXISTE", "id_not_found", 404, "no encontrada"),
    ],
)
def test_get_route_by_id_rag(
    service_up,
    case_id,
    scenario,
    expected_status,
    expected_msg_sub,
):
    if scenario == "existing":
        r_state = _get("/__state")
        assert r_state.status_code == 200
        state = r_state.json()
        airplane_ids = state.get("airplane_ids") or []
        assert airplane_ids, "[GET_ROUTE_OK_EXISTENTE] No hay aviones registrados"
        aid = airplane_ids[0]

        route_payload = _build_valid_route_payload(aid)
        _post("/add_airplane_route", json=route_payload)
        aid_route = route_payload["airplane_route_id"]
    elif scenario == "id_invalid":
        aid_route = 0
    elif scenario == "id_not_found":
        aid_route = 999_999
    else:
        pytest.fail(f"Escenario desconocido en GET route_by_id: {scenario}")

    r = _get(f"/get_airplanes_route_by_id/{aid_route}")
    try:
        body = r.json()
    except Exception:
        body = {}

    assert (
        r.status_code == expected_status
    ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"

    if expected_msg_sub:
        msg_text = (body.get("message", "") or r.text)
        assert expected_msg_sub in msg_text
