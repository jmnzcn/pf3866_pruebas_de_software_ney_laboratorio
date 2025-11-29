# tests/api/test_usuario.py
import os
import random
import string

import pytest
import requests

# ---------------------------------------------------------------------------
# Configuración base
# ---------------------------------------------------------------------------

BASE_URL = (
    os.getenv("USUARIO_BASE_URL")
    or os.getenv("USUARIO_SERVICE_URL", "http://localhost:5003")
)

SPEC_CANDIDATES = [
    "/openapi.json",
    "/apispec_1.json",
    "/docs/openapi.json",
    "/docs/apispec_1.json",
    "/swagger.json",
]


# ---------------------------------------------------------------------------
# Utilidades genéricas HTTP / helpers
# ---------------------------------------------------------------------------

def _rand_suffix(n: int = 6) -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))


def _get_json(path: str, **kwargs):
    r = requests.get(f"{BASE_URL}{path}", timeout=kwargs.pop("timeout", 10))
    body = None
    if r.headers.get("content-type", "").startswith("application/json"):
        try:
            body = r.json()
        except Exception:
            body = None
    return r, body


def _post_json(path: str, payload: dict, **kwargs):
    r = requests.post(
        f"{BASE_URL}{path}", json=payload, timeout=kwargs.pop("timeout", 10)
    )
    body = None
    if r.headers.get("content-type", "").startswith("application/json"):
        try:
            body = r.json()
        except Exception:
            body = None
    return r, body


def _put_json(path: str, payload: dict, **kwargs):
    r = requests.put(
        f"{BASE_URL}{path}", json=payload, timeout=kwargs.pop("timeout", 10)
    )
    body = None
    if r.headers.get("content-type", "").startswith("application/json"):
        try:
            body = r.json()
        except Exception:
            body = None
    return r, body


def _delete(path: str, **kwargs):
    r = requests.delete(f"{BASE_URL}{path}", timeout=kwargs.pop("timeout", 10))
    body = None
    if r.headers.get("content-type", "").startswith("application/json"):
        try:
            body = r.json()
        except Exception:
            body = None
    return r, body


def _fetch_spec():
    """
    Intenta obtener la especificación OpenAPI/Swagger publicada por el servicio.
    Si no encuentra nada, devuelve None (los tests lo tratan como opcional).
    """
    for ep in SPEC_CANDIDATES:
        try:
            r = requests.get(f"{BASE_URL}{ep}", timeout=5)
            if r.status_code == 200 and "application/json" in r.headers.get(
                "content-type", ""
            ):
                return r.json()
        except Exception:
            pass
    return None


def _fetch_status_enum_from_spec():
    """
    Intenta descubrir el enum de 'status' para /usuario/add_reservation
    a partir de la especificación OpenAPI (si existe).

    Retorna:
        - lista de valores enum si los encuentra
        - None si no logra extraerlos
    """
    spec = _fetch_spec()
    if not spec or "paths" not in spec:
        return None

    paths = spec.get("paths", {})
    for path, item in paths.items():
        if "add_reservation" not in path:
            continue

        post_op = item.get("post")
        if not isinstance(post_op, dict):
            continue

        rb = post_op.get("requestBody", {})
        content = rb.get("content", {}).get("application/json", {})
        schema = content.get("schema", {})

        def find_enum(node):
            if not isinstance(node, dict):
                return None
            props = node.get("properties", {})
            st = props.get("status")
            if isinstance(st, dict) and isinstance(st.get("enum"), list):
                return st["enum"]

            for key in ("oneOf", "anyOf", "allOf"):
                if key in node and isinstance(node[key], list):
                    for sub in node[key]:
                        found = find_enum(sub)
                        if found:
                            return found
            return None

        enum_vals = find_enum(schema)
        if enum_vals:
            return enum_vals

    return None


def _choose_status_for_reservation():
    """
    Devuelve un valor de 'status' a usar en /usuario/add_reservation:

    - Preferentemente, el primer valor del enum obtenido de OpenAPI.
    - Si no hay spec o enum, usa 'Reservado' como fallback.
    """
    enum_vals = _fetch_status_enum_from_spec()
    if isinstance(enum_vals, list) and enum_vals:
        return enum_vals[0]
    return "Reservado"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def service_up():
    """
    Verifica que el servicio Usuario esté levantado.
    Si /health no responde 200, se saltan todos los tests de este archivo.
    """
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        if r.status_code != 200:
            pytest.skip("Usuario no responde 200 en /health")
    except Exception:
        pytest.skip("Usuario no está disponible en BASE_URL")
    return True


# ---------------------------------------------------------------------------
# Tests de diagnóstico / contrato general
# ---------------------------------------------------------------------------

def test_usuario_health_contract(service_up):
    r, body = _get_json("/health")
    assert r.status_code == 200, f"/health retornó {r.status_code}: {r.text}"
    assert isinstance(body, dict), f"/health no retornó JSON dict: {body}"

    status = body.get("status")
    service = body.get("service")

    assert status == "ok", f"Se esperaba status='ok' en /health, vino: {status!r}"
    assert service in ("usuario", "Usuario", None), (
        f"El campo 'service' en /health es inesperado: {service!r}"
    )


def test_usuario_openapi_present_optional(service_up):
    """
    Test opcional: solo verifica que exista algún spec OpenAPI/Swagger,
    similar a test_gestionvuelos.py.
    """
    spec = _fetch_spec()
    if not spec:
        pytest.skip("Usuario no publica OpenAPI/Swagger en las rutas conocidas.")

    assert isinstance(spec, dict), "La especificación devuelta no es un dict JSON."
    paths = spec.get("paths", {})
    assert isinstance(paths, dict), "OpenAPI.paths no es un dict."
    assert len(paths) > 0, "OpenAPI.paths viene vacío."

    # No exigimos que /health esté documentado, solo que haya paths en general.
    if not any("/health" in p for p in paths.keys()):
        print("AVISO: /health no aparece documentado en OpenAPI (no es error fatal).")


# ---------------------------------------------------------------------------
# Helpers de dominio para el flujo end-to-end
# ---------------------------------------------------------------------------

def _find_route_and_free_seat_via_usuario():
    """
    Busca una combinación (ruta, asiento Libre) a través de los endpoints
    expuestos por Usuario:

        - GET /get_all_airplanes_routes
        - GET /get_seats_by_airplane_id/<airplane_id>/seats

    Retorna (ruta, asiento) o None si no encuentra nada utilizable.
    """
    r_routes, routes = _get_json("/get_all_airplanes_routes")
    if r_routes.status_code != 200 or not isinstance(routes, list) or not routes:
        return None

    for ruta in routes:
        airplane_id = ruta.get("airplane_id")
        if not isinstance(airplane_id, int):
            continue

        r_seats, seats = _get_json(f"/get_seats_by_airplane_id/{airplane_id}/seats")
        if r_seats.status_code != 200 or not isinstance(seats, list):
            continue

        for seat in seats:
            if not isinstance(seat, dict):
                continue
            if seat.get("status") == "Libre":
                return ruta, seat

    return None


def _extract_reservation_from_body(body):
    """
    Muchos endpoints de Usuario regresan
    {
      "message": "...",
      "reservation": {...}
    }
    pero otros pueden devolver directamente la reserva.

    Esta función intenta extraer un dict de reserva válido.
    """
    if not isinstance(body, dict):
        return None

    if isinstance(body.get("reservation"), dict):
        return body["reservation"]

    # fallback: todo el body podría ser la reserva
    if "reservation_id" in body and "reservation_code" in body:
        return body

    return None


def _extract_payment_from_body(body):
    """
    Similar a _extract_reservation_from_body, pero para pagos.
    """
    if not isinstance(body, dict):
        return None

    if isinstance(body.get("payment"), dict):
        return body["payment"]

    if "payment_id" in body and "reservation_id" in body:
        return body

    return None


# ---------------------------------------------------------------------------
# Flujo end-to-end: reserva + pago + cancelación
# ---------------------------------------------------------------------------

def test_usuario_end_to_end_reservation_payment_and_cancel(service_up):
    """
    Flujo de alto nivel a través del microservicio Usuario:

      1) Obtener ruta + asiento Libre (vía Usuario -> GestiónVuelos).
      2) Crear reserva vía POST /usuario/add_reservation.
      3) Verificar contra GET /get_reservation_by_id y /get_reservation_by_code.
      4) Listar reservas con GET /get_all_reservations y encontrar la creada.
      5) Crear pago vía POST /usuario/create_payment.
      6) Verificar GET /get_payment_by_id y /get_all_payments.
      7) Cancelar pago y reserva vía DELETE /usuario/cancel_payment_and_reservation/<payment_id>.
      8) Verificar que el pago ya no se encuentre.
    """

    # 1) Buscar ruta + asiento Libre
    pair = _find_route_and_free_seat_via_usuario()
    if pair is None:
        pytest.skip(
            "[USR_E2E] No se encontró combinación (ruta, asiento Libre) a través de Usuario."
        )

    ruta, seat_libre = pair
    airplane_id = ruta.get("airplane_id")
    route_id = ruta.get("airplane_route_id")
    seat_number = seat_libre.get("seat_number")

    assert isinstance(airplane_id, int)
    assert isinstance(route_id, int)
    assert isinstance(seat_number, str) and seat_number

    # 2) Crear reserva vía Usuario
    status_value = _choose_status_for_reservation()

    add_payload = {
        "passport_number": "E2E123456",
        "full_name": f"Test Usuario {_rand_suffix()}",
        "email": f"e2e+{_rand_suffix()}@example.com",
        "phone_number": "+50680000000",
        "emergency_contact_name": "Contacto E2E",
        "emergency_contact_phone": "+50681111111",
        "airplane_id": airplane_id,
        "airplane_route_id": route_id,
        "seat_number": seat_number,
        "status": status_value,
    }

    r_add, body_add = _post_json("/usuario/add_reservation", add_payload)
    assert r_add.status_code in (200, 201), (
        f"[USR_E2E] Error al crear reserva vía Usuario: "
        f"{r_add.status_code} {r_add.text}"
    )

    reserva = _extract_reservation_from_body(body_add or {})
    assert isinstance(reserva, dict), (
        f"[USR_E2E] No se pudo extraer una reserva válida de la respuesta: "
        f"{body_add}"
    )

    reservation_id = reserva.get("reservation_id")
    reservation_code = reserva.get("reservation_code")

    assert isinstance(reservation_id, int) and reservation_id > 0
    assert isinstance(reservation_code, str) and len(reservation_code) >= 4

    assert reserva.get("airplane_id") == airplane_id
    assert reserva.get("airplane_route_id") == route_id
    assert reserva.get("seat_number") == seat_number

    # 3) Verificación por ID y por código
    r_by_id, body_by_id = _get_json(f"/get_reservation_by_id/{reservation_id}")
    assert r_by_id.status_code == 200, (
        f"[USR_E2E] GET /get_reservation_by_id/{reservation_id} devolvió "
        f"{r_by_id.status_code}: {r_by_id.text}"
    )
    assert body_by_id.get("reservation_id") == reservation_id

    r_by_code, body_by_code = _get_json(f"/get_reservation_by_code/{reservation_code}")
    assert r_by_code.status_code == 200, (
        f"[USR_E2E] GET /get_reservation_by_code/{reservation_code} devolvió "
        f"{r_by_code.status_code}: {r_by_code.text}"
    )
    assert body_by_code.get("reservation_code") == reservation_code

    # 4) Verificar que la reserva aparezca en el listado general
    r_all_res, all_res = _get_json("/get_all_reservations")
    assert r_all_res.status_code == 200, (
        f"[USR_E2E] GET /get_all_reservations devolvió "
        f"{r_all_res.status_code}: {r_all_res.text}"
    )

    if isinstance(all_res, list):
        assert any(
            (r.get("reservation_id") == reservation_id) for r in all_res
        ), (
            "[USR_E2E] La reserva recién creada no aparece en /get_all_reservations."
        )
    elif isinstance(all_res, dict) and "message" in all_res:
        pytest.fail(
            "[USR_E2E] /get_all_reservations devolvió un mensaje de 'sin reservas' "
            "a pesar de haber creado una."
        )

    # 5) Crear pago para la reserva
    pay_payload = {
        "reservation_id": reservation_id,
        "payment_method": "Tarjeta",
        "currency": "Dolares",
    }
    r_pay, body_pay = _post_json("/usuario/create_payment", pay_payload)
    assert r_pay.status_code in (200, 201), (
        f"[USR_E2E] Error al crear pago vía Usuario: "
        f"{r_pay.status_code} {r_pay.text}"
    )

    payment = _extract_payment_from_body(body_pay or {})
    assert isinstance(payment, dict), (
        f"[USR_E2E] No se pudo extraer un pago válido de la respuesta: "
        f"{body_pay}"
    )

    payment_id = payment.get("payment_id")
    assert isinstance(payment_id, str) and payment_id, (
        "[USR_E2E] payment_id inválido en respuesta de create_payment."
    )
    assert payment.get("reservation_id") == reservation_id

    # 6) Verificar /get_payment_by_id y /get_all_payments
    r_by_pid, body_by_pid = _get_json(f"/get_payment_by_id/{payment_id}")
    assert r_by_pid.status_code == 200, (
        f"[USR_E2E] GET /get_payment_by_id/{payment_id} devolvió "
        f"{r_by_pid.status_code}: {r_by_pid.text}"
    )
    assert body_by_pid.get("payment_id") == payment_id

    r_all_pay, all_pay = _get_json("/get_all_payments")
    assert r_all_pay.status_code == 200, (
        f"[USR_E2E] GET /get_all_payments devolvió "
        f"{r_all_pay.status_code}: {r_all_pay.text}"
    )
    if isinstance(all_pay, list):
        assert any(
            (p.get("payment_id") == payment_id) for p in all_pay
        ), (
            "[USR_E2E] El pago recién creado no aparece en /get_all_payments."
        )
    elif isinstance(all_pay, dict) and "message" in all_pay:
        pytest.fail(
            "[USR_E2E] /get_all_payments devolvió un mensaje de 'sin pagos' "
            "a pesar de haber creado uno."
        )

    # 7) Cancelar pago y reserva
    r_cancel, body_cancel = _delete(
        f"/usuario/cancel_payment_and_reservation/{payment_id}"
    )
    assert r_cancel.status_code == 200, (
        f"[USR_E2E] Error al cancelar pago+reserva: "
        f"{r_cancel.status_code} {r_cancel.text}"
    )

    msg_cancel = (body_cancel or {}).get("message", "")
    assert msg_cancel, (
        "[USR_E2E] La respuesta de cancelación no incluye mensaje."
    )

    # 8) Verificar que el pago ya no se encuentre
    r_check_pay, body_check_pay = _get_json(f"/get_payment_by_id/{payment_id}")
    assert r_check_pay.status_code in (404, 400), (
        f"[USR_E2E] Se esperaba que el GET del pago cancelado devolviera 404/400, "
        f"pero vino {r_check_pay.status_code}: {r_check_pay.text}"
    )
    if isinstance(body_check_pay, dict):
        msg_check = (body_check_pay.get("message") or body_check_pay.get("error") or "").lower()
        assert (
            "no se encontró" in msg_check
            or "no hay pagos" in msg_check
            or "no existe" in msg_check
        ), (
            f"[USR_E2E] Mensaje inesperado al consultar pago cancelado: {body_check_pay}"
        )
