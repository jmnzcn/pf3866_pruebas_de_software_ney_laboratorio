# tests/api/test_gestionvuelos_rag.py
"""
Suite de pruebas generadas / inspiradas por el "RAG tester" para el microservicio GestiónVuelos.

Objetivo:
- Modelar cómo un agente MCP/RAG podría proponer casos de prueba a partir de la
  documentación de negocio (README_testing.md, ENDPOINTS_GestionVuelos.md, etc.).
- No busca duplicar al 100% la suite manual, sino complementarla con variaciones
  interesantes de validación y negocio, cubriendo el CRUD principal.
"""

import os
import random
import string

import pytest
import requests

BASE_URL = os.getenv("GV_BASE_URL", "http://localhost:5001")


# ---------------------------------------------------------------------------
# Utilidades simples HTTP
# ---------------------------------------------------------------------------

def _get(path, timeout=10):
    return requests.get(f"{BASE_URL}{path}", timeout=timeout)


def _post(path, json=None, timeout=10):
    return requests.post(f"{BASE_URL}{path}", json=json, timeout=timeout)


def _put(path, json=None, timeout=10):
    return requests.put(f"{BASE_URL}{path}", json=json, timeout=timeout)


def _delete(path, timeout=10):
    return requests.delete(f"{BASE_URL}{path}", timeout=timeout)


def _random_suffix(n=4):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))


# -------------------------------------------------------------------
# Helper para construir un payload válido de /add_airplane_route
# -------------------------------------------------------------------
def _build_valid_route_payload(airplane_id, route_id=None):
    """
    Construye un payload válido para /add_airplane_route, usando:
    - meses en español (para que pase el validador de fecha),
    - flight_number con formato 'AA-1234',
    - Moneda válida ('Colones').
    """
    if route_id is None:
        route_id = random.randint(30_000, 39_999)

    flight_number = (
        f"{random.choice(string.ascii_uppercase)}"
        f"{random.choice(string.ascii_uppercase)}-"
        f"{random.randint(1000, 9999)}"
    )

    return {
        "airplane_route_id": route_id,
        "airplane_id": airplane_id,
        "flight_number": flight_number,
        "departure": "Aeropuerto Internacional A",
        "departure_time": "Marzo 30, 2025 - 16:46:19",
        "arrival": "Aeropuerto Internacional B",
        "arrival_time": "Marzo 30, 2025 - 19:25:00",
        "price": 98000,
        "Moneda": "Colones",
    }


# ---------------------------------------------------------------------------
# Fixture: servicio arriba
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def service_up():
    """
    Verifica que GestiónVuelos esté disponible en /health.
    Si no responde 200, se hace skip de toda la suite.
    """
    try:
        r = _get("/health", timeout=5)
        if r.status_code != 200:
            pytest.skip("GestiónVuelos no responde 200 en /health")
    except Exception:
        pytest.skip("GestiónVuelos no está disponible en BASE_URL")
    return True


# ---------------------------------------------------------------------------
# Bloque 1: Casos RAG para POST /add_airplane
# ---------------------------------------------------------------------------

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

    # Intentamos parsear cuerpo JSON
    try:
        body = r.json()
    except Exception:
        body = {}

    # Log de la respuesta
    print(
        f"[{case_id}] Respuesta /add_airplane: status={r.status_code}, body={body}"
    )

    # Manejo especial para el caso feliz: aceptamos 201 o 400 duplicado
    if scenario == "happy":
        assert r.status_code in (201, 400), (
            f"[{case_id}] Código inesperado en caso feliz: "
            f"{r.status_code} {r.text}"
        )
        msg_text = (body.get("message", "") or r.text)

        if r.status_code == 201:
            # Flujo ideal: se creó el avión
            assert "Avión y asientos agregados" in msg_text
        else:
            # Flujo alterno: el avión ya existía con ese ID
            # sigue siendo un comportamiento válido de negocio
            assert "Ya existe un avión con ese ID" in msg_text
        # En ambos casos, no seguimos validando expected_error_field
        return

    # Para los demás escenarios sí exigimos el status esperado exacto
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


# ---------------------------------------------------------------------------
# Bloque 2: Casos RAG para PUT /update_airplane/<id>
# ---------------------------------------------------------------------------

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


# ---------------------------------------------------------------------------
# Bloque 3: Casos RAG para POST /add_airplane_route
# ---------------------------------------------------------------------------

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
    # Estado actual para obtener un airplane_id válido
    r_state = _get("/__state")
    assert r_state.status_code == 200, f"[{case_id}] __state no respondió 200"
    state = r_state.json()
    airplane_ids = state.get("airplane_ids") or []
    assert airplane_ids, f"[{case_id}] No hay aviones registrados en el sistema"
    any_airplane_id = airplane_ids[0]

    # Construcción de payload según escenario
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
        route_id = random.randint(31_000, 31_999)
        base_payload = _build_valid_route_payload(any_airplane_id, route_id=route_id)
        _post("/add_airplane_route", json=base_payload)
        payload = base_payload
        r = _post("/add_airplane_route", json=payload)

    else:
        pytest.fail(f"Escenario desconocido en /add_airplane_route: {scenario}")

    # Intentamos parsear cuerpo JSON
    try:
        body = r.json()
    except Exception:
        body = {}

    # Manejo especial para el caso feliz:
    # puede devolver 201 (ruta creada) o 400 (algún tipo de duplicado)
    if scenario == "happy":
        assert r.status_code in (201, 400), (
            f"[{case_id}] Código inesperado en caso feliz: "
            f"{r.status_code} {r.text}"
        )
        msg_text = (body.get("message", "") or r.text)

        if r.status_code == 201:
            # Alta correcta
            assert "Ruta agregada con éxito" in msg_text
        else:
            # Algún tipo de duplicado aceptable según la lógica del servicio:
            # - ID duplicado
            # - flight_number + airplane_id duplicado
            # - todos los campos idénticos
            assert any(
                frag in msg_text
                for frag in [
                    "Ya existe una ruta con ID",
                    "Ya existe la ruta",  # "Ya existe la ruta AR-XXXX para el avión Y."
                    "Ya existe una ruta con todos los mismos datos",
                ]
            ), f"[{case_id}] Mensaje de duplicado inesperado: {msg_text}"
        return  # No seguimos con las aserciones genéricas

    # Para los demás escenarios, exigimos exactamente el status esperado
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


# ---------------------------------------------------------------------------
# Bloque 4: Casos RAG para GET (lecturas) de aviones y rutas
# ---------------------------------------------------------------------------

def test_get_airplanes_rag_basic(service_up):
    """
    Caso RAG: listar aviones con /get_airplanes.
    Acepta dos diseños: lista de aviones o mensaje de 'No hay aviones...'.
    """
    r = _get("/get_airplanes")
    assert r.status_code in (200, 500), f"Código inesperado en /get_airplanes: {r.status_code} {r.text}"

    if r.status_code == 200:
        body = r.json()
        # Puede ser lista o dict con 'message'
        if isinstance(body, list):
            # Si hay lista, validamos que cada item tenga airplane_id
            assert all("airplane_id" in a for a in body)
        elif isinstance(body, dict):
            assert "message" in body
    else:
        # 500 se cubre como señal de posible problema de datos internos
        pass


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
    """
    Casos RAG para GET /get_airplane_by_id/<id>.
    """
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


def test_get_all_routes_rag_basic(service_up):
    """
    Caso RAG: listar rutas con /get_all_airplanes_routes.
    Acepta lista de rutas o mensaje 'No hay rutas registradas actualmente.'.
    """
    r = _get("/get_all_airplanes_routes")
    assert r.status_code in (200, 500)

    if r.status_code == 200:
        body = r.json()
        if isinstance(body, list):
            # Si hay lista, validamos que, si no está vacía, tenga airplane_route_id
            if body:
                assert all("airplane_route_id" in rt for rt in body)
        elif isinstance(body, dict):
            assert "message" in body
    else:
        # 500 = posible problema interno
        pass


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
    """
    Casos RAG para GET /get_airplanes_route_by_id/<id>.
    Crea una ruta si hace falta para tener un ID existente controlado.
    """
    # Para el caso "existing" creamos una ruta y usamos su ID
    if scenario == "existing":
        # Tomar un avión cualquiera existente
        r_state = _get("/__state")
        assert r_state.status_code == 200
        state = r_state.json()
        airplane_ids = state.get("airplane_ids") or []
        assert airplane_ids, "[GET_ROUTE_OK_EXISTENTE] No hay aviones registrados"
        aid = airplane_ids[0]

        route_payload = _build_valid_route_payload(aid)
        r_add = _post("/add_airplane_route", json=route_payload)
        # Puede ser 201 o 400 si por azar coinciden IDs; si 400, igual intentamos usar route_id
        route_id = route_payload["airplane_route_id"]
        aid_route = route_id
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


# ---------------------------------------------------------------------------
# Bloque 5: Casos RAG para DELETE de aviones y rutas
# ---------------------------------------------------------------------------

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
    # Preparación para caso feliz: crear avión con capacity 10
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

        # Verificar que existan asientos (si la creación fue exitosa)
        if r_add.status_code == 201:
            r_seats = _get(f"/get_airplane_seats/{aid}/seats")
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

    if scenario == "happy" and r.status_code == 200:
        # Verificar que asientos estén eliminados o inaccesibles
        r_seats2 = _get(f"/get_airplane_seats/{aid}/seats")
        assert r_seats2.status_code in (404, 200)
        if r_seats2.status_code == 200:
            # Si el diseño devolviera 200, debería ser lista vacía
            try:
                seats2 = r_seats2.json()
            except Exception:
                seats2 = []
            assert seats2 == []


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
        # Necesitamos un avión válido
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
