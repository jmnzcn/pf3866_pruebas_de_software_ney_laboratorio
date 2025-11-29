"""
EXPERIMENTO_RAG_05_gestionreservas_edit_reservation

Pruebas de contrato para el endpoint:
    PUT /reservations/<reservation_code>
"""

import pytest

from gestionreservas_common import (
    put_reservas,
    get_usuario,
    BASE_CONTACT_DATA,
    build_edit_reservation_body,
    find_any_reservation,
    find_reservation_and_free_seat,
)


@pytest.mark.parametrize(
    "case_id, reservation_code, body, expected_status, expected_msg_sub",
    [
        (
            "GR_EDITRES_CODE_MALFORMADO_400",
            "ABC",
            BASE_CONTACT_DATA | {"seat_number": "1A"},
            400,
            "El código de reserva debe ser 6 caracteres alfanuméricos",
        ),
        (
            "GR_EDITRES_NO_EXISTE_404",
            "ZZZ999",
            BASE_CONTACT_DATA | {"seat_number": "1A"},
            404,
            "Reserva no encontrada",
        ),
        (
            "GR_EDITRES_BODY_AUSENTE_400",
            "REAL_FROM_FIXTURE",
            None,
            400,
            "No se recibió cuerpo JSON",
        ),
        (
            "GR_EDITRES_BODY_INCOMPLETO_400",
            "REAL_FROM_FIXTURE",
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
            {
                **build_edit_reservation_body("1A"),
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
    """
    if reservation_code == "REAL_FROM_FIXTURE":
        reserva = find_any_reservation()
        if reserva is None:
            pytest.skip(f"[{case_id}] No se encontró ninguna reserva en el sistema.")
        reservation_code = reserva.get("reservation_code")
        assert reservation_code, (
            f"[{case_id}] La reserva encontrada no tiene reservation_code."
        )

    path = f"/reservations/{reservation_code}"

    if body is None:
        r = put_reservas(path)
    else:
        r = put_reservas(path, json=body)

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


def test_gestionreservas_edit_reservation_asiento_no_existe_400():
    """
    Cambiar a un asiento que no existe en el avión -> 400.
    """
    reserva = find_any_reservation()
    if reserva is None:
        pytest.skip("[GR_EDITRES_SEAT_NO_EXISTE_400] No hay reservas para probar.")

    code = reserva.get("reservation_code")
    current_seat = reserva.get("seat_number")
    assert code and current_seat, (
        "[GR_EDITRES_SEAT_NO_EXISTE_400] Reserva sin reservation_code o seat_number."
    )

    body = build_edit_reservation_body(seat_number="99Z")

    r = put_reservas(f"/reservations/{code}", json=body)

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
    """
    reserva = find_any_reservation()
    if reserva is None:
        pytest.skip("[GR_EDITRES_SEAT_NO_LIBRE_409] No hay reservas para probar.")

    code = reserva.get("reservation_code")
    airplane_id = reserva.get("airplane_id")
    current_seat = reserva.get("seat_number")
    assert code and airplane_id and current_seat, (
        "[GR_EDITRES_SEAT_NO_LIBRE_409] Reserva incompleta."
    )

    r_seats = get_usuario(f"/get_seats_by_airplane_id/{airplane_id}/seats")
    if r_seats.status_code != 200:
        pytest.skip(
            "[GR_EDITRES_SEAT_NO_LIBRE_409] No se pudo obtener asientos: "
            f"{r_seats.status_code}"
        )

    seats = r_seats.json()
    if not isinstance(seats, list) or not seats:
        pytest.skip(
            "[GR_EDITRES_SEAT_NO_LIBRE_409] Lista de asientos vacía o inválida."
        )

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
        pytest.skip(
            "[GR_EDITRES_SEAT_NO_LIBRE_409] No se encontró asiento no Libre en el avión."
        )

    target_seat = seat_not_free["seat_number"]
    body = build_edit_reservation_body(seat_number=target_seat)

    r = put_reservas(f"/reservations/{code}", json=body)

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


def test_gestionreservas_edit_reservation_happy_path_solo_contacto():
    """
    Caso feliz 1:
        Actualizar SOLO datos de contacto (mismo seat_number).
    """
    reserva = find_any_reservation()
    if reserva is None:
        pytest.skip("[GR_EDITRES_OK_CONTACTO] No hay reservas para probar.")

    code = reserva.get("reservation_code")
    seat_number = reserva.get("seat_number")
    assert code and seat_number, "[GR_EDITRES_OK_CONTACTO] Reserva incompleta."

    body = build_edit_reservation_body(
        seat_number=seat_number,
        email="contacto.actualizado@example.com",
        phone_number="+50662223333",
        emergency_contact_name="Contacto Actualizado",
        emergency_contact_phone="+50665556666",
    )

    r = put_reservas(f"/reservations/{code}", json=body)

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
    """
    pair = find_reservation_and_free_seat()
    if pair is None:
        pytest.skip("[GR_EDITRES_OK_SEAT] No se encontró reserva + asiento Libre.")

    reserva, seat_libre = pair
    code = reserva.get("reservation_code")
    new_seat = seat_libre.get("seat_number")

    assert code and new_seat, (
        "[GR_EDITRES_OK_SEAT] Datos incompletos de reserva o asiento."
    )

    body = build_edit_reservation_body(
        seat_number=new_seat,
        email="nuevo.asiento@example.com",
        phone_number="+50669998888",
        emergency_contact_name="Contacto Asiento Nuevo",
        emergency_contact_phone="+50667776666",
    )

    r = put_reservas(f"/reservations/{code}", json=body)

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
