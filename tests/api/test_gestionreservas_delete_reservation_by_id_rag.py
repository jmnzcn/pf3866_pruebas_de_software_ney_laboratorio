"""
EXPERIMENTO_RAG_04_gestionreservas_delete_reservation_by_id

Pruebas de contrato para el endpoint de GestiónReservas:
    DELETE /delete_reservation_by_id/<int:reservation_id>
"""

import pytest

from gestionreservas_common import (
    delete_reservas,
    get_vuelos,
    find_any_reservation,
)


@pytest.mark.parametrize(
    "case_id, path, expected_status, expected_msg_sub",
    [
        (
            "GR_DELRES_ID_CERO_400",
            "/delete_reservation_by_id/0",
            400,
            "El ID de reserva debe ser un número positivo",
        ),
        (
            "GR_DELRES_NO_EXISTE_404",
            "/delete_reservation_by_id/999999",
            404,
            "Reserva no encontrada",
        ),
    ],
)
def test_gestionreservas_delete_reservation_by_id_validaciones_y_404(
    case_id,
    path,
    expected_status,
    expected_msg_sub,
):
    """
    Casos de error para:
        DELETE /delete_reservation_by_id/<int:reservation_id>
    """
    r = delete_reservas(path)

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


def test_gestionreservas_delete_reservation_by_id_happy_path():
    """
    Caso feliz:
        Eliminar una reserva existente y verificar que el asiento en GestiónVuelos
        queda marcado como Libre.
    """
    reserva = find_any_reservation()
    if reserva is None:
        pytest.skip(
            "[GR_DELRES_OK_200_LIBERA_ASIENTO] No hay reservas disponibles "
            "para probar."
        )

    reservation_id = reserva.get("reservation_id")
    airplane_id = reserva.get("airplane_id")
    seat_number = reserva.get("seat_number")

    assert isinstance(reservation_id, int) and reservation_id > 0, (
        "[GR_DELRES_OK_200_LIBERA_ASIENTO] La reserva no tiene 'reservation_id' entero positivo: "
        f"{reserva}"
    )
    assert airplane_id, (
        "[GR_DELRES_OK_200_LIBERA_ASIENTO] La reserva no tiene 'airplane_id' válido: "
        f"{reserva}"
    )
    assert seat_number, (
        "[GR_DELRES_OK_200_LIBERA_ASIENTO] La reserva no tiene 'seat_number' válido: "
        f"{reserva}"
    )

    r = delete_reservas(f"/delete_reservation_by_id/{reservation_id}")

    assert (
        r.status_code == 200
    ), f"[GR_DELRES_OK_200_LIBERA_ASIENTO] Código inesperado en DELETE: {r.status_code} {r.text}"

    resp_json = r.json()
    assert isinstance(resp_json, dict), (
        "[GR_DELRES_OK_200_LIBERA_ASIENTO] La respuesta no es un objeto JSON: "
        f"{resp_json}"
    )

    msg = resp_json.get("message", "")
    msg_lower = msg.lower()
    assert "eliminada" in msg_lower and "reserva" in msg_lower, (
        "[GR_DELRES_OK_200_LIBERA_ASIENTO] Mensaje de éxito inesperado: "
        f"{msg}"
    )

    deleted_res = resp_json.get("deleted_reservation")
    assert isinstance(deleted_res, dict), (
        "[GR_DELRES_OK_200_LIBERA_ASIENTO] Falta 'deleted_reservation' o no es un objeto: "
        f"{resp_json}"
    )

    assert deleted_res.get("reservation_id") == reservation_id
    assert deleted_res.get("airplane_id") == airplane_id
    assert deleted_res.get("seat_number") == seat_number

    rv = get_vuelos(f"/get_airplane_seats/{airplane_id}/seats")
    assert (
        rv.status_code == 200
    ), (
        "[GR_DELRES_OK_200_LIBERA_ASIENTO] Error al consultar asientos en GestiónVuelos: "
        f"{rv.status_code} {rv.text}"
    )

    try:
        seats = rv.json()
    except Exception:
        pytest.fail(
            "[GR_DELRES_OK_200_LIBERA_ASIENTO] La respuesta de GestiónVuelos no es JSON válido."
        )

    assert isinstance(seats, list), (
        "[GR_DELRES_OK_200_LIBERA_ASIENTO] La respuesta de GestiónVuelos no es una lista de asientos."
    )

    seat_info = next((s for s in seats if s.get("seat_number") == seat_number), None)
    assert seat_info is not None, (
        "[GR_DELRES_OK_200_LIBERA_ASIENTO] No se encontró el asiento en GestiónVuelos "
        f"(airplane_id={airplane_id}, seat_number={seat_number})."
    )

    assert seat_info.get("status") == "Libre", (
        "[GR_DELRES_OK_200_LIBERA_ASIENTO] El asiento no quedó 'Libre' en GestiónVuelos "
        f"después del borrado. Estado actual: {seat_info.get('status')}"
    )
