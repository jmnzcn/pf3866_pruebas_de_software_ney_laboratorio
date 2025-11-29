"""
EXPERIMENTO_RAG_03_gestionreservas_get_reservation_by_id

Pruebas de contrato para el endpoint de GestiónReservas:
    GET /get_reservation_by_id/<reservation_id>
"""

import pytest

from gestionreservas_common import (
    get_reservas,
    find_any_reservation,
)


@pytest.mark.parametrize(
    "case_id, path, expected_status, expected_msg_sub",
    [
        (
            "GR_GETRESID_NO_NUM_ABC_400",
            "/get_reservation_by_id/abc",
            400,
            "El ID de reserva debe ser un número entero positivo.",
        ),
        (
            "GR_GETRESID_NO_NUM_DECIMAL_400",
            "/get_reservation_by_id/10.5",
            400,
            "El ID de reserva debe ser un número entero positivo.",
        ),
        (
            "GR_GETRESID_CERO_400",
            "/get_reservation_by_id/0",
            400,
            "El ID de reserva debe ser un número positivo mayor que cero.",
        ),
        (
            "GR_GETRESID_NEGATIVO_400",
            "/get_reservation_by_id/-1",
            400,
            "El ID de reserva debe ser un número positivo mayor que cero.",
        ),
        (
            "GR_GETRESID_NO_EXISTE_404",
            "/get_reservation_by_id/999999",
            404,
            "Reserva no encontrada",
        ),
    ],
)
def test_gestionreservas_get_reservation_by_id_validaciones_y_404(
    case_id,
    path,
    expected_status,
    expected_msg_sub,
):
    """
    Casos de error para:
        GET /get_reservation_by_id/<reservation_id>
    """
    r = get_reservas(path)

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


def test_gestionreservas_get_reservation_by_id_happy_path():
    """
    Caso feliz: obtener una reserva existente por ID.
    """
    reserva = find_any_reservation()
    if reserva is None:
        pytest.skip(
            "[GR_GETRESID_OK_200] No hay reservas disponibles para el caso feliz."
        )

    reservation_id = reserva.get("reservation_id")
    assert isinstance(reservation_id, int) and reservation_id > 0, (
        "[GR_GETRESID_OK_200] La reserva no tiene un 'reservation_id' entero positivo: "
        f"{reserva}"
    )

    r = get_reservas(f"/get_reservation_by_id/{reservation_id}")

    assert (
        r.status_code == 200
    ), f"[GR_GETRESID_OK_200] Código inesperado: {r.status_code} {r.text}"

    resp_json = r.json()
    assert isinstance(resp_json, dict), (
        "[GR_GETRESID_OK_200] La respuesta no es un objeto JSON: "
        f"{resp_json}"
    )

    for field in [
        "reservation_id",
        "reservation_code",
        "airplane_id",
        "airplane_route_id",
        "seat_number",
        "status",
    ]:
        assert field in resp_json, (
            f"[GR_GETRESID_OK_200] Falta el campo '{field}' en la respuesta: "
            f"{resp_json}"
        )

    assert resp_json["reservation_id"] == reservation_id

    status = resp_json.get("status")
    assert status in ("Reservado", "Pagado"), (
        "[GR_GETRESID_OK_200] El campo 'status' no es válido: "
        f"{status}"
    )
