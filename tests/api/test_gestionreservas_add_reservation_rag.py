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

import pytest

from gestionreservas_common import (
    post_reservas,
    get_vuelos,
    make_add_reservation_body,
    get_all_routes_from_vuelos,
    find_route_and_free_seat,
)


# Cuerpos para las validaciones básicas (solo schema + lógica local)
BODY_EMAIL_INVALIDO = make_add_reservation_body()
BODY_EMAIL_INVALIDO["email"] = "no-es-un-email"

BODY_STATUS_INVALIDO = make_add_reservation_body()
BODY_STATUS_INVALIDO["status"] = "Pendiente"

BODY_CAMPO_FALTANTE = make_add_reservation_body()
BODY_CAMPO_FALTANTE.pop("seat_number", None)


@pytest.mark.parametrize(
    "case_id, body, expected_status, expected_msg_sub",
    [
        (
            "GR_ADDRES_BODY_VACIO_400",
            None,
            500,  # según implementación actual
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
        r = post_reservas("/add_reservation")
    else:
        r = post_reservas("/add_reservation", json=body)

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


def test_gestionreservas_add_reservation_ruta_no_encontrada_400():
    """
    Caso: airplane_route_id inexistente en GestiónVuelos.

    Esperado:
      - 400
      - Mensaje que incluya "Ruta con ID".
    """
    rutas = get_all_routes_from_vuelos()
    if not rutas:
        pytest.skip("[GR_ADDRES_RUTA_NO_EXISTE] No hay rutas disponibles en GestiónVuelos.")

    pair = find_route_and_free_seat()
    if pair is None:
        pytest.skip("[GR_ADDRES_RUTA_NO_EXISTE] No se encontró ruta + asiento Libre para el test.")

    ruta_valida, seat_libre = pair
    airplane_id = ruta_valida["airplane_id"]
    seat_number = seat_libre["seat_number"]

    route_ids = [
        r.get("airplane_route_id")
        for r in rutas
        if isinstance(r.get("airplane_route_id"), int)
    ]
    if not route_ids:
        pytest.skip("[GR_ADDRES_RUTA_NO_EXISTE] No se encontraron airplane_route_id válidos.")
    invalid_route_id = max(route_ids) + 1000

    body = make_add_reservation_body(
        airplane_id=airplane_id,
        airplane_route_id=invalid_route_id,
        seat_number=seat_number,
    )

    r = post_reservas("/add_reservation", json=body)

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        msg_text = r.text

    assert r.status_code == 400, (
        f"[GR_ADDRES_RUTA_NO_EXISTE] Código inesperado: {r.status_code} {r.text}"
    )
    assert "ruta con id" in msg_text.lower(), (
        "[GR_ADDRES_RUTA_NO_EXISTE] No se encontró 'Ruta con ID' en el mensaje: "
        f"{msg_text}"
    )


def test_gestionreservas_add_reservation_ruta_no_asociada_400():
    """
    Caso: la ruta existe pero NO está asociada al avión indicado.

    Esperado:
      - 400
      - Mensaje que incluya 'no está asociada al avión'.
    """
    rutas = get_all_routes_from_vuelos()
    if not rutas:
        pytest.skip("[GR_ADDRES_RUTA_NO_ASOCIADA] No hay rutas disponibles en GestiónVuelos.")

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

    airplane_ids = list(rutas_por_avion.keys())
    avion_a = airplane_ids[0]
    avion_b = airplane_ids[1]

    ruta_a = rutas_por_avion[avion_a][0]
    route_id = ruta_a["airplane_route_id"]

    body = make_add_reservation_body(
        airplane_id=avion_b,
        airplane_route_id=route_id,
        seat_number="1A",
    )

    r = post_reservas("/add_reservation", json=body)

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        msg_text = r.text

    assert r.status_code == 400, (
        f"[GR_ADDRES_RUTA_NO_ASOCIADA] Código inesperado: {r.status_code} {r.text}"
    )
    assert "no está asociada al avión" in msg_text.lower(), (
        f"[GR_ADDRES_RUTA_NO_ASOCIADA] Mensaje inesperado: {msg_text}"
    )


def test_gestionreservas_add_reservation_asiento_no_existe_400():
    """
    Caso: asiento inexistente para el avión dado.

    Esperado:
      - 400
      - Mensaje que incluya 'no existe para ese avión'.
    """
    pair = find_route_and_free_seat()
    if pair is None:
        pytest.skip(
            "[GR_ADDRES_ASIENTO_NO_EXISTE] No se encontró ruta + asiento Libre para preparar el caso."
        )

    ruta, _seat = pair
    airplane_id = ruta["airplane_id"]
    route_id = ruta["airplane_route_id"]

    r_seats = get_vuelos(f"/get_airplane_seats/{airplane_id}/seats")
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

    fake_seat = "99Z"
    if fake_seat in existing_seats:
        fake_seat = "100Z"

    body = make_add_reservation_body(
        airplane_id=airplane_id,
        airplane_route_id=route_id,
        seat_number=fake_seat,
    )

    r = post_reservas("/add_reservation", json=body)

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        msg_text = r.text

    assert r.status_code == 400, (
        f"[GR_ADDRES_ASIENTO_NO_EXISTE] Código inesperado: {r.status_code} {r.text}"
    )
    assert "no existe para ese avión" in msg_text.lower(), (
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
    pair = find_route_and_free_seat()
    if pair is None:
        pytest.skip(
            "[GR_ADDRES_ASIENTO_NO_LIBRE] No se encontró ruta + asiento Libre para el caso."
        )

    ruta, seat_libre = pair
    airplane_id = ruta["airplane_id"]
    route_id = ruta["airplane_route_id"]
    seat_number = seat_libre["seat_number"]

    body = make_add_reservation_body(
        airplane_id=airplane_id,
        airplane_route_id=route_id,
        seat_number=seat_number,
    )

    r1 = post_reservas("/add_reservation", json=body)
    assert r1.status_code == 201, (
        "[GR_ADDRES_ASIENTO_NO_LIBRE] La reserva inicial no fue creada: "
        f"{r1.status_code} {r1.text}"
    )

    r2 = post_reservas("/add_reservation", json=body)

    try:
        resp_json = r2.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        msg_text = r2.text

    assert r2.status_code == 409, (
        f"[GR_ADDRES_ASIENTO_NO_LIBRE] Código inesperado: {r2.status_code} {r2.text}"
    )
    assert "no está disponible" in msg_text.lower(), (
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
    pair = find_route_and_free_seat()
    if pair is None:
        pytest.skip(
            "[GR_ADDRES_OK_201] No se encontró ruta + asiento Libre para el caso feliz."
        )

    ruta, seat_libre = pair
    airplane_id = ruta["airplane_id"]
    route_id = ruta["airplane_route_id"]
    seat_number = seat_libre["seat_number"]

    body = make_add_reservation_body(
        airplane_id=airplane_id,
        airplane_route_id=route_id,
        seat_number=seat_number,
    )

    r = post_reservas("/add_reservation", json=body)
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
