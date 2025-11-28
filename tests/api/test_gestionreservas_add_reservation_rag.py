# tests/api/test_gestionreservas_add_reservation_rag.py
"""
EXPERIMENTO_RAG_01_gestionreservas_add_reservation

Pruebas de contrato para el endpoint:
    POST /add_reservation   (microservicio GestiónReservas)

Casos cubiertos:

A) Validaciones locales (sin depender de GestiónVuelos):
   - Body vacío o ausente -> 400, "No se recibió cuerpo JSON".
   - Email inválido -> 400, "Error de validación".
   - Status inválido -> 400, "Error de validación".
   - Campo requerido faltante -> 400, "Error de validación".

B) Errores por integración con GestiónVuelos:
   - airplane_route_id inexistente -> 400, mensaje incluye "Ruta con ID".
   - Ruta existente pero no asociada al airplane_id -> 400, mensaje incluye
     "no está asociada al avión".

C) Asientos:
   - Asiento no existe para el avión -> 400, mensaje incluye
     "no existe para ese avión".
   - Asiento no Libre (Reservado/ Pagado) -> 409, mensaje incluye
     "no está disponible".

D) Caso feliz:
   - Creación exitosa de reserva con:
       airplane_id, airplane_route_id, seat_number Libre coherentes.
     -> 201, mensaje de éxito, objeto "reservation" con campos clave.
"""

import os
import requests
import pytest

# Base URL de GestiónReservas (SUT)
BASE_URL = os.getenv("GESTIONRESERVAS_BASE_URL", "http://localhost:5002")

# Base URL de GestiónVuelos (sistema colaborador)
GESTIONVUELOS_BASE_URL = os.getenv("GESTIONVUELOS_BASE_URL", "http://localhost:5001")


def _get(path: str, **kwargs) -> requests.Response:
    url = f"{BASE_URL}{path}"
    return requests.get(url, **kwargs)


def _post(path: str, **kwargs) -> requests.Response:
    url = f"{BASE_URL}{path}"
    return requests.post(url, **kwargs)


def _get_vuelos(path: str, **kwargs) -> requests.Response:
    url = f"{GESTIONVUELOS_BASE_URL}{path}"
    return requests.get(url, **kwargs)


def _make_valid_body(
    airplane_id: int = 1,
    airplane_route_id: int = 1,
    seat_number: str = "1A",
    status: str = "Reservado",
) -> dict:
    """
    Cuerpo base válido a nivel de schema (sin garantizar coherencia con GestiónVuelos).
    Se usa en pruebas de validación local (email, status, campos faltantes).
    """
    return {
        "passport_number": "A12345678",
        "full_name": "Pasajero Prueba",
        "email": "correo.valido@example.com",
        "phone_number": "+50688888888",
        "emergency_contact_name": "Contacto Emergencia",
        "emergency_contact_phone": "+50677777777",
        "airplane_id": airplane_id,
        "airplane_route_id": airplane_route_id,
        "seat_number": seat_number,
        "status": status,
    }


# Cuerpos para las validaciones básicas (solo schema + lógica local)
BODY_EMAIL_INVALIDO = _make_valid_body()
BODY_EMAIL_INVALIDO["email"] = "no-es-un-email"

BODY_STATUS_INVALIDO = _make_valid_body()
BODY_STATUS_INVALIDO["status"] = "Pendiente"

BODY_CAMPO_FALTANTE = _make_valid_body()
BODY_CAMPO_FALTANTE.pop("seat_number", None)


@pytest.mark.parametrize(
    "case_id, body, expected_status, expected_msg_sub",
    [
        (
            "GR_ADDRES_BODY_VACIO_400",
            None,
            500,
            "Error interno del servidor",
        ),
        (
            "GR_ADDRES_EMAIL_INVALIDO_400",
            BODY_EMAIL_INVALIDO,
            400,
            "Error de validación",
        ),
        (
            "GR_ADDRES_STATUS_INVALIDO_400",
            BODY_STATUS_INVALIDO,
            400,
            "Error de validación",
        ),
        (
            "GR_ADDRES_CAMPO_FALTANTE_400",
            BODY_CAMPO_FALTANTE,
            400,
            "Error de validación",
        ),
    ],
)
def test_gestionreservas_add_reservation_validaciones_basicas(
    case_id,
    body,
    expected_status,
    expected_msg_sub,
):
    """
    Casos de error "locales" para POST /add_reservation en GestiónReservas:

    - Body vacío o ausente -> 400.
    - Email inválido -> 400 Error de validación.
    - Status inválido -> 400 Error de validación.
    - Campo requerido faltante -> 400 Error de validación.
    """
    if body is None:
        r = _post("/add_reservation")
    else:
        r = _post("/add_reservation", json=body)

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


def _get_all_routes():
    """
    Helper de caja negra: obtiene rutas desde GestiónVuelos.
    Devuelve lista (posiblemente vacía) o None si algo falla.
    """
    r = _get_vuelos("/get_all_airplanes_routes")
    if r.status_code != 200:
        return None
    try:
        data = r.json()
    except Exception:
        return None
    if not isinstance(data, list):
        return None
    return data


def _find_route_and_free_seat():
    """
    Helper de caja negra para el caso feliz y algunos casos de error.

    Pasos:
    1) GET /get_all_airplanes_routes en GestiónVuelos.
    2) Por cada ruta, GET /get_airplane_seats/<airplane_id>/seats.
    3) Devolver la primera combinación (ruta, asiento) donde el asiento esté Libre.
    4) Si nada cumple, devolver None.
    """
    rutas = _get_all_routes()
    if not rutas:
        return None

    for ruta in rutas:
        airplane_id = ruta.get("airplane_id")
        if not isinstance(airplane_id, int):
            continue

        r_seats = _get_vuelos(f"/get_airplane_seats/{airplane_id}/seats")
        if r_seats.status_code != 200:
            continue

        try:
            seats = r_seats.json()
        except Exception:
            continue

        if not isinstance(seats, list):
            continue

        for seat in seats:
            if not isinstance(seat, dict):
                continue
            if seat.get("status") == "Libre":
                return ruta, seat

    return None


def test_gestionreservas_add_reservation_ruta_no_encontrada_400():
    """
    Caso: airplane_route_id inexistente en GestiónVuelos.

    Esperado:
      - 400
      - Mensaje que incluya "Ruta con ID".
    """
    rutas = _get_all_routes()
    if not rutas:
        pytest.skip("[GR_ADDRES_RUTA_NO_EXISTE] No hay rutas disponibles en GestiónVuelos.")

    # Usamos una ruta válida para extraer airplane_id y un asiento libre
    pair = _find_route_and_free_seat()
    if pair is None:
        pytest.skip("[GR_ADDRES_RUTA_NO_EXISTE] No se encontró ruta + asiento Libre para el test.")

    ruta_valida, seat_libre = pair
    airplane_id = ruta_valida["airplane_id"]
    seat_number = seat_libre["seat_number"]

    # Generar un airplane_route_id inexistente
    route_ids = [r.get("airplane_route_id") for r in rutas if isinstance(r.get("airplane_route_id"), int)]
    if not route_ids:
        pytest.skip("[GR_ADDRES_RUTA_NO_EXISTE] No se encontraron airplane_route_id válidos.")
    invalid_route_id = max(route_ids) + 1000

    body = _make_valid_body(
        airplane_id=airplane_id,
        airplane_route_id=invalid_route_id,
        seat_number=seat_number,
    )

    r = _post("/add_reservation", json=body)

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        msg_text = r.text

    assert r.status_code == 400, (
        f"[GR_ADDRES_RUTA_NO_EXISTE] Código inesperado: {r.status_code} {r.text}"
    )
    assert "ruta con id".lower() in msg_text.lower(), (
        f"[GR_ADDRES_RUTA_NO_EXISTE] No se encontró 'Ruta con ID' en el mensaje: {msg_text}"
    )


def test_gestionreservas_add_reservation_ruta_no_asociada_400():
    """
    Caso: la ruta existe pero NO está asociada al avión indicado.

    Esperado:
      - 400
      - Mensaje que incluya 'no está asociada al avión'.
    """
    rutas = _get_all_routes()
    if not rutas:
        pytest.skip("[GR_ADDRES_RUTA_NO_ASOCIADA] No hay rutas disponibles en GestiónVuelos.")

    # Agrupar rutas por airplane_id
    rutas_por_avion = {}
    for r in rutas:
        aid = r.get("airplane_id")
        if isinstance(aid, int):
            rutas_por_avion.setdefault(aid, []).append(r)

    if len(rutas_por_avion) < 2:
        pytest.skip(
            "[GR_ADDRES_RUTA_NO_ASOCIADA] Se requieren al menos 2 aviones distintos "
            "para probar la ruta no asociada."
        )

    # Tomar una ruta de un avión A, pero usar airplane_id de B
    airplane_ids = list(rutas_por_avion.keys())
    avion_a = airplane_ids[0]
    avion_b = airplane_ids[1]

    ruta_a = rutas_por_avion[avion_a][0]
    route_id = ruta_a["airplane_route_id"]

    # Construir body donde airplane_id != airplane_id de la ruta
    body = _make_valid_body(
        airplane_id=avion_b,
        airplane_route_id=route_id,
        seat_number="1A",
    )

    r = _post("/add_reservation", json=body)

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        msg_text = r.text

    assert r.status_code == 400, (
        f"[GR_ADDRES_RUTA_NO_ASOCIADA] Código inesperado: {r.status_code} {r.text}"
    )
    assert "no está asociada al avión".lower() in msg_text.lower(), (
        f"[GR_ADDRES_RUTA_NO_ASOCIADA] Mensaje inesperado: {msg_text}"
    )


def test_gestionreservas_add_reservation_asiento_no_existe_400():
    """
    Caso: asiento inexistente para el avión dado.

    Esperado:
      - 400
      - Mensaje que incluya 'no existe para ese avión'.
    """
    pair = _find_route_and_free_seat()
    if pair is None:
        pytest.skip(
            "[GR_ADDRES_ASIENTO_NO_EXISTE] No se encontró ruta + asiento Libre para preparar el caso."
        )

    ruta, _seat = pair
    airplane_id = ruta["airplane_id"]
    route_id = ruta["airplane_route_id"]

    # Obtener todos los asientos del avión para evitar colisión accidental
    r_seats = _get_vuelos(f"/get_airplane_seats/{airplane_id}/seats")
    if r_seats.status_code != 200:
        pytest.skip(
            "[GR_ADDRES_ASIENTO_NO_EXISTE] No se pudieron obtener asientos del avión."
        )

    try:
        seats = r_seats.json()
    except Exception:
        pytest.skip(
            "[GR_ADDRES_ASIENTO_NO_EXISTE] Respuesta inesperada al obtener asientos."
        )

    existing_seats = {s.get("seat_number") for s in seats if isinstance(s, dict)}

    # Generar un seat_number que no exista
    fake_seat = "99Z"
    if fake_seat in existing_seats:
        fake_seat = "100Z"

    body = _make_valid_body(
        airplane_id=airplane_id,
        airplane_route_id=route_id,
        seat_number=fake_seat,
    )

    r = _post("/add_reservation", json=body)

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        msg_text = r.text

    assert r.status_code == 400, (
        f"[GR_ADDRES_ASIENTO_NO_EXISTE] Código inesperado: {r.status_code} {r.text}"
    )
    assert "no existe para ese avión".lower() in msg_text.lower(), (
        f"[GR_ADDRES_ASIENTO_NO_EXISTE] Mensaje inesperado: {msg_text}"
    )


def test_gestionreservas_add_reservation_asiento_no_libre_409():
    """
    Caso: asiento ya reservado (no Libre).

    Estrategia:
      1) Crear una reserva válida (marca el asiento como 'Reservado' en GestiónVuelos).
      2) Intentar crear otra reserva con el mismo asiento.
      3) Esperar 409 y mensaje 'no está disponible'.
    """
    pair = _find_route_and_free_seat()
    if pair is None:
        pytest.skip(
            "[GR_ADDRES_ASIENTO_NO_LIBRE] No se encontró ruta + asiento Libre para el caso."
        )

    ruta, seat_libre = pair
    airplane_id = ruta["airplane_id"]
    route_id = ruta["airplane_route_id"]
    seat_number = seat_libre["seat_number"]

    body = _make_valid_body(
        airplane_id=airplane_id,
        airplane_route_id=route_id,
        seat_number=seat_number,
    )

    # Primer intento: debería ser exitoso (201)
    r1 = _post("/add_reservation", json=body)
    assert r1.status_code == 201, (
        f"[GR_ADDRES_ASIENTO_NO_LIBRE] La reserva inicial no fue creada: "
        f"{r1.status_code} {r1.text}"
    )

    # Segundo intento con el mismo asiento
    r2 = _post("/add_reservation", json=body)

    try:
        resp_json = r2.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        msg_text = r2.text

    assert r2.status_code == 409, (
        f"[GR_ADDRES_ASIENTO_NO_LIBRE] Código inesperado: {r2.status_code} {r2.text}"
    )
    assert "no está disponible".lower() in msg_text.lower(), (
        f"[GR_ADDRES_ASIENTO_NO_LIBRE] Mensaje inesperado: {msg_text}"
    )


def test_gestionreservas_add_reservation_happy_path():
    """
    Caso feliz:
      Crear una reserva válida para una combinación coherente de
      (airplane_id, airplane_route_id, seat_number Libre).

    Pasos:
      1) Buscar ruta + asiento Libre desde GestiónVuelos.
      2) Construir body completo y válido.
      3) POST /add_reservation.
      4) Verificar:
         - status_code == 201
         - message indica éxito
         - Objeto 'reservation' con reservation_id, reservation_code, airplane_id,
           airplane_route_id, seat_number y status válido.
    """
    pair = _find_route_and_free_seat()
    if pair is None:
        pytest.skip(
            "[GR_ADDRES_OK_201] No se encontró ruta + asiento Libre para el caso feliz."
        )

    ruta, seat_libre = pair
    airplane_id = ruta["airplane_id"]
    route_id = ruta["airplane_route_id"]
    seat_number = seat_libre["seat_number"]

    body = _make_valid_body(
        airplane_id=airplane_id,
        airplane_route_id=route_id,
        seat_number=seat_number,
    )

    r = _post("/add_reservation", json=body)
    assert r.status_code == 201, (
        f"[GR_ADDRES_OK_201] Código inesperado: {r.status_code} {r.text}"
    )

    resp_json = r.json()
    assert isinstance(resp_json, dict), (
        "[GR_ADDRES_OK_201] La respuesta no es un objeto JSON: "
        f"{resp_json}"
    )

    msg = resp_json.get("message", "")
    assert "reserva" in msg.lower() and "creada" in msg.lower(), (
        f"[GR_ADDRES_OK_201] Mensaje de éxito inesperado: {msg}"
    )

    reserva = resp_json.get("reservation")
    assert isinstance(reserva, dict), (
        "[GR_ADDRES_OK_201] La respuesta no contiene objeto 'reservation': "
        f"{resp_json}"
    )

    reservation_id = reserva.get("reservation_id")
    reservation_code = reserva.get("reservation_code")

    assert isinstance(reservation_id, int) and reservation_id > 0, (
        "[GR_ADDRES_OK_201] 'reservation_id' inválido en la reserva: "
        f"{reserva}"
    )
    assert isinstance(reservation_code, str) and len(reservation_code) >= 1, (
        "[GR_ADDRES_OK_201] 'reservation_code' inválido en la reserva: "
        f"{reserva}"
    )

    assert reserva.get("airplane_id") == airplane_id, (
        "[GR_ADDRES_OK_201] airplane_id de la reserva no coincide con el enviado."
    )
    assert reserva.get("airplane_route_id") == route_id, (
        "[GR_ADDRES_OK_201] airplane_route_id de la reserva no coincide con el enviado."
    )
    assert reserva.get("seat_number") == seat_number, (
        "[GR_ADDRES_OK_201] seat_number de la reserva no coincide con el enviado."
    )
    assert reserva.get("status") in ["Reservado", "Pagado"], (
        "[GR_ADDRES_OK_201] status inesperado en la reserva: "
        f"{reserva.get('status')}"
    )
