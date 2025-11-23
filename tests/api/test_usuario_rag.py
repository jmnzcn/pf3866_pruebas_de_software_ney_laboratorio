# tests/api/test_usuario_rag.py
import os
import random
import string

import pytest
import requests

BASE_URL = os.getenv("USUARIO_BASE_URL", "http://localhost:5003")


def _url(path: str) -> str:
    """Construye la URL absoluta contra el microservicio Usuario."""
    return BASE_URL.rstrip("/") + path


def _get(path: str, **kwargs) -> requests.Response:
    return requests.get(_url(path), timeout=20, **kwargs)


def _post(path: str, **kwargs) -> requests.Response:
    return requests.post(_url(path), timeout=20, **kwargs)


@pytest.fixture(scope="session")
def service_up():
    """
    Verifica que el microservicio Usuario esté accesible.
    Si no lo está, se hace skip de TODAS las pruebas de este archivo.
    """
    try:
        r = _get("/get_all_airplanes_routes")
    except Exception as e:  # conexión rechazada, etc.
        pytest.skip(f"Usuario no está levantado en {BASE_URL}: {e}")

    # Aceptamos 200 (hay rutas) o 404 (no hay rutas, pero el servicio responde)
    if r.status_code not in (200, 404):
        pytest.skip(
            f"Usuario respondió código inesperado en /get_all_airplanes_routes: "
            f"{r.status_code} {r.text}"
        )
    return True


# ---------------------------------------------------------------------
# Helpers para construir payloads y encontrar una ruta/asiento válido
# ---------------------------------------------------------------------


def _build_base_payload(airplane_id: int, route_id: int, seat_number: str) -> dict:
    """Payload mínimo válido para /usuario/add_reservation."""
    return {
        "passport_number": "A12345678",
        "full_name": "Usuario Prueba RAG",
        "email": "rag.tester@example.com",
        "phone_number": "+50688889999",
        "emergency_contact_name": "Contacto RAG",
        "emergency_contact_phone": "+50677778888",
        "airplane_id": airplane_id,
        "airplane_route_id": route_id,
        "seat_number": seat_number,
        "status": "Reservado",
    }


def _find_valid_route_and_free_seat():
    """
    Usa los propios endpoints de Usuario para obtener:
    - una ruta válida (airplane_id + airplane_route_id)
    - un asiento Libre para ese avión.

    Si no se encuentra nada, hace pytest.skip para no romper las pruebas.
    """
    r_routes = _get("/get_all_airplanes_routes")
    assert r_routes.status_code == 200, (
        f"GET /get_all_airplanes_routes no devolvió 200: "
        f"{r_routes.status_code} {r_routes.text}"
    )

    routes = r_routes.json()
    assert isinstance(routes, list) and routes, "La lista de rutas está vacía."

    # Intentar con varias rutas hasta encontrar al menos un asiento Libre
    for route in routes:
        airplane_id = route.get("airplane_id")
        route_id = route.get("airplane_route_id")
        if airplane_id is None or route_id is None:
            continue

        r_seats = _get(f"/get_seats_by_airplane_id/{airplane_id}/seats")
        if r_seats.status_code != 200:
            continue

        seats = r_seats.json()
        free = [s["seat_number"] for s in seats if s.get("status") == "Libre"]
        if free:
            return airplane_id, route_id, free[0]

    pytest.skip("No se encontraron asientos 'Libre' para probar /usuario/add_reservation.")


# ---------------------------------------------------------------------
# Pruebas RAG sobre /usuario/add_reservation
# ---------------------------------------------------------------------


@pytest.mark.parametrize(
    "case_id, scenario, expected_status, expected_msg_sub",
    [
        # Casos de validación local (no dependen de otros microservicios)
        (
            "USR_ADD_BODY_VACIO",
            "body_empty",
            400,
            "No se recibió cuerpo JSON",
        ),
        (
            "USR_ADD_EMAIL_INVALIDO",
            "email_invalid",
            400,
            "Error de validación",
        ),
        (
            "USR_ADD_STATUS_INVALIDO",
            "status_invalid",
            400,
            "Error de validación",
        ),
        (
            "USR_ADD_RUTA_NO_EXISTE",
            "route_not_exists",
            400,
            "Ruta con ID",
        ),
        # Caso feliz completo
        (
            "USR_ADD_OK_01",
            "happy",
            201,
            "Reserva",  # parte del mensaje/estructura esperada
        ),
    ],
)
def test_usuario_add_reservation_rag_cases(
    service_up,
    case_id,
    scenario,
    expected_status,
    expected_msg_sub,
):
    """
    Casos de prueba sugeridos para /usuario/add_reservation basados en el contrato
    documentado en ENDPOINTS_Usuario.md y EXPERIMENTO_RAG_01_usuario_add_reservation.md.
    """
    if scenario == "body_empty":
        # Enviar la petición SIN body JSON (ni parámetro json),
        # para que request.get_json() devuelva None y el endpoint responda 400
        r = _post("/usuario/add_reservation")

    elif scenario == "email_invalid":
        # Payload con email inválido -> falla validación local (Marshmallow)
        payload = _build_base_payload(airplane_id=1, route_id=1, seat_number="1A")
        payload["email"] = "no-es-email"
        r = _post("/usuario/add_reservation", json=payload)

    elif scenario == "status_invalid":
        # status distinto de "Reservado"
        payload = _build_base_payload(airplane_id=1, route_id=1, seat_number="1A")
        payload["status"] = "Pagado"
        r = _post("/usuario/add_reservation", json=payload)

    elif scenario == "route_not_exists":
        # airplane_route_id muy alto que seguramente no exista
        payload = _build_base_payload(airplane_id=1, route_id=999_999, seat_number="1A")
        r = _post("/usuario/add_reservation", json=payload)

    elif scenario == "happy":
        # Caso feliz: seleccionar ruta real + asiento Libre
        airplane_id, route_id, seat_number = _find_valid_route_and_free_seat()
        payload = _build_base_payload(airplane_id, route_id, seat_number)
        r = _post("/usuario/add_reservation", json=payload)

    else:
        pytest.fail(f"Escenario desconocido en /usuario/add_reservation: {scenario}")

    # Intentar parsear JSON, pero no romper si no es JSON
    try:
        body = r.json()
    except Exception:
        body = {}

    msg_text = (
        body.get("message", "")
        or body.get("error", "")
        or r.text
    )

    if scenario == "happy":
        # En el caso feliz esperamos 201 exacto
        assert (
            r.status_code == expected_status
        ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"

        # No atamos el test a un mensaje exacto, solo verificamos que haya
        # alguna señal de reserva exitosa en el body.
        assert "reservation" in body, f"[{case_id}] No viene 'reservation' en la respuesta: {body}"
    else:
        assert (
            r.status_code == expected_status
        ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"
        assert expected_msg_sub in msg_text, (
            f"[{case_id}] No se encontró el texto esperado en el mensaje. "
            f"Buscaba: '{expected_msg_sub}' en: '{msg_text}'"
        )
