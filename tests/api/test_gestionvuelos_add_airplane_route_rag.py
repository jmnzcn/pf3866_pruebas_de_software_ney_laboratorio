import pytest

from gestionvuelos_common import (
    _get,
    _post,
    _build_valid_route_payload,
    service_up,
)


@pytest.mark.parametrize(
    "case_id, scenario, expected_status, expected_msg_sub, expected_error_field",
    [
        (
            "ROUTE_OK_01",
            "happy",
            201,
            "Ruta agregada con éxito",
            None,
        ),
        (
            "ROUTE_ERR_AIRPLANE_NO_EXISTE",
            "airplane_not_exists",
            400,
            "El avión especificado no existe",
            "airplane_id",
        ),
        (
            "ROUTE_ERR_MONEDA",
            "invalid_currency",
            400,
            "Error de validación",
            "Moneda",
        ),
        (
            "ROUTE_ERR_FECHAS",
            "arrival_before_departure",
            400,
            "La hora de llegada debe ser posterior a la de salida",
            "arrival_time",
        ),
        (
            "ROUTE_ERR_ID_DUP",
            "duplicate_id",
            400,
            "Ya existe una ruta con ID",
            "airplane_route_id",
        ),
    ],
)
def test_add_airplane_route_rag_cases(
    service_up,
    case_id,
    scenario,
    expected_status,
    expected_msg_sub,
    expected_error_field,
):
    """
    Casos sugeridos por el RAG tester para /add_airplane_route.
    """
    r_state = _get("/__state")
    assert r_state.status_code == 200, f"[{case_id}] __state no respondió 200"
    state = r_state.json()
    airplane_ids = state.get("airplane_ids") or []
    assert airplane_ids, f"[{case_id}] No hay aviones registrados en el sistema"
    any_airplane_id = airplane_ids[0]

    if scenario == "happy":
        payload = _build_valid_route_payload(any_airplane_id)
        r = _post("/add_airplane_route", json=payload)

    elif scenario == "airplane_not_exists":
        payload = _build_valid_route_payload(airplane_id=99_999)
        r = _post("/add_airplane_route", json=payload)

    elif scenario == "invalid_currency":
        payload = _build_valid_route_payload(any_airplane_id)
        payload["Moneda"] = "Yenes"
        r = _post("/add_airplane_route", json=payload)

    elif scenario == "arrival_before_departure":
        payload = _build_valid_route_payload(any_airplane_id)
        payload["departure_time"] = "Marzo 30, 2025 - 19:25:00"
        payload["arrival_time"] = "Marzo 30, 2025 - 16:46:19"
        r = _post("/add_airplane_route", json=payload)

    elif scenario == "duplicate_id":
        import random

        route_id = random.randint(31_000, 31_999)
        base_payload = _build_valid_route_payload(any_airplane_id, route_id=route_id)
        _post("/add_airplane_route", json=base_payload)
        payload = base_payload
        r = _post("/add_airplane_route", json=payload)

    else:
        pytest.fail(f"Escenario desconocido en /add_airplane_route: {scenario}")

    try:
        body = r.json()
    except Exception:
        body = {}

    if scenario == "happy":
        assert r.status_code in (201, 400), (
            f"[{case_id}] Código inesperado en caso feliz: "
            f"{r.status_code} {r.text}"
        )
        msg_text = (body.get("message", "") or r.text)

        if r.status_code == 201:
            assert "Ruta agregada con éxito" in msg_text
        else:
            assert any(
                frag in msg_text
                for frag in [
                    "Ya existe una ruta con ID",
                    "Ya existe la ruta",
                    "Ya existe una ruta con todos los mismos datos",
                ]
            ), f"[{case_id}] Mensaje de duplicado inesperado: {msg_text}"
        return

    assert r.status_code == expected_status, (
        f"[{case_id}] Código inesperado: {r.status_code} {r.text}"
    )

    msg_text = (body.get("message", "") or r.text)
    if expected_msg_sub:
        assert expected_msg_sub in msg_text, (
            f"[{case_id}] No se encontró '{expected_msg_sub}' en '{msg_text}'"
        )

    if expected_error_field:
        errors = body.get("errors", {})
        assert expected_error_field in errors, (
            f"[{case_id}] No se encontró campo de error '{expected_error_field}' en {errors}"
        )
