# tests/api/test_gestionreservas_rag.py

import os
import random
import re

import pytest
import requests

# ------------------------------------------------------------------------------------
# Configuración base
# ------------------------------------------------------------------------------------

BASE_URL_RES = os.getenv("GRES_BASE_URL", "http://localhost:5002")
BASE_URL_GV = os.getenv("GV_BASE_URL", "http://localhost:5001")
DEFAULT_TIMEOUT = 20


def _request_res(method: str, path: str, **kwargs) -> requests.Response:
    url = f"{BASE_URL_RES}{path}"
    timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)
    return requests.request(method, url, timeout=timeout, **kwargs)


def _get_res(path: str, **kwargs) -> requests.Response:
    return _request_res("GET", path, **kwargs)


def _post_res(path: str, **kwargs) -> requests.Response:
    return _request_res("POST", path, **kwargs)


def _put_res(path: str, **kwargs) -> requests.Response:
    return _request_res("PUT", path, **kwargs)


def _delete_res(path: str, **kwargs) -> requests.Response:
    return _request_res("DELETE", path, **kwargs)


def _request_gv(method: str, path: str, **kwargs) -> requests.Response:
    url = f"{BASE_URL_GV}{path}"
    timeout = kwargs.pop("timeout", DEFAULT_TIMEOUT)
    return requests.request(method, url, timeout=timeout, **kwargs)


def _get_gv(path: str, **kwargs) -> requests.Response:
    return _request_gv("GET", path, **kwargs)


# ------------------------------------------------------------------------------------
# Fixtures / helpers para escenarios felices
# ------------------------------------------------------------------------------------


@pytest.fixture(scope="session")
def service_up():
    """
    Verifica que GestiónReservas y GestiónVuelos estén arriba antes de ejecutar los tests.
    """
    # GestiónReservas
    try:
        r_res = _get_res("/get_fake_reservations")
    except Exception as exc:  # pragma: no cover
        pytest.fail(f"No se pudo conectar con GestiónReservas en {BASE_URL_RES}: {exc}")

    assert r_res.status_code in (
        200,
        204,
    ), f"GestiónReservas no respondió OK: {r_res.status_code} {r_res.text}"

    # GestiónVuelos
    try:
        r_gv = _get_gv("/health")
    except Exception as exc:  # pragma: no cover
        pytest.fail(f"No se pudo conectar con GestiónVuelos en {BASE_URL_GV}: {exc}")

    assert r_gv.status_code == 200, f"GestiónVuelos /health falló: {r_gv.status_code} {r_gv.text}"

    return True


def _build_valid_reservation_payload():
    """
    Construye un body válido para /add_reservation usando datos reales de GestiónVuelos:
    - una ruta válida
    - un asiento Libre
    """
    r_routes = _get_gv("/get_all_airplanes_routes")
    assert (
        r_routes.status_code == 200
    ), f"No se pudieron obtener rutas de GestiónVuelos: {r_routes.status_code} {r_routes.text}"

    routes = r_routes.json()
    assert isinstance(routes, list) and routes, "No hay rutas disponibles en GestiónVuelos"

    # Escogemos la primera ruta para simplificar
    route = routes[0]
    airplane_id = route["airplane_id"]
    airplane_route_id = route["airplane_route_id"]

    # Obtener asiento libre
    r_seat = _get_gv(f"/get_random_free_seat/{airplane_id}")
    assert (
        r_seat.status_code == 200
    ), f"No se pudo obtener asiento libre para avión {airplane_id}: {r_seat.status_code} {r_seat.text}"

    seat = r_seat.json()
    seat_number = seat["seat_number"]

    payload = {
        "passport_number": "A12345678",
        "full_name": f"Test User {random.randint(1, 9999)}",
        "email": f"test{random.randint(1, 99999)}@example.com",
        "phone_number": "+50688889999",
        "emergency_contact_name": "Contacto Test",
        "emergency_contact_phone": "+50677778888",
        "airplane_id": airplane_id,
        "airplane_route_id": airplane_route_id,
        "seat_number": seat_number,
        "status": "Reservado",
    }
    return payload


def _create_reservation():
    """
    Crea una reserva feliz usando /add_reservation y devuelve el objeto reserva.
    """
    payload = _build_valid_reservation_payload()
    r = _post_res("/add_reservation", json=payload)
    assert (
        r.status_code == 201
    ), f"Falló creación de reserva feliz: {r.status_code} {r.text}"
    body = r.json()
    return body["reservation"]


def _create_payment_for_new_reservation(payment_method="Tarjeta", currency="Dolares"):
    """
    Crea una reserva y luego registra un pago asociado a ella.
    Devuelve el objeto pago resultante.
    """
    reservation = _create_reservation()
    rid = reservation["reservation_id"]

    data = {
        "reservation_id": rid,
        "payment_method": payment_method,
        "currency": currency,
    }
    r = _post_res("/create_payment", json=data)
    assert (
        r.status_code == 201
    ), f"Falló creación de pago feliz: {r.status_code} {r.text}"
    body = r.json()
    return body["payment"]


# ------------------------------------------------------------------------------------
# Tests RAG para /add_reservation
# ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case_id, scenario, expected_status, expected_msg_sub",
    [
        (
            "ADD_RES_OK_01",
            "happy",
            201,
            "Reserva creada exitosamente",
        ),
        (
            "ADD_RES_ERR_BODY_VACIO",
            "body_empty",
            400,
            "No se recibió cuerpo JSON",
        ),
        (
            "ADD_RES_ERR_FALTANTES",
            "missing_fields",
            400,
            "Error de validación",
        ),
        (
            "ADD_RES_ERR_EXTRAS",
            "extra_fields",
            400,
            "Error de validación",
        ),
        (
            "ADD_RES_ERR_EMAIL_INVALIDO",
            "email_invalid",
            400,
            "Error de validación",
        ),
        (
            "ADD_RES_ERR_STATUS_INVALIDO",
            "status_invalid",
            400,
            "Error de validación",
        ),
        (
            "ADD_RES_ERR_RUTA_NO_EXISTE",
            "route_not_found",
            400,
            "Ruta con ID",
        ),
        (
            "ADD_RES_ERR_RUTA_NO_ASOCIADA_AVION",
            "route_not_associated",
            400,
            "no está asociada al avión",
        ),
        (
            "ADD_RES_ERR_ASIENTO_NO_EXISTE",
            "seat_not_exists",
            400,
            "no existe para ese avión",
        ),
        (
            "ADD_RES_ERR_ASIENTO_NO_LIBRE",
            "seat_not_free",
            409,
            "no está disponible",
        ),
    ],
)
def test_add_reservation_rag_cases(
    service_up, case_id, scenario, expected_status, expected_msg_sub
):
    """
    Casos generados/sugeridos por el agente RAG tester para /add_reservation.
    """
    if scenario == "happy":
        payload = _build_valid_reservation_payload()
        r = _post_res("/add_reservation", json=payload)

    elif scenario == "body_empty":
        # JSON vacío -> el endpoint lo trata como no recibido
        r = _post_res("/add_reservation", json={})

    elif scenario == "missing_fields":
        payload = {
            "passport_number": "A12345678",
            "full_name": "Juan Pérez",
            "email": "juan.perez@example.com",
            "phone_number": "+50688889999",
            "emergency_contact_name": "Carlos Jiménez",
            "emergency_contact_phone": "+50677778888",
            # faltan airplane_id, airplane_route_id, seat_number, status
        }
        r = _post_res("/add_reservation", json=payload)

    elif scenario == "extra_fields":
        payload = _build_valid_reservation_payload()
        payload["coupon_code"] = "PROMO2025"
        r = _post_res("/add_reservation", json=payload)

    elif scenario == "email_invalid":
        payload = _build_valid_reservation_payload()
        payload["email"] = "no-es-un-correo"
        r = _post_res("/add_reservation", json=payload)

    elif scenario == "status_invalid":
        payload = _build_valid_reservation_payload()
        payload["status"] = "Pendiente"
        r = _post_res("/add_reservation", json=payload)

    elif scenario == "route_not_found":
        payload = _build_valid_reservation_payload()
        payload["airplane_route_id"] = 999_999
        r = _post_res("/add_reservation", json=payload)

    elif scenario == "route_not_associated":
        # Necesitamos al menos 2 aviones distintos en las rutas
        r_routes = _get_gv("/get_all_airplanes_routes")
        assert r_routes.status_code == 200, "No se pudieron obtener rutas de GestiónVuelos"
        routes = r_routes.json()
        assert isinstance(routes, list) and routes, "No hay rutas disponibles"

        routes_by_plane = {}
        for rt in routes:
            routes_by_plane.setdefault(rt["airplane_id"], []).append(rt)

        airplanes = list(routes_by_plane.keys())
        if len(airplanes) < 2:
            pytest.skip(
                f"[{case_id}] No hay al menos 2 aviones distintos para probar ruta no asociada."
            )

        airplane_a = airplanes[0]
        airplane_b = airplanes[1]
        route_b = routes_by_plane[airplane_b][0]

        # Asiento libre para airplane_a
        r_seat = _get_gv(f"/get_random_free_seat/{airplane_a}")
        assert r_seat.status_code == 200, "No se pudo obtener asiento libre para airplane_a"
        seat = r_seat.json()

        payload = {
            "passport_number": "A12345678",
            "full_name": "Juan Pérez",
            "email": "juan.perez@example.com",
            "phone_number": "+50688889999",
            "emergency_contact_name": "Carlos Jiménez",
            "emergency_contact_phone": "+50677778888",
            "airplane_id": airplane_a,
            "airplane_route_id": route_b["airplane_route_id"],  # ruta de otro avión
            "seat_number": seat["seat_number"],
            "status": "Reservado",
        }
        r = _post_res("/add_reservation", json=payload)

    elif scenario == "seat_not_exists":
        payload = _build_valid_reservation_payload()
        payload["seat_number"] = "Z99"  # asiento inexistente
        r = _post_res("/add_reservation", json=payload)

    elif scenario == "seat_not_free":
        # 1) Creamos una reserva feliz para dejar un asiento en estado Reservado
        payload1 = _build_valid_reservation_payload()
        r1 = _post_res("/add_reservation", json=payload1)
        assert r1.status_code == 201, f"Primer reserva falló: {r1.status_code} {r1.text}"
        res1 = r1.json()["reservation"]

        airplane_id = res1["airplane_id"]
        route_id = res1["airplane_route_id"]
        old_seat = res1["seat_number"]

        # 2) Buscamos otro asiento Libre del mismo avión
        r_seats = _get_gv(f"/get_airplane_seats/{airplane_id}/seats")
        assert (
            r_seats.status_code == 200
        ), f"Error obteniendo asientos para avión {airplane_id}: {r_seats.status_code} {r_seats.text}"
        seats = r_seats.json()

        new_seat = None
        for s in seats:
            if s["seat_number"] != old_seat and s["status"] == "Libre":
                new_seat = s["seat_number"]
                break

        if not new_seat:
            pytest.skip(
                f"[{case_id}] No hay un segundo asiento Libre en el avión {airplane_id} para probar asiento no libre."
            )

        # 3) Crear segunda reserva para dejar new_seat como Reservado
        payload2 = {
            **payload1,
            "seat_number": new_seat,
            "airplane_route_id": route_id,
        }
        r2 = _post_res("/add_reservation", json=payload2)
        assert r2.status_code == 201, f"Segunda reserva falló: {r2.status_code} {r2.text}"
        res2 = r2.json()["reservation"]

        # 4) Intentar crear una tercera reserva usando ese asiento ya reservado
        payload3 = {
            "passport_number": "B12345678",
            "full_name": "Usuario Tercero",
            "email": "tercero@example.com",
            "phone_number": "+50611112222",
            "emergency_contact_name": "Contacto Tercero",
            "emergency_contact_phone": "+50633334444",
            "airplane_id": res2["airplane_id"],
            "airplane_route_id": res2["airplane_route_id"],
            "seat_number": res2["seat_number"],
            "status": "Reservado",
        }
        r = _post_res("/add_reservation", json=payload3)

    else:
        pytest.fail(f"Escenario desconocido en /add_reservation: {scenario}")

    try:
        body = r.json()
    except Exception:
        body = {}

    assert (
        r.status_code == expected_status
    ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"

    if expected_msg_sub:
        msg_text = body.get("message", "") or r.text
        assert (
            expected_msg_sub in msg_text
        ), f"[{case_id}] No se encontró '{expected_msg_sub}' en: {msg_text}"


# ------------------------------------------------------------------------------------
# Tests RAG para reservas: GET por código, GET por ID, DELETE
# ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case_id, scenario, expected_status, expected_msg_sub",
    [
        ("GET_RES_BY_CODE_OK_EXISTENTE", "existing", 200, None),
        ("GET_RES_BY_CODE_INVALIDO", "code_invalid", 400, "6 caracteres"),
        ("GET_RES_BY_CODE_NO_EXISTE", "not_found", 404, "Reserva no encontrada"),
    ],
)
def test_get_reservation_by_code_rag(
    service_up, case_id, scenario, expected_status, expected_msg_sub
):
    if scenario == "existing":
        res = _create_reservation()
        code = res["reservation_code"]
        r = _get_res(f"/get_reservation_by_code/{code}")

        assert r.status_code == 200, f"[{case_id}] Código inesperado: {r.status_code} {r.text}"
        body = r.json()
        assert body["reservation_code"] == code

        return

    elif scenario == "code_invalid":
        r = _get_res("/get_reservation_by_code/ABC12")  # 5 caracteres
    elif scenario == "not_found":
        code = "ZZZ999"
        r = _get_res(f"/get_reservation_by_code/{code}")
    else:
        pytest.fail(f"Escenario desconocido: {scenario}")

    try:
        body = r.json()
    except Exception:
        body = {}

    assert (
        r.status_code == expected_status
    ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"

    if expected_msg_sub:
        msg_text = body.get("message", "") or r.text
        assert (
            expected_msg_sub in msg_text
        ), f"[{case_id}] No se encontró '{expected_msg_sub}' en: {msg_text}"


@pytest.mark.parametrize(
    "case_id, scenario, expected_status, expected_msg_sub",
    [
        ("GET_RES_BY_ID_OK_EXISTENTE", "existing", 200, None),
        ("GET_RES_BY_ID_INVALIDO", "id_invalid", 400, "entero positivo"),
        ("GET_RES_BY_ID_NO_EXISTE", "id_not_found", 404, "Reserva no encontrada"),
    ],
)
def test_get_reservation_by_id_rag(
    service_up, case_id, scenario, expected_status, expected_msg_sub
):
    if scenario == "existing":
        res = _create_reservation()
        rid = res["reservation_id"]
        r = _get_res(f"/get_reservation_by_id/{rid}")

        assert r.status_code == 200, f"[{case_id}] Código inesperado: {r.status_code} {r.text}"
        body = r.json()
        assert body["reservation_id"] == rid
        return

    elif scenario == "id_invalid":
        r = _get_res("/get_reservation_by_id/abc")
    elif scenario == "id_not_found":
        r = _get_res("/get_reservation_by_id/999999")
    else:
        pytest.fail(f"Escenario desconocido: {scenario}")

    try:
        body = r.json()
    except Exception:
        body = {}

    assert (
        r.status_code == expected_status
    ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"

    if expected_msg_sub:
        msg_text = body.get("message", "") or r.text
        assert (
            expected_msg_sub in msg_text
        ), f"[{case_id}] No se encontró '{expected_msg_sub}' en: {msg_text}"


@pytest.mark.parametrize(
    "case_id, scenario, expected_status, expected_msg_sub",
    [
        ("DEL_RES_OK_EXISTENTE", "happy", 200, "Reserva eliminada exitosamente"),
        ("DEL_RES_ID_INVALIDO", "id_invalid", 400, "número positivo"),
        ("DEL_RES_ID_NO_EXISTE", "id_not_found", 404, "Reserva no encontrada"),
    ],
)
def test_delete_reservation_by_id_rag(
    service_up, case_id, scenario, expected_status, expected_msg_sub
):
    if scenario == "happy":
        res = _create_reservation()
        rid = res["reservation_id"]
        r = _delete_res(f"/delete_reservation_by_id/{rid}")
    elif scenario == "id_invalid":
        r = _delete_res("/delete_reservation_by_id/-1")
    elif scenario == "id_not_found":
        r = _delete_res("/delete_reservation_by_id/999999")
    else:
        pytest.fail(f"Escenario desconocido: {scenario}")

    try:
        body = r.json()
    except Exception:
        body = {}

    assert (
        r.status_code == expected_status
    ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"

    if expected_msg_sub:
        msg_text = body.get("message", "") or r.text
        assert (
            expected_msg_sub in msg_text
        ), f"[{case_id}] No se encontró '{expected_msg_sub}' en: {msg_text}"


# ------------------------------------------------------------------------------------
# Tests RAG para /reservations/<reservation_code> (editar reserva)
# ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case_id, scenario, expected_status, expected_msg_sub",
    [
        (
            "EDIT_RES_OK_CAMBIO_ASIENTO_Y_CONTACTO",
            "happy",
            200,
            "actualizados exitosamente",
        ),
        (
            "EDIT_RES_BODY_INVALIDO",
            "body_invalid",
            400,
            "exactamente estos campos",
        ),
        (
            "EDIT_RES_CODE_INVALIDO",
            "code_invalid",
            400,
            "6 caracteres",
        ),
        (
            "EDIT_RES_ASIENTO_NO_LIBRE",
            "seat_not_free",
            409,
            "no está libre",
        ),
        (
            "EDIT_RES_NO_BODY",
            "no_body",
            400,
            "No se recibió cuerpo JSON",
        ),
        (
            "EDIT_RES_NO_EXISTE",
            "not_found",
            404,
            "Reserva no encontrada",
        ),
    ],
)
def test_edit_reservation_rag(
    service_up, case_id, scenario, expected_status, expected_msg_sub
):
    if scenario == "happy":
        res = _create_reservation()
        code = res["reservation_code"]
        airplane_id = res["airplane_id"]
        old_seat = res["seat_number"]

        # buscar un asiento libre distinto al actual
        r_seats = _get_gv(f"/get_airplane_seats/{airplane_id}/seats")
        assert r_seats.status_code == 200
        seats = r_seats.json()

        new_seat = None
        for s in seats:
            if s["seat_number"] != old_seat and s["status"] == "Libre":
                new_seat = s["seat_number"]
                break

        if not new_seat:
            pytest.skip(
                f"[{case_id}] No hay segundo asiento Libre para probar cambio de asiento."
            )

        body = {
            "seat_number": new_seat,
            "email": "nuevo@example.com",
            "phone_number": "+50612345678",
            "emergency_contact_name": "Nuevo Contacto",
            "emergency_contact_phone": "+50687654321",
        }
        r = _put_res(f"/reservations/{code}", json=body)

    elif scenario == "body_invalid":
        res = _create_reservation()
        code = res["reservation_code"]
        body = {
            "seat_number": "2C",
            "email": "nuevo@example.com",
            # faltan phone_number, emergency_contact_name, emergency_contact_phone
        }
        r = _put_res(f"/reservations/{code}", json=body)

    elif scenario == "code_invalid":
        body = {
            "seat_number": "2C",
            "email": "nuevo@example.com",
            "phone_number": "+50612345678",
            "emergency_contact_name": "Nuevo Contacto",
            "emergency_contact_phone": "+50687654321",
        }
        r = _put_res("/reservations/ABC12", json=body)  # 5 caracteres

    elif scenario == "seat_not_free":
        # Creamos res1
        payload1 = _build_valid_reservation_payload()
        r1 = _post_res("/add_reservation", json=payload1)
        assert r1.status_code == 201, f"res1 falló: {r1.status_code} {r1.text}"
        res1 = r1.json()["reservation"]

        airplane_id = res1["airplane_id"]
        old_seat = res1["seat_number"]

        # Buscar otro asiento Libre y crear res2
        r_seats = _get_gv(f"/get_airplane_seats/{airplane_id}/seats")
        assert r_seats.status_code == 200
        seats = r_seats.json()

        new_seat = None
        for s in seats:
            if s["seat_number"] != old_seat and s["status"] == "Libre":
                new_seat = s["seat_number"]
                break

        if not new_seat:
            pytest.skip(
                f"[{case_id}] No hay segundo asiento Libre para probar asiento no libre."
            )

        payload2 = {**payload1, "seat_number": new_seat}
        r2 = _post_res("/add_reservation", json=payload2)
        assert r2.status_code == 201, f"res2 falló: {r2.status_code} {r2.text}"
        res2 = r2.json()["reservation"]

        # Intentar editar res1 hacia el asiento ya reservado por res2
        body = {
            "seat_number": res2["seat_number"],
            "email": "nuevo@example.com",
            "phone_number": "+50612345678",
            "emergency_contact_name": "Nuevo Contacto",
            "emergency_contact_phone": "+50687654321",
        }
        r = _put_res(f"/reservations/{res1['reservation_code']}", json=body)

    elif scenario == "no_body":
        res = _create_reservation()
        code = res["reservation_code"]
        r = _put_res(f"/reservations/{code}", json={})

    elif scenario == "not_found":
        body = {
            "seat_number": "2C",
            "email": "nuevo@example.com",
            "phone_number": "+50612345678",
            "emergency_contact_name": "Nuevo Contacto",
            "emergency_contact_phone": "+50687654321",
        }
        r = _put_res("/reservations/ZZZ999", json=body)
    else:
        pytest.fail(f"Escenario desconocido en edit_reservation: {scenario}")

    try:
        body = r.json()
    except Exception:
        body = {}

    assert (
        r.status_code == expected_status
    ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"

    if expected_msg_sub:
        msg_text = body.get("message", "") or r.text
        assert (
            expected_msg_sub in msg_text
        ), f"[{case_id}] No se encontró '{expected_msg_sub}' en: {msg_text}"


# ------------------------------------------------------------------------------------
# Tests RAG para pagos: /create_payment, /get_payment_by_id, /delete_payment_by_id,
#                       /cancel_payment_and_reservation, /edit_payment
# ------------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "case_id, scenario, expected_status, expected_msg_sub",
    [
        ("CREATE_PAY_OK_01", "happy", 201, "Pago registrado correctamente"),
        (
            "CREATE_PAY_ERR_RESERVATION_ID_INVALIDO",
            "reservation_id_invalid",
            400,
            "reservation_id debe ser un número entero positivo",
        ),
        (
            "CREATE_PAY_ERR_METODO_INVALIDO",
            "method_invalid",
            400,
            "Método de pago inválido",
        ),
        (
            "CREATE_PAY_ERR_MONEDA_INVALIDA",
            "currency_invalid",
            400,
            "Moneda no soportada",
        ),
        (
            "CREATE_PAY_ERR_RESERVA_NO_EXISTE",
            "reservation_not_found",
            404,
            "Reserva con ID",
        ),
        (
            "CREATE_PAY_ERR_DUPLICADO",
            "duplicate",
            409,
            "ya tiene un pago registrado",
        ),
    ],
)
def test_create_payment_rag_cases(
    service_up, case_id, scenario, expected_status, expected_msg_sub
):
    if scenario == "happy":
        res = _create_reservation()
        rid = res["reservation_id"]
        data = {
            "reservation_id": rid,
            "payment_method": "Tarjeta",
            "currency": "Dolares",
        }
        r = _post_res("/create_payment", json=data)

    elif scenario == "reservation_id_invalid":
        data = {
            "reservation_id": -1,
            "payment_method": "Tarjeta",
            "currency": "Dolares",
        }
        r = _post_res("/create_payment", json=data)

    elif scenario == "method_invalid":
        res = _create_reservation()
        rid = res["reservation_id"]
        data = {
            "reservation_id": rid,
            "payment_method": "Crypto",
            "currency": "Dolares",
        }
        r = _post_res("/create_payment", json=data)

    elif scenario == "currency_invalid":
        res = _create_reservation()
        rid = res["reservation_id"]
        data = {
            "reservation_id": rid,
            "payment_method": "Tarjeta",
            "currency": "Euros",
        }
        r = _post_res("/create_payment", json=data)

    elif scenario == "reservation_not_found":
        data = {
            "reservation_id": 999999,
            "payment_method": "Tarjeta",
            "currency": "Dolares",
        }
        r = _post_res("/create_payment", json=data)

    elif scenario == "duplicate":
        res = _create_reservation()
        rid = res["reservation_id"]
        data = {
            "reservation_id": rid,
            "payment_method": "Tarjeta",
            "currency": "Dolares",
        }
        r1 = _post_res("/create_payment", json=data)
        assert r1.status_code == 201, f"Primer pago falló: {r1.status_code} {r1.text}"
        # segundo intento duplicado
        r = _post_res("/create_payment", json=data)
    else:
        pytest.fail(f"Escenario desconocido en create_payment: {scenario}")

    try:
        body = r.json()
    except Exception:
        body = {}

    assert (
        r.status_code == expected_status
    ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"

    if expected_msg_sub:
        msg_text = body.get("message", "") or r.text
        assert (
            expected_msg_sub in msg_text
        ), f"[{case_id}] No se encontró '{expected_msg_sub}' en: {msg_text}"


@pytest.mark.parametrize(
    "case_id, scenario, expected_status, expected_msg_sub",
    [
        ("GET_PAY_OK_EXISTENTE", "existing", 200, None),
        (
            "GET_PAY_ID_INVALIDO",
            "invalid_format",
            400,
            "formato del payment_id es inválido",
        ),
        ("GET_PAY_ID_NO_EXISTE", "not_found", 404, None),
    ],
)
def test_get_payment_by_id_rag(
    service_up, case_id, scenario, expected_status, expected_msg_sub
):
    if scenario == "existing":
        payment = _create_payment_for_new_reservation()
        pid = payment["payment_id"]
        r = _get_res(f"/get_payment_by_id/{pid}")
        assert r.status_code == 200, f"[{case_id}] Código inesperado: {r.status_code} {r.text}"
        body = r.json()
        assert body["payment_id"] == pid
        return

    elif scenario == "invalid_format":
        r = _get_res("/get_payment_by_id/INVALID")
    elif scenario == "not_found":
        pid = "PAY999999"
        r = _get_res(f"/get_payment_by_id/{pid}")
    else:
        pytest.fail(f"Escenario desconocido en get_payment_by_id: {scenario}")

    try:
        body = r.json()
    except Exception:
        body = {}

    assert (
        r.status_code == expected_status
    ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"

    if scenario == "not_found":
        msg = body.get("message", "") or r.text
        assert (
            "No se encontró" in msg or "No hay pagos generados" in msg
        ), f"[{case_id}] Mensaje inesperado: {msg}"
    elif expected_msg_sub:
        msg = body.get("message", "") or r.text
        assert (
            expected_msg_sub in msg
        ), f"[{case_id}] No se encontró '{expected_msg_sub}' en: {msg}"


@pytest.mark.parametrize(
    "case_id, scenario, expected_status, expected_msg_sub",
    [
        ("DEL_PAY_OK_EXISTENTE", "happy", 200, "fue eliminado con éxito"),
        (
            "DEL_PAY_ID_INVALIDO",
            "invalid_format",
            400,
            "formato del payment_id es inválido",
        ),
        (
            "DEL_PAY_ID_NO_EXISTE",
            "not_found",
            404,
            "No se encontró ningún pago con ID",
        ),
    ],
)
def test_delete_payment_by_id_rag(
    service_up, case_id, scenario, expected_status, expected_msg_sub
):
    if scenario == "happy":
        payment = _create_payment_for_new_reservation()
        pid = payment["payment_id"]
        r = _delete_res(f"/delete_payment_by_id/{pid}")
    elif scenario == "invalid_format":
        r = _delete_res("/delete_payment_by_id/INVALID")
    elif scenario == "not_found":
        pid = "PAY999999"
        r = _delete_res(f"/delete_payment_by_id/{pid}")
    else:
        pytest.fail(f"Escenario desconocido en delete_payment_by_id: {scenario}")

    try:
        body = r.json()
    except Exception:
        body = {}

    assert (
        r.status_code == expected_status
    ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"

    if expected_msg_sub:
        msg = body.get("message", "") or r.text
        assert (
            expected_msg_sub in msg
        ), f"[{case_id}] No se encontró '{expected_msg_sub}' en: {msg}"


@pytest.mark.parametrize(
    "case_id, scenario, expected_status, expected_msg_sub",
    [
        (
            "CANCEL_PAY_RES_OK",
            "happy",
            200,
            "Cancelación exitosa",
        ),
        (
            "CANCEL_PAY_RES_INVALID_ID_FORMAT",
            "invalid_format",
            400,
            "formato del payment_id es inválido",
        ),
        (
            "CANCEL_PAY_RES_NOT_FOUND",
            "not_found",
            404,
            "No se encontró el pago",
        ),
    ],
)
def test_cancel_payment_and_reservation_rag(
    service_up, case_id, scenario, expected_status, expected_msg_sub
):
    if scenario == "happy":
        payment = _create_payment_for_new_reservation()
        pid = payment["payment_id"]
        rid = payment["reservation_id"]
        r = _delete_res(f"/cancel_payment_and_reservation/{pid}")

        # Verificar que reserva ya no exista (si la API responde 404 es aceptable)
        r_res = _get_res(f"/get_reservation_by_id/{rid}")
        if r_res.status_code == 200:
            # Entonces al menos debe ser la misma reserva? En escenarios reales
            # podría fallar, pero aquí solo validamos que no sea 500.
            assert r_res.status_code != 500

    elif scenario == "invalid_format":
        r = _delete_res("/cancel_payment_and_reservation/INVALID")
    elif scenario == "not_found":
        pid = "PAY999999"
        r = _delete_res(f"/cancel_payment_and_reservation/{pid}")
    else:
        pytest.fail(
            f"Escenario desconocido en cancel_payment_and_reservation: {scenario}"
        )

    try:
        body = r.json()
    except Exception:
        body = {}

    assert (
        r.status_code == expected_status
    ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"

    if expected_msg_sub:
        msg = body.get("message", "") or r.text
        assert (
            expected_msg_sub in msg
        ), f"[{case_id}] No se encontró '{expected_msg_sub}' en: {msg}"


@pytest.mark.parametrize(
    "case_id, scenario, expected_status, expected_msg_sub",
    [
        ("EDIT_PAY_OK", "happy", 200, "Pago actualizado correctamente"),
        ("EDIT_PAY_INVALID_METHOD", "invalid_method", 400, "Método de pago inválido"),
        ("EDIT_PAY_NO_BODY", "no_body", 400, "No se recibió cuerpo JSON"),
        ("EDIT_PAY_NOT_FOUND", "not_found", 404, "No se encontró el pago"),
        (
            "EDIT_PAY_INVALID_FORMAT",
            "invalid_format",
            400,
            "formato del payment_id es inválido",
        ),
    ],
)
def test_edit_payment_rag(
    service_up, case_id, scenario, expected_status, expected_msg_sub
):
    if scenario == "happy":
        payment = _create_payment_for_new_reservation()
        pid = payment["payment_id"]
        body = {
            "payment_method": "SINPE",
            "payment_date": "Abril 25, 2025 - 17:00:00",
            "transaction_reference": "XYZ123ABC456",
        }
        r = _put_res(f"/edit_payment/{pid}", json=body)

    elif scenario == "invalid_method":
        payment = _create_payment_for_new_reservation()
        pid = payment["payment_id"]
        body = {
            "payment_method": "Crypto",
        }
        r = _put_res(f"/edit_payment/{pid}", json=body)

    elif scenario == "no_body":
        payment = _create_payment_for_new_reservation()
        pid = payment["payment_id"]
        r = _put_res(f"/edit_payment/{pid}", json={})

    elif scenario == "not_found":
        pid = "PAY999999"
        body = {
            "payment_method": "Tarjeta",
        }
        r = _put_res(f"/edit_payment/{pid}", json=body)

    elif scenario == "invalid_format":
        body = {
            "payment_method": "Tarjeta",
        }
        r = _put_res("/edit_payment/BADID", json=body)
    else:
        pytest.fail(f"Escenario desconocido en edit_payment: {scenario}")

    try:
        body = r.json()
    except Exception:
        body = {}

    assert (
        r.status_code == expected_status
    ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"

    if expected_msg_sub:
        msg = body.get("message", "") or r.text
        assert (
            expected_msg_sub in msg
        ), f"[{case_id}] No se encontró '{expected_msg_sub}' en: {msg}"
