import pytest

from gestionvuelos_common import _get, service_up


@pytest.mark.parametrize(
    "case_id, scenario, expected_status, expected_msg_sub",
    [
        ("GET_AIRPLANE_OK_EXISTENTE", "existing", 200, None),
        ("GET_AIRPLANE_ID_INVALIDO", "id_invalid", 400, "entero positivo"),
        ("GET_AIRPLANE_ID_NO_EXISTE", "id_not_found", 404, "no encontrado"),
    ],
)
def test_get_airplane_by_id_rag(
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
        assert airplane_ids, f"[{case_id}] No hay aviones registrados"
        aid = airplane_ids[0]
    elif scenario == "id_invalid":
        aid = 0
    elif scenario == "id_not_found":
        aid = 999_999
    else:
        pytest.fail(f"Escenario desconocido en GET airplane_by_id: {scenario}")

    r = _get(f"/get_airplane_by_id/{aid}")
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
