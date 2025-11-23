"""
EXPERIMENTO_RAG_01_usuario_add_reservation

Pruebas de contrato para el endpoint:

    POST /usuario/add_reservation

Casos cubiertos (mínimos):
- Body vacío o ausente -> 400.
- Email inválido -> 400.
- Status inválido -> 400.
- Campo requerido faltante -> 400.
- Ruta no asociada al avión -> 400 (si hay suficientes rutas).
- Asiento no existe en el avión -> 400 (si hay datos suficientes).
- Asiento no libre -> 409 (si existe algún asiento Reservado/Pagado).
- Caso feliz: creación correcta de reserva -> 201.
"""

import os
import requests
import pytest

# Base URL del microservicio Usuario
BASE_URL = os.getenv("USUARIO_BASE_URL", "http://localhost:5003")


def _get(path: str, **kwargs) -> requests.Response:
    url = f"{BASE_URL}{path}"
    return requests.get(url, **kwargs)


def _post(path: str, **kwargs) -> requests.Response:
    url = f"{BASE_URL}{path}"
    return requests.post(url, **kwargs)


def _build_base_body(airplane_id: int, airplane_route_id: int, seat_number: str) -> dict:
    """
    Construye un body válido base para POST /usuario/add_reservation.
    """
    return {
        "passport_number": "A12345678",
        "full_name": "Usuario Prueba",
        "email": "usuario.prueba@example.com",
        "phone_number": "+50688888888",
        "emergency_contact_name": "Contacto Emergencia",
        "emergency_contact_phone": "+50677777777",
        "airplane_id": airplane_id,
        "airplane_route_id": airplane_route_id,
        "seat_number": seat_number,
        "status": "Reservado",
    }


def _find_route_and_free_seat():
    """
    Busca una combinación (ruta, asiento Libre) usando endpoints de Usuario:

    1) GET /get_all_airplanes_routes
    2) GET /get_seats_by_airplane_id/<airplane_id>/seats

    Retorna:
        (ruta_dict, asiento_dict) o None si no se puede determinar.
    """
    r_routes = _get("/get_all_airplanes_routes")
    if r_routes.status_code != 200:
        return None

    try:
        rutas = r_routes.json()
    except Exception:
        return None

    if not isinstance(rutas, list) or not rutas:
        return None

    # Tomar la primera ruta válida que tenga airplane_id.
    for ruta in rutas:
        airplane_id = ruta.get("airplane_id")
        route_id = ruta.get("airplane_route_id")
        if not isinstance(airplane_id, int) or not isinstance(route_id, int):
            continue

        r_seats = _get(f"/get_seats_by_airplane_id/{airplane_id}/seats")
        if r_seats.status_code != 200:
            continue

        try:
            seats = r_seats.json()
        except Exception:
            continue

        if not isinstance(seats, list):
            continue

        # Buscar asiento Libre
        for s in seats:
            if isinstance(s, dict) and s.get("status") == "Libre":
                return ruta, s

    return None


def _find_route_and_non_free_seat():
    """
    Busca una combinación (ruta, asiento NO libre) usando endpoints de Usuario.

    Retorna:
        (ruta_dict, asiento_dict) o None si no hay ningún asiento Reservado/Pagado.
    """
    r_routes = _get("/get_all_airplanes_routes")
    if r_routes.status_code != 200:
        return None

    try:
        rutas = r_routes.json()
    except Exception:
        return None

    if not isinstance(rutas, list) or not rutas:
        return None

    for ruta in rutas:
        airplane_id = ruta.get("airplane_id")
        if not isinstance(airplane_id, int):
            continue

        r_seats = _get(f"/get_seats_by_airplane_id/{airplane_id}/seats")
        if r_seats.status_code != 200:
            continue

        try:
            seats = r_seats.json()
        except Exception:
            continue

        if not isinstance(seats, list):
            continue

        for s in seats:
            if not isinstance(s, dict):
                continue
            status = s.get("status")
            if status in ("Reservado", "Pagado"):
                return ruta, s

    return None


def _find_two_routes_with_different_airplanes():
    """
    Busca dos rutas con airplane_id distintos para forzar el caso
    "La ruta X no está asociada al avión Y".

    Retorna:
        (ruta_1, ruta_2) o None si no hay suficientes rutas.
    """
    r_routes = _get("/get_all_airplanes_routes")
    if r_routes.status_code != 200:
        return None

    try:
        rutas = r_routes.json()
    except Exception:
        return None

    if not isinstance(rutas, list) or len(rutas) < 2:
        return None

    # Tomamos la primera ruta como base
    base = rutas[0]
    base_airplane_id = base.get("airplane_id")

    if base_airplane_id is None:
        return None

    # Buscar otra ruta con airplane_id distinto
    for otra in rutas[1:]:
        aid = otra.get("airplane_id")
        if aid is None:
            continue
        if aid != base_airplane_id:
            return base, otra

    return None


# ---------------------------------------------------------------------------
# Validaciones básicas (body / schema)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "case_id, body, expected_status, expected_msg_sub",
    [
        (
            "USR_ADDRES_BODY_VACIO_400",
            None,
            400,
            "No se recibió cuerpo JSON",
        ),
        (
            "USR_ADDRES_EMAIL_INVALIDO_400",
            {
                "passport_number": "A12345678",
                "full_name": "Usuario Prueba",
                "email": "no-es-email",
                "phone_number": "+50688888888",
                "emergency_contact_name": "Contacto Emergencia",
                "emergency_contact_phone": "+50677777777",
                "airplane_id": 1,
                "airplane_route_id": 1,
                "seat_number": "1A",
                "status": "Reservado",
            },
            400,
            "Error de validación",
        ),
        (
            "USR_ADDRES_STATUS_INVALIDO_400",
            {
                "passport_number": "A12345678",
                "full_name": "Usuario Prueba",
                "email": "usuario.prueba@example.com",
                "phone_number": "+50688888888",
                "emergency_contact_name": "Contacto Emergencia",
                "emergency_contact_phone": "+50677777777",
                "airplane_id": 1,
                "airplane_route_id": 1,
                "seat_number": "1A",
                "status": "Pagado",  # inválido, solo se permite "Reservado"
            },
            400,
            "Error de validación",
        ),
        (
            "USR_ADDRES_CAMPO_FALTANTE_400",
            {
                # Falta passport_number
                "full_name": "Usuario Prueba",
                "email": "usuario.prueba@example.com",
                "phone_number": "+50688888888",
                "emergency_contact_name": "Contacto Emergencia",
                "emergency_contact_phone": "+50677777777",
                "airplane_id": 1,
                "airplane_route_id": 1,
                "seat_number": "1A",
                "status": "Reservado",
            },
            400,
            "Error de validación",
        ),
    ],
)
def test_usuario_add_reservation_validaciones_basicas(
    case_id,
    body,
    expected_status,
    expected_msg_sub,
):
    """
    Casos de error de validación local para:
        POST /usuario/add_reservation

    - Body vacío o ausente -> 400.
    - Email inválido -> 400.
    - Status inválido -> 400.
    - Campo requerido faltante -> 400.
    """
    if body is None:
        r = _post("/usuario/add_reservation")
    else:
        r = _post("/usuario/add_reservation", json=body)

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        resp_json = {}
        msg_text = r.text

    assert (
        r.status_code == expected_status
    ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"

    assert expected_msg_sub.lower() in msg_text.lower(), (
        f"[{case_id}] No se encontró el texto esperado en el mensaje. "
        f"Buscaba: '{expected_msg_sub}' en: '{msg_text}'"
    )


# ---------------------------------------------------------------------------
# Casos con rutas y asientos (dependen de datos en GestiónVuelos)
# ---------------------------------------------------------------------------

def test_usuario_add_reservation_ruta_no_asociada_400():
    """
    Caso:
        La ruta existe pero no está asociada al avión enviado.

    Estrategia:
    1) Buscar dos rutas con airplane_id diferentes.
    2) Tomar:
        - airplane_route_id de la ruta A
        - airplane_id de la ruta B
    3) Buscar un asiento Libre en el avión de la ruta B.
    4) Enviar reserva con esa combinación para forzar:
        "La ruta X no está asociada al avión Y."
    """
    pair = _find_two_routes_with_different_airplanes()
    if pair is None:
        pytest.skip(
            "[USR_ADDRES_RUTA_NO_ASOCIADA_400] No se encontraron dos rutas con "
            "airplanes distintos."
        )

    ruta_a, ruta_b = pair
    route_id = ruta_a.get("airplane_route_id")
    airplane_id_b = ruta_b.get("airplane_id")

    if not isinstance(route_id, int) or not isinstance(airplane_id_b, int):
        pytest.skip(
            "[USR_ADDRES_RUTA_NO_ASOCIADA_400] Rutas no tienen IDs válidos."
        )

    # Buscar asiento Libre en avión de ruta_b
    r_seats = _get(f"/get_seats_by_airplane_id/{airplane_id_b}/seats")
    if r_seats.status_code != 200:
        pytest.skip(
            "[USR_ADDRES_RUTA_NO_ASOCIADA_400] No se pudieron obtener asientos "
            "para el avión de ruta_b."
        )

    try:
        seats = r_seats.json()
    except Exception:
        pytest.skip(
            "[USR_ADDRES_RUTA_NO_ASOCIADA_400] Respuesta de asientos no es JSON."
        )

    if not isinstance(seats, list) or not seats:
        pytest.skip(
            "[USR_ADDRES_RUTA_NO_ASOCIADA_400] Lista de asientos vacía o inválida."
        )

    seat_libre = next(
        (s for s in seats if isinstance(s, dict) and s.get("status") == "Libre"),
        None,
    )
    if not seat_libre:
        pytest.skip(
            "[USR_ADDRES_RUTA_NO_ASOCIADA_400] No se encontró ningún asiento Libre "
            "en el avión de ruta_b."
        )

    seat_number = seat_libre.get("seat_number")
    body = _build_base_body(
        airplane_id=airplane_id_b,
        airplane_route_id=route_id,  # ruta de otro avión
        seat_number=seat_number,
    )

    r = _post("/usuario/add_reservation", json=body)

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        resp_json = {}
        msg_text = r.text

    assert (
        r.status_code == 400
    ), f"[USR_ADDRES_RUTA_NO_ASOCIADA_400] Código inesperado: {r.status_code} {r.text}"

    assert "no está asociada al avión" in msg_text.lower(), (
        "[USR_ADDRES_RUTA_NO_ASOCIADA_400] No se encontró el texto esperado en el "
        f"mensaje. Mensaje: '{msg_text}'"
    )


def test_usuario_add_reservation_asiento_no_existe_400():
    """
    Caso:
        Asiento no existe en el avión.

    Estrategia:
    1) Buscar una ruta y un asiento Libre válidos.
    2) Construir un seat_number que no exista en la lista de asientos.
    3) Enviar reserva y validar 400 con mensaje de asiento no existente.
    """
    pair = _find_route_and_free_seat()
    if pair is None:
        pytest.skip(
            "[USR_ADDRES_ASIENTO_NO_EXISTE_400] No se encontró ruta + asiento Libre "
            "para probar."
        )

    ruta, seat_libre = pair
    airplane_id = ruta["airplane_id"]
    route_id = ruta["airplane_route_id"]

    # Obtener todos los asientos para este avión
    r_seats = _get(f"/get_seats_by_airplane_id/{airplane_id}/seats")
    if r_seats.status_code != 200:
        pytest.skip(
            "[USR_ADDRES_ASIENTO_NO_EXISTE_400] No se pudieron obtener asientos "
            "para el avión."
        )

    try:
        seats = r_seats.json()
    except Exception:
        pytest.skip(
            "[USR_ADDRES_ASIENTO_NO_EXISTE_400] Respuesta de asientos no es JSON."
        )

    if not isinstance(seats, list):
        pytest.skip(
            "[USR_ADDRES_ASIENTO_NO_EXISTE_400] La respuesta de asientos no es lista."
        )

    existentes = {s.get("seat_number") for s in seats if isinstance(s, dict)}
    # Elegir un seat_number que con alta probabilidad no exista
    candidate = "99Z"
    if candidate in existentes:
        candidate = "ZZ99"
    if candidate in existentes:
        candidate = "ASIENTO_INEXISTENTE"

    body = _build_base_body(
        airplane_id=airplane_id,
        airplane_route_id=route_id,
        seat_number=candidate,
    )

    r = _post("/usuario/add_reservation", json=body)

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        resp_json = {}
        msg_text = r.text

    assert (
        r.status_code == 400
    ), f"[USR_ADDRES_ASIENTO_NO_EXISTE_400] Código inesperado: {r.status_code} {r.text}"

    msg_lower = msg_text.lower()
    assert "asiento" in msg_lower and "no existe" in msg_lower, (
        "[USR_ADDRES_ASIENTO_NO_EXISTE_400] El mensaje no indica claramente que el "
        f"asiento no existe. Mensaje: '{msg_text}'"
    )


def test_usuario_add_reservation_asiento_no_libre_409():
    """
    Caso:
        Asiento existe pero no está Libre (Reservado o Pagado).

    Estrategia:
    1) Buscar una ruta y un asiento con status != 'Libre'.
    2) Enviar la reserva usando ese seat_number.
    3) Verificar que devuelva 409 y mensaje 'no está libre'.
    """
    pair = _find_route_and_non_free_seat()
    if pair is None:
        pytest.skip(
            "[USR_ADDRES_ASIENTO_NO_LIBRE_409] No se encontró ningún asiento "
            "Reservado/Pagado para probar el caso."
        )

    ruta, seat_no_free = pair
    airplane_id = ruta["airplane_id"]
    route_id = ruta["airplane_route_id"]
    seat_number = seat_no_free["seat_number"]

    body = _build_base_body(
        airplane_id=airplane_id,
        airplane_route_id=route_id,
        seat_number=seat_number,
    )

    r = _post("/usuario/add_reservation", json=body)

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        resp_json = {}
        msg_text = r.text

    assert (
        r.status_code == 409
    ), f"[USR_ADDRES_ASIENTO_NO_LIBRE_409] Código inesperado: {r.status_code} {r.text}"

    msg_lower = msg_text.lower()
    assert "asiento" in msg_lower and "no está libre" in msg_lower, (
        "[USR_ADDRES_ASIENTO_NO_LIBRE_409] El mensaje no indica claramente que el "
        f"asiento no está libre. Mensaje: '{msg_text}'"
    )


def test_usuario_add_reservation_happy_path():
    """
    Caso feliz:
        Crear una reserva para una combinación válida de
        (airplane_id, airplane_route_id, seat_number Libre).

    Pasos:
    1) Buscar ruta + asiento Libre.
    2) Construir body completo y válido.
    3) POST /usuario/add_reservation.
    4) Verificar:
       - status_code == 201
       - JSON con reservation_id, reservation_code, airplane_id,
         airplane_route_id, seat_number y status='Reservado'
         (dentro del objeto 'reservation' o en la raíz).
    """
    pair = _find_route_and_free_seat()
    if pair is None:
        pytest.skip(
            "[USR_ADDRES_OK_201] No se encontró ruta + asiento Libre para el caso feliz."
        )

    ruta, seat_libre = pair
    airplane_id = ruta["airplane_id"]
    route_id = ruta["airplane_route_id"]
    seat_number = seat_libre["seat_number"]

    body = _build_base_body(
        airplane_id=airplane_id,
        airplane_route_id=route_id,
        seat_number=seat_number,
    )

    r = _post("/usuario/add_reservation", json=body)

    assert (
        r.status_code == 201
    ), f"[USR_ADDRES_OK_201] Código inesperado: {r.status_code} {r.text}"

    resp_json = r.json()
    assert isinstance(resp_json, dict), (
        "[USR_ADDRES_OK_201] La respuesta no es un objeto JSON: "
        f"{resp_json}"
    )

    # Mensaje de éxito (opcional, pero útil)
    msg = resp_json.get("message", "")
    assert "reserva" in msg.lower() and "cread" in msg.lower(), (
        "[USR_ADDRES_OK_201] El mensaje no indica claramente que la reserva fue creada. "
        f"message='{msg}'"
    )

    # La reserva puede venir en resp_json["reservation"] o en la raíz
    reservation = resp_json.get("reservation")
    if not isinstance(reservation, dict):
        reservation = resp_json

    reservation_id = reservation.get("reservation_id")
    reservation_code = reservation.get("reservation_code")

    assert reservation_id, (
        "[USR_ADDRES_OK_201] Falta 'reservation_id' en la reserva: "
        f"{reservation}"
    )
    assert reservation_code, (
        "[USR_ADDRES_OK_201] Falta 'reservation_code' en la reserva: "
        f"{reservation}"
    )
    assert reservation.get("airplane_id") == airplane_id, (
        "[USR_ADDRES_OK_201] airplane_id devuelto no coincide."
    )
    assert reservation.get("airplane_route_id") == route_id, (
        "[USR_ADDRES_OK_201] airplane_route_id devuelto no coincide."
    )
    assert reservation.get("seat_number") == seat_number, (
        "[USR_ADDRES_OK_201] seat_number devuelto no coincide."
    )
    assert reservation.get("status") == "Reservado", (
        "[USR_ADDRES_OK_201] status devuelto no es 'Reservado'. "
        f"status={reservation.get('status')}"
    )
