import random
import pytest

from gestionvuelos_common import _post, _random_suffix, service_up


@pytest.mark.parametrize(
    "case_id, scenario, expected_status, expected_msg, expected_error_field",
    [
        # Caso feliz con ID nuevo generado dinámicamente
        (
            "ADD_OK_01",
            "happy",
            201,
            "Avión y asientos agregados",
            None,
        ),
        # Duplicado de ID: se crea primero y luego se intenta recrear
        (
            "ADD_ERR_ID_DUP",
            "id_dup",
            400,
            "Ya existe un avión con ese ID",
            None,
        ),
        # Faltan campos obligatorios
        (
            "ADD_ERR_FALTANTES",
            "missing_fields",
            400,
            "Faltan campos obligatorios",
            None,
        ),
        # Campos extra no permitidos
        (
            "ADD_ERR_EXTRAS",
            "extra_fields",
            400,
            "Campos no válidos",
            None,
        ),
        # Año inválido (<= 0): validación de negocio explícita
        (
            "ADD_ERR_YEAR",
            "year_zero",
            400,
            "El campo 'year' debe ser un entero positivo",
            None,
        ),
        # Capacidad inválida (<= 0): error de Marshmallow en campo capacity
        (
            "ADD_ERR_CAPACITY",
            "capacity_zero",
            400,
            "Errores de validación",
            "capacity",
        ),
        # Body vacío
        (
            "ADD_ERR_BODY_VACIO",
            "empty_body",
            400,
            "No se recibió ningún cuerpo JSON",
            None,
        ),
    ],
)
def test_add_airplane_rag_cases(
    service_up,
    case_id,
    scenario,
    expected_status,
    expected_msg,
    expected_error_field,
):
    """
    Casos generados/sugeridos por el agente RAG tester para /add_airplane.
    """
    payload = None

    if scenario == "happy":
        new_id = random.randint(10_000, 19_999)
        payload = {
            "airplane_id": new_id,
            "model": f"B737-RAG-{_random_suffix()}",
            "manufacturer": "Boeing",
            "year": 2020,
            "capacity": 15,
        }
        print(f"[{case_id}] Escenario '{scenario}' -> payload: {payload}")
        r = _post("/add_airplane", json=payload)

    elif scenario == "id_dup":
        base_id = random.randint(20_000, 20_999)
        base_payload = {
            "airplane_id": base_id,
            "model": f"A320-RAG-{_random_suffix()}",
            "manufacturer": "Airbus",
            "year": 2018,
            "capacity": 12,
        }
        print(f"[{case_id}] Creando avión base para duplicado: {base_payload}")
        _post("/add_airplane", json=base_payload)

        payload = base_payload
        print(f"[{case_id}] Escenario '{scenario}' -> payload duplicado: {payload}")
        r = _post("/add_airplane", json=payload)

    elif scenario == "missing_fields":
        payload = {
            "airplane_id": random.randint(21_000, 21_999),
            "model": "X-SIN-CAMPOS",
        }
        print(f"[{case_id}] Escenario '{scenario}' -> payload: {payload}")
        r = _post("/add_airplane", json=payload)

    elif scenario == "extra_fields":
        payload = {
            "airplane_id": random.randint(22_000, 22_999),
            "model": "A320-EXTRA",
            "manufacturer": "Airbus",
            "year": 2018,
            "capacity": 12,
            "color": "rojo",
        }
        print(f"[{case_id}] Escenario '{scenario}' -> payload: {payload}")
        r = _post("/add_airplane", json=payload)

    elif scenario == "year_zero":
        payload = {
            "airplane_id": random.randint(23_000, 23_999),
            "model": "MD80-NEG",
            "manufacturer": "McDonnell",
            "year": 0,
            "capacity": 10,
        }
        print(f"[{case_id}] Escenario '{scenario}' -> payload: {payload}")
        r = _post("/add_airplane", json=payload)

    elif scenario == "capacity_zero":
        payload = {
            "airplane_id": random.randint(24_000, 24_999),
            "model": "E190-CAP0",
            "manufacturer": "Embraer",
            "year": 2017,
            "capacity": 0,
        }
        print(f"[{case_id}] Escenario '{scenario}' -> payload: {payload}")
        r = _post("/add_airplane", json=payload)

    elif scenario == "empty_body":
        print(f"[{case_id}] Escenario '{scenario}' -> payload vacío {{}}")
        r = _post("/add_airplane", json={})

    else:
        pytest.fail(f"Escenario desconocido en /add_airplane: {scenario}")

    try:
        body = r.json()
    except Exception:
        body = {}

    print(f"[{case_id}] Respuesta /add_airplane: status={r.status_code}, body={body}")

    # Caso feliz acepta 201 o 400 duplicado
    if scenario == "happy":
        assert r.status_code in (201, 400), (
            f"[{case_id}] Código inesperado en caso feliz: "
            f"{r.status_code} {r.text}"
        )
        msg_text = (body.get("message", "") or r.text)

        if r.status_code == 201:
            assert "Avión y asientos agregados" in msg_text
        else:
            assert "Ya existe un avión con ese ID" in msg_text
        return

    assert (
        r.status_code == expected_status
    ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"

    msg_text = (body.get("message", "") or r.text)
    assert expected_msg in msg_text, f"[{case_id}] Mensaje esperado no encontrado"

    if expected_error_field:
        errors = body.get("errors", {})
        assert (
            expected_error_field in errors
        ), f"[{case_id}] Se esperaba error en campo '{expected_error_field}'"
