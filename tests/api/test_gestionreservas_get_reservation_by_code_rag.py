"""
EXPERIMENTO_RAG_02_gestionreservas_get_reservation_by_code

Pruebas de contrato (caja negra) para el endpoint:

    GET /get_reservation_by_code/<reservation_code>
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
            "GR_GETRES_CODE_CORTO_400",
            "/get_reservation_by_code/ABC12",
            400,
            "string alfanumérico de 6 caracteres",
        ),
        (
            "GR_GETRES_CODE_CHAR_INVALIDO_400",
            "/get_reservation_by_code/ABC12-",
            400,
            "string alfanumérico de 6 caracteres",
        ),
        (
            "GR_GETRES_NO_EXISTE_404",
            "/get_reservation_by_code/ZZZ999",
            404,
            "Reserva no encontrada",
        ),
    ],
)
def test_gestionreservas_get_reservation_by_code_validaciones_y_404(
    case_id,
    path,
    expected_status,
    expected_msg_sub,
):
    """
    Casos de error para:
        GET /get_reservation_by_code/<reservation_code>
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


def test_gestionreservas_get_reservation_by_code_happy_path():
    """
    Caso feliz:
        GET /get_reservation_by_code/<reservation_code>
    """
    reserva = find_any_reservation()
    if not reserva:
        pytest.skip(
            "[GR_GETRES_OK_200] No se encontró ninguna reserva para probar el caso feliz."
        )

    reservation_code = reserva.get("reservation_code")
    if not reservation_code:
        pytest.skip(
            "[GR_GETRES_OK_200] La reserva encontrada no tiene reservation_code."
        )

    r = get_reservas(f"/get_reservation_by_code/{reservation_code}")
    assert (
        r.status_code == 200
    ), f"[GR_GETRES_OK_200] Código inesperado: {r.status_code} {r.text}"

    resp_json = r.json()
    assert isinstance(
        resp_json, dict
    ), f"[GR_GETRES_OK_200] La respuesta no es un objeto JSON: {resp_json}"

    assert resp_json.get("reservation_code") == reservation_code.upper(), (
        "[GR_GETRES_OK_200] reservation_code de la respuesta no coincide con "
        f"el consultado. Esperado={reservation_code.upper()} "
        f"Obtenido={resp_json.get('reservation_code')}"
    )

    reservation_id = resp_json.get("reservation_id")
    assert isinstance(reservation_id, int) and reservation_id > 0

    airplane_id = resp_json.get("airplane_id")
    route_id = resp_json.get("airplane_route_id")
    assert isinstance(airplane_id, int)
    assert isinstance(route_id, int)

    seat_number = resp_json.get("seat_number")
    assert isinstance(seat_number, str) and seat_number.strip()

    status = resp_json.get("status")
    assert status in {"Reservado", "Pagado"}
