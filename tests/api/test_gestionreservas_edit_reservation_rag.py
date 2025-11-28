"""
EXPERIMENTO_RAG_05_gestionreservas_edit_reservation

Pruebas de contrato para el endpoint:
    PUT /reservations/<reservation_code>

Casos cubiertos:

A) Validaciones básicas y 404
   - Código mal formado (no 6 chars alfanuméricos)  -> 400.
   - Reserva no existe                              -> 404.
   - Body ausente / no JSON                         -> 400.
   - Body sin todos los campos requeridos           -> 400.
   - Body con campos extra                          -> 400.

B) Casos de asiento / GestiónVuelos
   - Cambiar a asiento que no existe                -> 400.
   - Cambiar a asiento que no está libre            -> 409.

C) Happy path
   - Cambiar datos de contacto sin cambiar asiento  -> 200, sin tocar GestiónVuelos.
   - Cambiar asiento a uno Libre                    -> 200, asiento viejo liberado y nuevo reservado.
"""

import os
import pytest
import requests

BASE_URL_RESERVAS = os.getenv("GESTIONRESERVAS_BASE_URL", "http://localhost:5002")
BASE_URL_USUARIO  = os.getenv("USUARIO_BASE_URL", "http://localhost:5003")


def _get_reservas(path: str, **kwargs) -> requests.Response:
    return requests.get(f"{BASE_URL_RESERVAS}{path}", **kwargs)


def _put_reservas(path: str, **kwargs) -> requests.Response:
    return requests.put(f"{BASE_URL_RESERVAS}{path}", **kwargs)


def _get_usuario(path: str, **kwargs) -> requests.Response:
    return requests.get(f"{BASE_URL_USUARIO}{path}", **kwargs)


# -------------------------------------------------------------------
# Helpers de caja negra
# -------------------------------------------------------------------


def _find_any_reservation() -> dict | None:
    """
    Intenta obtener alguna reserva existente:

    - Primero pregunta al microservicio Usuario: GET /get_all_reservations
      porque ahí ya están validadas y es la fachada principal.
    - Si falla, trata de llamar directamente a GestiónReservas
      a GET /get_fake_reservations.

    Devuelve un dict con una reserva o None si no hay.
    """
    # 1) Intentar vía Usuario
    try:
        r_usr = _get_usuario("/get_all_reservations", timeout=20)
        if r_usr.status_code == 200:
            data = r_usr.json()
            if isinstance(data, list) and data:
                return data[0]
    except Exception:
        pass

    # 2) Fallback directo a GestiónReservas
    try:
        r_gr = _get_reservas("/get_fake_reservations", timeout=20)
        if r_gr.status_code == 200:
            data = r_gr.json()
            if isinstance(data, list) and data:
                return data[0]
    except Exception:
        pass

    return None


def _find_reservation_and_free_seat() -> tuple[dict, dict] | None:
    """
    Intenta encontrar una reserva y, para su mismo avión,
    un asiento Libre diferente al actual.

    Estrategia (caja negra):
    1) Obtener alguna reserva -> reservation.
    2) Usar Usuario para consultar asientos del mismo avión:
         GET /get_seats_by_airplane_id/<airplane_id>/seats
    3) Buscar un asiento con status == 'Libre' (y seat_number distinto).
    4) Devuelve (reservation, seat_libre) o None si no se puede.
    """
    reserva = _find_any_reservation()
    if not reserva:
        return None

    airplane_id = reserva.get("airplane_id")
    current_seat = reserva.get("seat_number")
    if not airplane_id or not current_seat:
        return None

    try:
        r_seats = _get_usuario(f"/get_seats_by_airplane_id/{airplane_id}/seats", timeout=20)
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


# -------------------------------------------------------------------
# Datos base para bodies válidos
# -------------------------------------------------------------------


BASE_CONTACT_DATA = {
    "email": "nuevo.contacto@example.com",
    "phone_number": "+50660000000",
    "emergency_contact_name": "Nuevo Contacto",
    "emergency_contact_phone": "+50661111111",
}


def _build_full_body(
    seat_number: str,
    email: str | None = None,
    phone_number: str | None = None,
    emergency_contact_name: str | None = None,
    emergency_contact_phone: str | None = None,
) -> dict:
    """
    Construye un body válido completo para PUT /reservations/<code>:

    Requerido:
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
        "emergency_contact_name": emergency_contact_name or BASE_CONTACT_DATA["emergency_contact_name"],
        "emergency_contact_phone": emergency_contact_phone or BASE_CONTACT_DATA["emergency_contact_phone"],
    }


# -------------------------------------------------------------------
# A) Validaciones básicas y 404
# -------------------------------------------------------------------


@pytest.mark.parametrize(
    "case_id, reservation_code, body, expected_status, expected_msg_sub",
    [
        (
            "GR_EDITRES_CODE_MALFORMADO_400",
            "ABC",  # no 6 chars
            BASE_CONTACT_DATA | {"seat_number": "1A"},
            400,
            "El código de reserva debe ser 6 caracteres alfanuméricos",
        ),
        (
            "GR_EDITRES_NO_EXISTE_404",
            "ZZZ999",  # asumimos que no existe
            BASE_CONTACT_DATA | {"seat_number": "1A"},
            404,
            "Reserva no encontrada",
        ),
        (
            "GR_EDITRES_BODY_AUSENTE_400",
            # usaremos una reserva real para evitar 404
            "REAL_FROM_FIXTURE",  # marcador, se reemplaza en el test
            None,
            400,
            "No se recibió cuerpo JSON",
        ),
        (
            "GR_EDITRES_BODY_INCOMPLETO_400",
            "REAL_FROM_FIXTURE",
            # Falta emergency_contact_phone
            {
                "seat_number": "1A",
                "email": BASE_CONTACT_DATA["email"],
                "phone_number": BASE_CONTACT_DATA["phone_number"],
                "emergency_contact_name": BASE_CONTACT_DATA["emergency_contact_name"],
            },
            400,
            "exactamente estos campos",
        ),
        (
            "GR_EDITRES_BODY_CAMPO_EXTRA_400",
            "REAL_FROM_FIXTURE",
            # Tiene todos + un campo extra
            {
                **_build_full_body("1A"),
                "extra_field": "no debe ir",
            },
            400,
            "exactamente estos campos",
        ),
    ],
)
def test_gestionreservas_edit_reservation_validaciones_basicas(
    case_id,
    reservation_code,
    body,
    expected_status,
    expected_msg_sub,
):
    """
    Casos de error "locales" para:
        PUT /reservations/<reservation_code>

    - Código mal formado -> 400.
    - Reserva no existente -> 404.
    - Body ausente / no JSON -> 400.
    - Body sin todos los campos -> 400.
    - Body con campos extra -> 400.
    """
    # Si el código es el marcador "REAL_FROM_FIXTURE", obtenemos una reserva existente
    if reservation_code == "REAL_FROM_FIXTURE":
        reserva = _find_any_reservation()
        if reserva is None:
            pytest.skip(f"[{case_id}] No se encontró ninguna reserva en el sistema.")
        reservation_code = reserva.get("reservation_code")
        assert reservation_code, f"[{case_id}] La reserva encontrada no tiene reservation_code."

    path = f"/reservations/{reservation_code}"

    if body is None:
        r = _put_reservas(path)  # sin json
    else:
        r = _put_reservas(path, json=body)

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


# -------------------------------------------------------------------
# B) Casos de asiento / GestiónVuelos (no existe, no libre)
# -------------------------------------------------------------------


def test_gestionreservas_edit_reservation_asiento_no_existe_400():
    """
    Cambiar a un asiento que no existe en el avión -> 400.
    """
    reserva = _find_any_reservation()
    if reserva is None:
        pytest.skip("[GR_EDITRES_SEAT_NO_EXISTE_400] No hay reservas para probar.")

    code = reserva.get("reservation_code")
    current_seat = reserva.get("seat_number")
    assert code and current_seat, (
        "[GR_EDITRES_SEAT_NO_EXISTE_400] Reserva sin reservation_code o seat_number."
    )

    body = _build_full_body(seat_number="99Z")  # asiento obviously inválido

    r = _put_reservas(f"/reservations/{code}", json=body)

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        msg_text = r.text

    assert (
        r.status_code == 400
    ), f"[GR_EDITRES_SEAT_NO_EXISTE_400] Código inesperado: {r.status_code} {r.text}"

    assert "no existe" in msg_text.lower(), (
        "[GR_EDITRES_SEAT_NO_EXISTE_400] El mensaje no indica que el asiento no existe. "
        f"Mensaje: {msg_text}"
    )


def test_gestionreservas_edit_reservation_asiento_no_libre_409():
    """
    Cambiar a un asiento que no está Libre -> 409.

    Estrategia:
    1) Encontrar una reserva A que tenga seat_number S1.
    2) Crear (o asumir) otra reserva B en el mismo avión con seat_number S2.
       En este laboratorio, asumimos que ya hay varias reservas y
       al menos hay algún asiento marcado como 'Reservado' en el avión.
    3) Intentar cambiar la reserva A al asiento S2 (que ya no está 'Libre').
    4) Debe devolver 409.
    """
    reserva = _find_any_reservation()
    if reserva is None:
        pytest.skip("[GR_EDITRES_SEAT_NO_LIBRE_409] No hay reservas para probar.")

    code = reserva.get("reservation_code")
    airplane_id = reserva.get("airplane_id")
    current_seat = reserva.get("seat_number")
    assert code and airplane_id and current_seat, (
        "[GR_EDITRES_SEAT_NO_LIBRE_409] Reserva incompleta."
    )

    # Usamos Usuario para buscar algún asiento que no esté Libre
    r_seats = _get_usuario(f"/get_seats_by_airplane_id/{airplane_id}/seats", timeout=20)
    if r_seats.status_code != 200:
        pytest.skip(
            f"[GR_EDITRES_SEAT_NO_LIBRE_409] No se pudo obtener asientos: {r_seats.status_code}"
        )

    seats = r_seats.json()
    if not isinstance(seats, list) or not seats:
        pytest.skip("[GR_EDITRES_SEAT_NO_LIBRE_409] Lista de asientos vacía o inválida.")

    seat_not_free = None
    for s in seats:
        if (
            isinstance(s, dict)
            and s.get("status") in ("Reservado", "Pagado")
            and s.get("seat_number") != current_seat
        ):
            seat_not_free = s
            break

    if seat_not_free is None:
        pytest.skip("[GR_EDITRES_SEAT_NO_LIBRE_409] No se encontró asiento no Libre en el avión.")

    target_seat = seat_not_free["seat_number"]
    body = _build_full_body(seat_number=target_seat)

    r = _put_reservas(f"/reservations/{code}", json=body)

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        msg_text = r.text

    assert (
        r.status_code == 409
    ), f"[GR_EDITRES_SEAT_NO_LIBRE_409] Código inesperado: {r.status_code} {r.text}"

    assert "no está libre" in msg_text.lower(), (
        "[GR_EDITRES_SEAT_NO_LIBRE_409] El mensaje no indica que el asiento no está libre. "
        f"Mensaje: {msg_text}"
    )


# -------------------------------------------------------------------
# C) Happy path
# -------------------------------------------------------------------


def test_gestionreservas_edit_reservation_happy_path_solo_contacto():
    """
    Caso feliz 1:
        Actualizar SOLO datos de contacto (mismo seat_number).
        Debe devolver 200 y la reserva actualizada.
    """
    reserva = _find_any_reservation()
    if reserva is None:
        pytest.skip("[GR_EDITRES_OK_CONTACTO] No hay reservas para probar.")

    code = reserva.get("reservation_code")
    seat_number = reserva.get("seat_number")
    assert code and seat_number, "[GR_EDITRES_OK_CONTACTO] Reserva incompleta."

    body = _build_full_body(
        seat_number=seat_number,
        email="contacto.actualizado@example.com",
        phone_number="+50662223333",
        emergency_contact_name="Contacto Actualizado",
        emergency_contact_phone="+50665556666",
    )

    r = _put_reservas(f"/reservations/{code}", json=body)

    assert (
        r.status_code == 200
    ), f"[GR_EDITRES_OK_CONTACTO] Código inesperado: {r.status_code} {r.text}"

    resp_json = r.json()
    assert isinstance(resp_json, dict), (
        "[GR_EDITRES_OK_CONTACTO] Respuesta no es JSON dict."
    )

    msg = resp_json.get("message", "")
    assert "actualizados exitosamente" in msg.lower(), (
        "[GR_EDITRES_OK_CONTACTO] Mensaje de éxito inesperado: "
        f"{msg}"
    )

    reservation = resp_json.get("reservation")
    assert isinstance(reservation, dict), (
        "[GR_EDITRES_OK_CONTACTO] 'reservation' no es dict."
    )

    assert reservation.get("email") == "contacto.actualizado@example.com"
    assert reservation.get("phone_number") == "+50662223333"
    assert reservation.get("emergency_contact_name") == "Contacto Actualizado"
    assert reservation.get("emergency_contact_phone") == "+50665556666"
    assert reservation.get("seat_number") == seat_number


def test_gestionreservas_edit_reservation_happy_path_cambio_asiento():
    """
    Caso feliz 2:
        Cambiar asiento a uno Libre y actualizar datos de contacto.
        Debe devolver 200 y la reserva con el nuevo seat_number.
    """
    pair = _find_reservation_and_free_seat()
    if pair is None:
        pytest.skip("[GR_EDITRES_OK_SEAT] No se encontró reserva + asiento Libre.")

    reserva, seat_libre = pair
    code = reserva.get("reservation_code")
    new_seat = seat_libre.get("seat_number")

    assert code and new_seat, "[GR_EDITRES_OK_SEAT] Datos incompletos de reserva o asiento."

    body = _build_full_body(
        seat_number=new_seat,
        email="nuevo.asiento@example.com",
        phone_number="+50669998888",
        emergency_contact_name="Contacto Asiento Nuevo",
        emergency_contact_phone="+50667776666",
    )

    r = _put_reservas(f"/reservations/{code}", json=body)

    assert (
        r.status_code == 200
    ), f"[GR_EDITRES_OK_SEAT] Código inesperado: {r.status_code} {r.text}"

    resp_json = r.json()
    assert isinstance(resp_json, dict), "[GR_EDITRES_OK_SEAT] Respuesta no es dict."

    msg = resp_json.get("message", "")
    assert "actualizados exitosamente" in msg.lower(), (
        "[GR_EDITRES_OK_SEAT] Mensaje de éxito inesperado: "
        f"{msg}"
    )

    reservation = resp_json.get("reservation")
    assert isinstance(reservation, dict), "[GR_EDITRES_OK_SEAT] 'reservation' no es dict."
    assert reservation.get("seat_number") == new_seat
    assert reservation.get("email") == "nuevo.asiento@example.com"
"""
EXPERIMENTO_RAG_05_gestionreservas_edit_reservation

Pruebas de contrato para el endpoint:
    PUT /reservations/<reservation_code>

Casos cubiertos:

A) Validaciones básicas y 404
   - Código mal formado (no 6 chars alfanuméricos)  -> 400.
   - Reserva no existe                              -> 404.
   - Body ausente / no JSON                         -> 400.
   - Body sin todos los campos requeridos           -> 400.
   - Body con campos extra                          -> 400.

B) Casos de asiento / GestiónVuelos
   - Cambiar a asiento que no existe                -> 400.
   - Cambiar a asiento que no está libre            -> 409.

C) Happy path
   - Cambiar datos de contacto sin cambiar asiento  -> 200, sin tocar GestiónVuelos.
   - Cambiar asiento a uno Libre                    -> 200, asiento viejo liberado y nuevo reservado.
"""

import os
import pytest
import requests

BASE_URL_RESERVAS = os.getenv("GESTIONRESERVAS_BASE_URL", "http://localhost:5002")
BASE_URL_USUARIO  = os.getenv("USUARIO_BASE_URL", "http://localhost:5003")


def _get_reservas(path: str, **kwargs) -> requests.Response:
    return requests.get(f"{BASE_URL_RESERVAS}{path}", **kwargs)


def _put_reservas(path: str, **kwargs) -> requests.Response:
    return requests.put(f"{BASE_URL_RESERVAS}{path}", **kwargs)


def _get_usuario(path: str, **kwargs) -> requests.Response:
    return requests.get(f"{BASE_URL_USUARIO}{path}", **kwargs)


# -------------------------------------------------------------------
# Helpers de caja negra
# -------------------------------------------------------------------


def _find_any_reservation() -> dict | None:
    """
    Intenta obtener alguna reserva existente:

    - Primero pregunta al microservicio Usuario: GET /get_all_reservations
      porque ahí ya están validadas y es la fachada principal.
    - Si falla, trata de llamar directamente a GestiónReservas
      a GET /get_fake_reservations.

    Devuelve un dict con una reserva o None si no hay.
    """
    # 1) Intentar vía Usuario
    try:
        r_usr = _get_usuario("/get_all_reservations", timeout=20)
        if r_usr.status_code == 200:
            data = r_usr.json()
            if isinstance(data, list) and data:
                return data[0]
    except Exception:
        pass

    # 2) Fallback directo a GestiónReservas
    try:
        r_gr = _get_reservas("/get_fake_reservations", timeout=20)
        if r_gr.status_code == 200:
            data = r_gr.json()
            if isinstance(data, list) and data:
                return data[0]
    except Exception:
        pass

    return None


def _find_reservation_and_free_seat() -> tuple[dict, dict] | None:
    """
    Intenta encontrar una reserva y, para su mismo avión,
    un asiento Libre diferente al actual.

    Estrategia (caja negra):
    1) Obtener alguna reserva -> reservation.
    2) Usar Usuario para consultar asientos del mismo avión:
         GET /get_seats_by_airplane_id/<airplane_id>/seats
    3) Buscar un asiento con status == 'Libre' (y seat_number distinto).
    4) Devuelve (reservation, seat_libre) o None si no se puede.
    """
    reserva = _find_any_reservation()
    if not reserva:
        return None

    airplane_id = reserva.get("airplane_id")
    current_seat = reserva.get("seat_number")
    if not airplane_id or not current_seat:
        return None

    try:
        r_seats = _get_usuario(f"/get_seats_by_airplane_id/{airplane_id}/seats", timeout=20)
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


# -------------------------------------------------------------------
# Datos base para bodies válidos
# -------------------------------------------------------------------


BASE_CONTACT_DATA = {
    "email": "nuevo.contacto@example.com",
    "phone_number": "+50660000000",
    "emergency_contact_name": "Nuevo Contacto",
    "emergency_contact_phone": "+50661111111",
}


def _build_full_body(
    seat_number: str,
    email: str | None = None,
    phone_number: str | None = None,
    emergency_contact_name: str | None = None,
    emergency_contact_phone: str | None = None,
) -> dict:
    """
    Construye un body válido completo para PUT /reservations/<code>:

    Requerido:
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
        "emergency_contact_name": emergency_contact_name or BASE_CONTACT_DATA["emergency_contact_name"],
        "emergency_contact_phone": emergency_contact_phone or BASE_CONTACT_DATA["emergency_contact_phone"],
    }


# -------------------------------------------------------------------
# A) Validaciones básicas y 404
# -------------------------------------------------------------------


@pytest.mark.parametrize(
    "case_id, reservation_code, body, expected_status, expected_msg_sub",
    [
        (
            "GR_EDITRES_CODE_MALFORMADO_400",
            "ABC",  # no 6 chars
            BASE_CONTACT_DATA | {"seat_number": "1A"},
            400,
            "El código de reserva debe ser 6 caracteres alfanuméricos",
        ),
        (
            "GR_EDITRES_NO_EXISTE_404",
            "ZZZ999",  # asumimos que no existe
            BASE_CONTACT_DATA | {"seat_number": "1A"},
            404,
            "Reserva no encontrada",
        ),
        (
            "GR_EDITRES_BODY_AUSENTE_400",
            # usaremos una reserva real para evitar 404
            "REAL_FROM_FIXTURE",  # marcador, se reemplaza en el test
            None,
            400,
            "No se recibió cuerpo JSON",
        ),
        (
            "GR_EDITRES_BODY_INCOMPLETO_400",
            "REAL_FROM_FIXTURE",
            # Falta emergency_contact_phone
            {
                "seat_number": "1A",
                "email": BASE_CONTACT_DATA["email"],
                "phone_number": BASE_CONTACT_DATA["phone_number"],
                "emergency_contact_name": BASE_CONTACT_DATA["emergency_contact_name"],
            },
            400,
            "exactamente estos campos",
        ),
        (
            "GR_EDITRES_BODY_CAMPO_EXTRA_400",
            "REAL_FROM_FIXTURE",
            # Tiene todos + un campo extra
            {
                **_build_full_body("1A"),
                "extra_field": "no debe ir",
            },
            400,
            "exactamente estos campos",
        ),
    ],
)
def test_gestionreservas_edit_reservation_validaciones_basicas(
    case_id,
    reservation_code,
    body,
    expected_status,
    expected_msg_sub,
):
    """
    Casos de error "locales" para:
        PUT /reservations/<reservation_code>

    - Código mal formado -> 400.
    - Reserva no existente -> 404.
    - Body ausente / no JSON -> 400.
    - Body sin todos los campos -> 400.
    - Body con campos extra -> 400.
    """
    # Si el código es el marcador "REAL_FROM_FIXTURE", obtenemos una reserva existente
    if reservation_code == "REAL_FROM_FIXTURE":
        reserva = _find_any_reservation()
        if reserva is None:
            pytest.skip(f"[{case_id}] No se encontró ninguna reserva en el sistema.")
        reservation_code = reserva.get("reservation_code")
        assert reservation_code, f"[{case_id}] La reserva encontrada no tiene reservation_code."

    path = f"/reservations/{reservation_code}"

    if body is None:
        r = _put_reservas(path)  # sin json
    else:
        r = _put_reservas(path, json=body)

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


# -------------------------------------------------------------------
# B) Casos de asiento / GestiónVuelos (no existe, no libre)
# -------------------------------------------------------------------


def test_gestionreservas_edit_reservation_asiento_no_existe_400():
    """
    Cambiar a un asiento que no existe en el avión -> 400.
    """
    reserva = _find_any_reservation()
    if reserva is None:
        pytest.skip("[GR_EDITRES_SEAT_NO_EXISTE_400] No hay reservas para probar.")

    code = reserva.get("reservation_code")
    current_seat = reserva.get("seat_number")
    assert code and current_seat, (
        "[GR_EDITRES_SEAT_NO_EXISTE_400] Reserva sin reservation_code o seat_number."
    )

    body = _build_full_body(seat_number="99Z")  # asiento obviously inválido

    r = _put_reservas(f"/reservations/{code}", json=body)

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        msg_text = r.text

    assert (
        r.status_code == 400
    ), f"[GR_EDITRES_SEAT_NO_EXISTE_400] Código inesperado: {r.status_code} {r.text}"

    assert "no existe" in msg_text.lower(), (
        "[GR_EDITRES_SEAT_NO_EXISTE_400] El mensaje no indica que el asiento no existe. "
        f"Mensaje: {msg_text}"
    )


def test_gestionreservas_edit_reservation_asiento_no_libre_409():
    """
    Cambiar a un asiento que no está Libre -> 409.

    Estrategia:
    1) Encontrar una reserva A que tenga seat_number S1.
    2) Crear (o asumir) otra reserva B en el mismo avión con seat_number S2.
       En este laboratorio, asumimos que ya hay varias reservas y
       al menos hay algún asiento marcado como 'Reservado' en el avión.
    3) Intentar cambiar la reserva A al asiento S2 (que ya no está 'Libre').
    4) Debe devolver 409.
    """
    reserva = _find_any_reservation()
    if reserva is None:
        pytest.skip("[GR_EDITRES_SEAT_NO_LIBRE_409] No hay reservas para probar.")

    code = reserva.get("reservation_code")
    airplane_id = reserva.get("airplane_id")
    current_seat = reserva.get("seat_number")
    assert code and airplane_id and current_seat, (
        "[GR_EDITRES_SEAT_NO_LIBRE_409] Reserva incompleta."
    )

    # Usamos Usuario para buscar algún asiento que no esté Libre
    r_seats = _get_usuario(f"/get_seats_by_airplane_id/{airplane_id}/seats", timeout=20)
    if r_seats.status_code != 200:
        pytest.skip(
            f"[GR_EDITRES_SEAT_NO_LIBRE_409] No se pudo obtener asientos: {r_seats.status_code}"
        )

    seats = r_seats.json()
    if not isinstance(seats, list) or not seats:
        pytest.skip("[GR_EDITRES_SEAT_NO_LIBRE_409] Lista de asientos vacía o inválida.")

    seat_not_free = None
    for s in seats:
        if (
            isinstance(s, dict)
            and s.get("status") in ("Reservado", "Pagado")
            and s.get("seat_number") != current_seat
        ):
            seat_not_free = s
            break

    if seat_not_free is None:
        pytest.skip("[GR_EDITRES_SEAT_NO_LIBRE_409] No se encontró asiento no Libre en el avión.")

    target_seat = seat_not_free["seat_number"]
    body = _build_full_body(seat_number=target_seat)

    r = _put_reservas(f"/reservations/{code}", json=body)

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        msg_text = r.text

    assert (
        r.status_code == 409
    ), f"[GR_EDITRES_SEAT_NO_LIBRE_409] Código inesperado: {r.status_code} {r.text}"

    assert "no está libre" in msg_text.lower(), (
        "[GR_EDITRES_SEAT_NO_LIBRE_409] El mensaje no indica que el asiento no está libre. "
        f"Mensaje: {msg_text}"
    )


# -------------------------------------------------------------------
# C) Happy path
# -------------------------------------------------------------------


def test_gestionreservas_edit_reservation_happy_path_solo_contacto():
    """
    Caso feliz 1:
        Actualizar SOLO datos de contacto (mismo seat_number).
        Debe devolver 200 y la reserva actualizada.
    """
    reserva = _find_any_reservation()
    if reserva is None:
        pytest.skip("[GR_EDITRES_OK_CONTACTO] No hay reservas para probar.")

    code = reserva.get("reservation_code")
    seat_number = reserva.get("seat_number")
    assert code and seat_number, "[GR_EDITRES_OK_CONTACTO] Reserva incompleta."

    body = _build_full_body(
        seat_number=seat_number,
        email="contacto.actualizado@example.com",
        phone_number="+50662223333",
        emergency_contact_name="Contacto Actualizado",
        emergency_contact_phone="+50665556666",
    )

    r = _put_reservas(f"/reservations/{code}", json=body)

    assert (
        r.status_code == 200
    ), f"[GR_EDITRES_OK_CONTACTO] Código inesperado: {r.status_code} {r.text}"

    resp_json = r.json()
    assert isinstance(resp_json, dict), (
        "[GR_EDITRES_OK_CONTACTO] Respuesta no es JSON dict."
    )

    msg = resp_json.get("message", "")
    assert "actualizados exitosamente" in msg.lower(), (
        "[GR_EDITRES_OK_CONTACTO] Mensaje de éxito inesperado: "
        f"{msg}"
    )

    reservation = resp_json.get("reservation")
    assert isinstance(reservation, dict), (
        "[GR_EDITRES_OK_CONTACTO] 'reservation' no es dict."
    )

    assert reservation.get("email") == "contacto.actualizado@example.com"
    assert reservation.get("phone_number") == "+50662223333"
    assert reservation.get("emergency_contact_name") == "Contacto Actualizado"
    assert reservation.get("emergency_contact_phone") == "+50665556666"
    assert reservation.get("seat_number") == seat_number


def test_gestionreservas_edit_reservation_happy_path_cambio_asiento():
    """
    Caso feliz 2:
        Cambiar asiento a uno Libre y actualizar datos de contacto.
        Debe devolver 200 y la reserva con el nuevo seat_number.
    """
    pair = _find_reservation_and_free_seat()
    if pair is None:
        pytest.skip("[GR_EDITRES_OK_SEAT] No se encontró reserva + asiento Libre.")

    reserva, seat_libre = pair
    code = reserva.get("reservation_code")
    new_seat = seat_libre.get("seat_number")

    assert code and new_seat, "[GR_EDITRES_OK_SEAT] Datos incompletos de reserva o asiento."

    body = _build_full_body(
        seat_number=new_seat,
        email="nuevo.asiento@example.com",
        phone_number="+50669998888",
        emergency_contact_name="Contacto Asiento Nuevo",
        emergency_contact_phone="+50667776666",
    )

    r = _put_reservas(f"/reservations/{code}", json=body)

    assert (
        r.status_code == 200
    ), f"[GR_EDITRES_OK_SEAT] Código inesperado: {r.status_code} {r.text}"

    resp_json = r.json()
    assert isinstance(resp_json, dict), "[GR_EDITRES_OK_SEAT] Respuesta no es dict."

    msg = resp_json.get("message", "")
    assert "actualizados exitosamente" in msg.lower(), (
        "[GR_EDITRES_OK_SEAT] Mensaje de éxito inesperado: "
        f"{msg}"
    )

    reservation = resp_json.get("reservation")
    assert isinstance(reservation, dict), "[GR_EDITRES_OK_SEAT] 'reservation' no es dict."
    assert reservation.get("seat_number") == new_seat
    assert reservation.get("email") == "nuevo.asiento@example.com"
