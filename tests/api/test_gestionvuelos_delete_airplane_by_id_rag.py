import random
import pytest

from gestionvuelos_common import _get, _post, _delete, _random_suffix, _get as _get_http, service_up


@pytest.mark.parametrize(
    "case_id, scenario, expected_status, expected_msg_sub",
    [
        ("DEL_PLANE_OK_EXISTENTE", "happy", 200, "eliminado exitosamente"),
        ("DEL_PLANE_ID_INVALIDO", "id_invalid", 400, "entero positivo"),
        ("DEL_PLANE_ID_NO_EXISTE", "id_not_found", 404, "no encontrado"),
    ],
)
def test_delete_airplane_rag(
    service_up,
    case_id,
    scenario,
    expected_status,
    expected_msg_sub,
):
    """
    Casos RAG para DELETE /delete_airplane_by_id/<id>.
    Incluye cascada de asientos en el caso feliz.
    """
    if scenario == "happy":
        new_id = random.randint(40_000, 40_999)
        payload = {
            "airplane_id": new_id,
            "model": f"E190-DEL-{_random_suffix()}",
            "manufacturer": "Embraer",
            "year": 2017,
            "capacity": 10,
        }
        r_add = _post("/add_airplane", json=payload)
        assert r_add.status_code in (201, 400)

        aid = new_id

        if r_add.status_code == 201:
            r_seats = _get_http(f"/get_airplane_seats/{aid}/seats")
            assert r_seats.status_code == 200
            seats = r_seats.json()
            assert isinstance(seats, list) and len(seats) == 10

    elif scenario == "id_invalid":
        aid = 0
    elif scenario == "id_not_found":
        aid = 999_999
    else:
        pytest.fail(f"Escenario desconocido en DELETE airplane: {scenario}")

    r = _delete(f"/delete_airplane_by_id/{aid}")
    try:
        body = r.json()
    except Exception:
        body = {}

    assert (
        r.status_code == expected_status
    ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"

    msg_text = (body.get("message", "") or r.text)
    assert expected_msg_sub in msg_text
