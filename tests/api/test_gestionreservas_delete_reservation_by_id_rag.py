"""
EXPERIMENTO_RAG_04_gestionreservas_delete_reservation_by_id

Pruebas de contrato para el endpoint de GestiónReservas:
    DELETE /delete_reservation_by_id/<int:reservation_id>

Casos cubiertos:
- reservation_id == 0 -> 400.
- Reserva no existente -> 404.
- Caso feliz: eliminar una reserva existente y liberar asiento -> 200.
"""

import os
import requests
import pytest

# Base URL del microservicio GestiónReservas
BASE_URL_RESERVAS = os.getenv("GESTIONRESERVAS_BASE_URL", "http://localhost:5002")

# Base URL del microservicio GestiónVuelos (para verificar liberación de asiento)
BASE_URL_VUELOS = os.getenv("GESTIONVUELOS_BASE_URL", "http://localhost:5001")


def _get_reservas(path: str, **kwargs) -> requests.Response:
    url = f"{BASE_URL_RESERVAS}{path}"
    return requests.get(url, **kwargs)


def _delete_reservas(path: str, **kwargs) -> requests.Response:
    url = f"{BASE_URL_RESERVAS}{path}"
    return requests.delete(url, **kwargs)


def _get_vuelos(path: str, **kwargs) -> requests.Response:
    url = f"{BASE_URL_VUELOS}{path}"
    return requests.get(url, **kwargs)


def _find_any_fake_reservation():
    """
    Devuelve una reserva generada por GestiónReservas usando /get_fake_reservations.

    - Si /get_fake_reservations devuelve 200 y una lista no vacía, retorna el primer elemento.
    - Si devuelve 204 o la estructura no es la esperada, retorna None.
    """
    r = _get_reservas("/get_fake_reservations")

    if r.status_code == 204:
        # No hay reservas generadas
        return None

    if r.status_code != 200:
        # Error inesperado, no rompemos aquí; dejamos que el test haga skip
        return None

    try:
        data = r.json()
    except Exception:
        return None

    if not isinstance(data, list) or not data:
        return None

    return data[0]


@pytest.mark.parametrize(
    "case_id, path, expected_status, expected_msg_sub",
    [
        (
            "GR_DELRES_ID_CERO_400",
            "/delete_reservation_by_id/0",
            400,
            "El ID de reserva debe ser un número positivo",
        ),
        # Nota: no probamos ID negativo porque Flask no matchea /-1 con <int:reservation_id>,
        # y respondería 404 a nivel de routing sin entrar al endpoint.
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

    - ID == 0           -> 400.
    - ID muy grande     -> 404 (reserva no encontrada).
    """
    r = _delete_reservas(path)

    # Intentar parsear el body como JSON, pero no romper si no lo es.
    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        resp_json = {}
        msg_text = r.text

    assert (
        r.status_code == expected_status
    ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"

    # Solo validamos que el mensaje contenga el fragmento esperado (substring).
    assert expected_msg_sub.lower() in msg_text.lower(), (
        f"[{case_id}] No se encontró el texto esperado en el mensaje. "
        f"Buscaba: '{expected_msg_sub}' en: '{msg_text}'"
    )


def test_gestionreservas_delete_reservation_by_id_happy_path():
    """
    Caso feliz:
        Eliminar una reserva existente y verificar que el asiento en GestiónVuelos
        queda marcado como Libre.

    Pasos:
    1) Obtener una reserva fake desde GET /get_fake_reservations.
    2) Extraer reservation_id, airplane_id, seat_number.
    3) DELETE /delete_reservation_by_id/<reservation_id>.
    4) Verificar:
       - status_code == 200.
       - JSON con "message" y "deleted_reservation".
       - Los campos de deleted_reservation corresponden a la reserva borrada.
    5) Consultar GestiónVuelos:
       - GET /get_airplane_seats/<airplane_id>/seats.
       - Verificar que el asiento seat_number tenga status == "Libre".
    """
    reserva = _find_any_fake_reservation()
    if reserva is None:
        pytest.skip(
            "[GR_DELRES_OK_200_LIBERA_ASIENTO] No hay reservas fake disponibles desde /get_fake_reservations."
        )

    reservation_id = reserva.get("reservation_id")
    airplane_id = reserva.get("airplane_id")
    seat_number = reserva.get("seat_number")

    assert isinstance(reservation_id, int) and reservation_id > 0, (
        "[GR_DELRES_OK_200_LIBERA_ASIENTO] La reserva fake no tiene 'reservation_id' entero positivo: "
        f"{reserva}"
    )
    assert airplane_id, (
        "[GR_DELRES_OK_200_LIBERA_ASIENTO] La reserva fake no tiene 'airplane_id' válido: "
        f"{reserva}"
    )
    assert seat_number, (
        "[GR_DELRES_OK_200_LIBERA_ASIENTO] La reserva fake no tiene 'seat_number' válido: "
        f"{reserva}"
    )

    # 3) Eliminar la reserva
    r = _delete_reservas(f"/delete_reservation_by_id/{reservation_id}")

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

    # Verificar que los datos coincidan
    assert deleted_res.get("reservation_id") == reservation_id, (
        "[GR_DELRES_OK_200_LIBERA_ASIENTO] 'reservation_id' en deleted_reservation no coincide con el borrado."
    )
    assert deleted_res.get("airplane_id") == airplane_id, (
        "[GR_DELRES_OK_200_LIBERA_ASIENTO] 'airplane_id' en deleted_reservation no coincide con el original."
    )
    assert deleted_res.get("seat_number") == seat_number, (
        "[GR_DELRES_OK_200_LIBERA_ASIENTO] 'seat_number' en deleted_reservation no coincide con el original."
    )

    # 5) Verificar en GestiónVuelos que el asiento fue liberado
    rv = _get_vuelos(f"/get_airplane_seats/{airplane_id}/seats")
    assert (
        rv.status_code == 200
    ), f"[GR_DELRES_OK_200_LIBERA_ASIENTO] Error al consultar asientos en GestiónVuelos: {rv.status_code} {rv.text}"

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
        "[GR_DELRES_OK_200_LIBERA_ASIENTO] El asiento no quedó 'Libre' en GestiónVuelos después del borrado. "
        f"Estado actual: {seat_info.get('status')}"
    )
