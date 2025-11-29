import pytest

from gestionvuelos_common import _get, _put, service_up


@pytest.mark.parametrize(
    "case_id, scenario, expected_status, expected_msg_sub, expected_error_field",
    [
        (
            "UPD_OK_CAMBIA_MODEL_Y_CAPACITY",
            "happy",
            200,
            "actualizado con éxito",
            None,
        ),
        (
            "UPD_FALTAN_CAMPOS",
            "missing_fields",
            400,
            "Faltan campos obligatorios",
            None,
        ),
        (
            "UPD_CAMPOS_EXTRAS",
            "extra_fields",
            400,
            "campos no válidos",
            None,
        ),
        (
            "UPD_YEAR_INVALIDO",
            "year_zero",
            400,
            "Errores de validación",
            "year",
        ),
    ],
)
def test_update_airplane_rag_cases(
    service_up,
    case_id,
    scenario,
    expected_status,
    expected_msg_sub,
    expected_error_field,
):
    """
    Casos sugeridos por el RAG tester para /update_airplane/<id>.
    """
    r_state = _get("/__state")
    assert r_state.status_code == 200, f"[{case_id}] __state no respondió 200"
    state = r_state.json()
    airplane_ids = state.get("airplane_ids") or []
    assert airplane_ids, f"[{case_id}] No hay aviones registrados en el sistema"
    aid = airplane_ids[0]

    r_get = _get(f"/get_airplane_by_id/{aid}")
    assert r_get.status_code == 200, f"[{case_id}] No se pudo obtener avión {aid}"
    avion = r_get.json()

    if scenario == "happy":
        payload = {
            "model": f"{avion['model']}-RAG",
            "manufacturer": avion["manufacturer"],
            "year": avion["year"],
            "capacity": avion["capacity"] + 1,
        }
    elif scenario == "missing_fields":
        payload = {
            "model": "X-SOLO-MODEL",
        }
    elif scenario == "extra_fields":
        payload = {
            "model": "X-EXTRA",
            "manufacturer": "Y",
            "year": 2020,
            "capacity": 10,
            "color": "rojo",
        }
    elif scenario == "year_zero":
        payload = {
            "model": "X-YEAR0",
            "manufacturer": "Y",
            "year": 0,
            "capacity": 10,
        }
    else:
        pytest.fail(f"Escenario desconocido en /update_airplane: {scenario}")

    r = _put(f"/update_airplane/{aid}", json=payload)
    try:
        body = r.json()
    except Exception:
        body = {}

    assert (
        r.status_code == expected_status
    ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"

    msg_text = (body.get("message", "") or r.text)
    assert (
        expected_msg_sub in msg_text
    ), f"[{case_id}] Substring de mensaje esperado no encontrado"

    if expected_error_field:
        errors = body.get("errors", {})
        assert (
            expected_error_field in errors
        ), f"[{case_id}] Se esperaba error en campo '{expected_error_field}'"
