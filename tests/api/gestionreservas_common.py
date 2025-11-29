# tests/api/gestionreservas_common.py
"""
Helpers compartidos para los tests RAG de GestiónReservas.
"""

from __future__ import annotations

import os
import re
import requests


# ---------------------------------------------------------------------------
# Base URLs de microservicios (tal como en los tests actuales)
# ---------------------------------------------------------------------------

BASE_URL_RESERVAS = os.getenv("GESTIONRESERVAS_BASE_URL", "http://localhost:5002")
BASE_URL_VUELOS = os.getenv("GESTIONVUELOS_BASE_URL", "http://localhost:5001")
BASE_URL_USUARIO = os.getenv("USUARIO_BASE_URL", "http://localhost:5003")


# ---------------------------------------------------------------------------
# Wrappers HTTP genéricos
# ---------------------------------------------------------------------------

def get_reservas(path: str, timeout: int = 20, **kwargs) -> requests.Response:
    """
    GET a GestiónReservas.
    """
    return requests.get(f"{BASE_URL_RESERVAS}{path}", timeout=timeout, **kwargs)


def post_reservas(path: str, timeout: int = 20, **kwargs) -> requests.Response:
    """
    POST a GestiónReservas.
    """
    return requests.post(f"{BASE_URL_RESERVAS}{path}", timeout=timeout, **kwargs)


def put_reservas(path: str, timeout: int = 20, **kwargs) -> requests.Response:
    """
    PUT a GestiónReservas.
    """
    return requests.put(f"{BASE_URL_RESERVAS}{path}", timeout=timeout, **kwargs)


def delete_reservas(path: str, timeout: int = 20, **kwargs) -> requests.Response:
    """
    DELETE a GestiónReservas.
    """
    return requests.delete(f"{BASE_URL_RESERVAS}{path}", timeout=timeout, **kwargs)


def get_vuelos(path: str, timeout: int = 20, **kwargs) -> requests.Response:
    """
    GET a GestiónVuelos.
    """
    return requests.get(f"{BASE_URL_VUELOS}{path}", timeout=timeout, **kwargs)


def get_usuario(path: str, timeout: int = 20, **kwargs) -> requests.Response:
    """
    GET al microservicio Usuario.
    """
    return requests.get(f"{BASE_URL_USUARIO}{path}", timeout=timeout, **kwargs)


# ---------------------------------------------------------------------------
# Helpers para /add_reservation (GestiónReservas) y GestiónVuelos
# ---------------------------------------------------------------------------

def make_add_reservation_body(
    airplane_id: int = 1,
    airplane_route_id: int = 1,
    seat_number: str = "1A",
    status: str = "Reservado",
) -> dict:
    """
    Cuerpo base válido para POST /add_reservation (GestiónReservas),
    tal como en test_gestionreservas_add_reservation_rag.py.

    Nota: la coherencia con GestiónVuelos (ruta y asiento válidos y libres)
    se controla en los tests, no aquí.
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


def get_all_routes_from_vuelos() -> list | None:
    """
    Envuelve GET /get_all_airplanes_routes en GestiónVuelos.

    Devuelve:
      - lista de rutas (posiblemente vacía) si todo va bien,
      - None si algo falla o la respuesta no es lista.
    """
    r = get_vuelos("/get_all_airplanes_routes")
    if r.status_code != 200:
        return None

    try:
        data = r.json()
    except Exception:
        return None

    if not isinstance(data, list):
        return None

    return data


def find_route_and_free_seat() -> tuple[dict, dict] | None:
    """
    Replica la lógica de _find_route_and_free_seat de
    test_gestionreservas_add_reservation_rag.py.

    Pasos:
      1) GET /get_all_airplanes_routes en GestiónVuelos.
      2) Para cada ruta, GET /get_airplane_seats/<airplane_id>/seats.
      3) Devolver la primera (ruta, asiento) donde el asiento esté Libre.
      4) Si no hay ninguna combinación, devuelve None.
    """
    rutas = get_all_routes_from_vuelos()
    if not rutas:
        return None

    for ruta in rutas:
        airplane_id = ruta.get("airplane_id")
        if not isinstance(airplane_id, int):
            continue

        r_seats = get_vuelos(f"/get_airplane_seats/{airplane_id}/seats")
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


# ---------------------------------------------------------------------------
# Helpers para reservas: búsqueda genérica y asientos libres
# ---------------------------------------------------------------------------

def find_any_reservation() -> dict | None:
    """
    Replica _find_any_reservation de test_gestionreservas_edit_reservation_rag.py.

    Estrategia:
      1) Intentar vía Usuario: GET /get_all_reservations.
      2) Si falla, fallback directo a GestiónReservas: GET /get_fake_reservations.
      3) Devuelve la primera reserva encontrada o None.
    """
    # 1) Intentar vía Usuario
    try:
        r_usr = get_usuario("/get_all_reservations")
        if r_usr.status_code == 200:
            data = r_usr.json()
            if isinstance(data, list) and data:
                return data[0]
    except Exception:
        pass

    # 2) Fallback a GestiónReservas
    try:
        r_gr = get_reservas("/get_fake_reservations")
        if r_gr.status_code == 200:
            data = r_gr.json()
            if isinstance(data, list) and data:
                return data[0]
    except Exception:
        pass

    return None


def find_reservation_and_free_seat() -> tuple[dict, dict] | None:
    """
    Replica _find_reservation_and_free_seat de test_gestionreservas_edit_reservation_rag.py.

    Pasos:
      1) Obtener alguna reserva -> reservation.
      2) Usar Usuario para consultar asientos del mismo avión:
           GET /get_seats_by_airplane_id/<airplane_id>/seats
      3) Buscar un asiento con status == 'Libre', distinto al seat actual.
      4) Devuelve (reservation, seat_libre) o None.
    """
    reserva = find_any_reservation()
    if not reserva:
        return None

    airplane_id = reserva.get("airplane_id")
    current_seat = reserva.get("seat_number")
    if not airplane_id or not current_seat:
        return None

    try:
        r_seats = get_usuario(f"/get_seats_by_airplane_id/{airplane_id}/seats")
        if r_seats.status_code != 200:
            return None

        seats = r_seats.json()
        if not isinstance(seats, list):
            return None

        for s in seats:
            if (
                isinstance(s, dict)
                and s.get("status") == "Libre"
                and s.get("seat_number") != current_seat
            ):
                return reserva, s
    except Exception:
        return None

    return None


# ---------------------------------------------------------------------------
# Datos base y helper para bodies de PUT /reservations/<code>
# ---------------------------------------------------------------------------

BASE_CONTACT_DATA = {
    "email": "nuevo.contacto@example.com",
    "phone_number": "+50660000000",
    "emergency_contact_name": "Nuevo Contacto",
    "emergency_contact_phone": "+50661111111",
}


def build_edit_reservation_body(
    seat_number: str,
    email: str | None = None,
    phone_number: str | None = None,
    emergency_contact_name: str | None = None,
    emergency_contact_phone: str | None = None,
) -> dict:
    """
    Equivalente a _build_full_body de test_gestionreservas_edit_reservation_rag.py.

    Body válido completo para PUT /reservations/<reservation_code>:
      - seat_number
      - email
      - phone_number
      - emergency_contact_name
      - emergency_contact_phone
    """
    return {
        "seat_number": seat_number,
        "email": email or BASE_CONTACT_DATA["email"],
        "phone_number": phone_number or BASE_CONTACT_DATA["phone_number"],
        "emergency_contact_name": (
            emergency_contact_name or BASE_CONTACT_DATA["emergency_contact_name"]
        ),
        "emergency_contact_phone": (
            emergency_contact_phone or BASE_CONTACT_DATA["emergency_contact_phone"]
        ),
    }


# ---------------------------------------------------------------------------
# Helpers para pagos: reservas con/sin pago y pagos existentes
# ---------------------------------------------------------------------------

def find_reservation_without_payment() -> dict | None:
    """
    Replica _find_reservation_without_payment de test_gestionreservas_create_payment_rag.py.

    Estrategia:
      1) GET /get_fake_reservations (GestiónReservas) -> lista de reservas.
      2) GET /get_all_fake_payments (GestiónReservas) -> lista de pagos.
      3) Devolver la primera reserva cuyo reservation_id NO esté en pagos.
    """
    # 1) Reservas
    r_res = get_reservas("/get_fake_reservations")
    if r_res.status_code == 204:
        # No hay reservas generadas
        return None

    if r_res.status_code != 200:
        return None

    try:
        reservas = r_res.json()
    except Exception:
        return None

    if not isinstance(reservas, list) or not reservas:
        return None

    # 2) Pagos
    r_pay = get_reservas("/get_all_fake_payments")
    if r_pay.status_code != 200:
        # Si falla, devolvemos alguna reserva cualquiera
        return reservas[0]

    try:
        pagos = r_pay.json()
    except Exception:
        return reservas[0]

    reservation_ids_con_pago: set[int] = set()

    if isinstance(pagos, list):
        for p in pagos:
            if isinstance(p, dict) and "reservation_id" in p:
                reservation_ids_con_pago.add(p["reservation_id"])
    elif isinstance(pagos, dict):
        msg = str(pagos.get("message", "")).lower()
        if "no hay pagos" in msg:
            reservation_ids_con_pago = set()
        else:
            # Respuesta no esperada; devolvemos la primera reserva
            return reservas[0]

    # 3) Primera reserva SIN pago
    for r in reservas:
        rid = r.get("reservation_id")
        if isinstance(rid, int) and rid not in reservation_ids_con_pago:
            return r

    return None


def find_reservation_with_payment() -> int | None:
    """
    Replica _find_reservation_with_payment de test_gestionreservas_create_payment_rag.py.

    Devuelve un reservation_id que sí tenga pago asociado, o None.
    """
    r_pay = get_reservas("/get_all_fake_payments")
    if r_pay.status_code != 200:
        return None

    try:
        pagos = r_pay.json()
    except Exception:
        return None

    if not isinstance(pagos, list) or not pagos:
        return None

    first = pagos[0]
    if isinstance(first, dict):
        rid = first.get("reservation_id")
        if isinstance(rid, int):
            return rid

    return None


def find_existing_payment_with_full_data() -> dict | None:
    """
    Replica _find_existing_payment_with_full_data de
    test_gestionreservas_cancel_payment_and_reservation_rag.py.

    Devuelve un pago que tenga al menos:
      - payment_id con formato 'PAY' + 6 dígitos
      - reservation_id (int)
      - airplane_id no None
      - seat_number (str)
    o None si no encuentra.
    """
    try:
        r = get_reservas("/get_all_fake_payments")
    except Exception:
        return None

    if r.status_code != 200:
        return None

    try:
        data = r.json()
    except Exception:
        return None

    if not isinstance(data, list):
        return None

    for p in data:
        if not isinstance(p, dict):
            continue
        pid = p.get("payment_id")
        rid = p.get("reservation_id")
        aid = p.get("airplane_id")
        seat = p.get("seat_number")
        if (
            isinstance(pid, str)
            and re.match(r"^PAY\d{6}$", pid)
            and isinstance(rid, int)
            and aid is not None
            and isinstance(seat, str)
        ):
            return p

    return None
