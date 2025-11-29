import random
import pytest

from gestionvuelos_common import _get, _post, _delete, _build_valid_route_payload, service_up


@pytest.mark.parametrize(
    "case_id, scenario, expected_status, expected_msg_sub",
    [
        ("DEL_ROUTE_OK_EXISTENTE", "happy", 200, "Ruta eliminada con éxito"),
        ("DEL_ROUTE_ID_INVALIDO", "id_invalid", 400, "entero positivo"),
        ("DEL_ROUTE_ID_NO_EXISTE", "id_not_found", 404, "no encontrada"),
    ],
)
def test_delete_route_rag(
    service_up,
    case_id,
    scenario,
    expected_status,
    expected_msg_sub,
):
    """
    Casos RAG para DELETE /delete_airplane_route_by_id/<id>.
    Crea primero una ruta para el caso feliz.
    """
    if scenario == "happy":
        r_state = _get("/__state")
        assert r_state.status_code == 200
        state = r_state.json()
        airplane_ids = state.get("airplane_ids") or []
        assert airplane_ids, f"[{case_id}] No hay aviones registrados"
        aid = airplane_ids[0]

        route_id = random.randint(41_000, 41_999)
        route_payload = _build_valid_route_payload(aid, route_id=route_id)
        r_add = _post("/add_airplane_route", json=route_payload)
        assert r_add.status_code in (201, 400)

        rid = route_id

    elif scenario == "id_invalid":
        rid = 0
    elif scenario == "id_not_found":
        rid = 999_999
    else:
        pytest.fail(f"Escenario desconocido en DELETE route: {scenario}")

    r = _delete(f"/delete_airplane_route_by_id/{rid}")
    try:
        body = r.json()
    except Exception:
        body = {}

    assert (
        r.status_code == expected_status
    ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"

    msg_text = (body.get("message", "") or r.text)
    assert expected_msg_sub in msg_text
