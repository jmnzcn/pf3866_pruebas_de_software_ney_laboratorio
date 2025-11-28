"""
EXPERIMENTO_RAG_02_gestionreservas_get_reservation_by_code

Pruebas de contrato (caja negra) para el endpoint:

    GET /get_reservation_by_code/<reservation_code>

del microservicio GestiónReservas.
"""

import os
import requests
import pytest

# Base URL del microservicio GestiónReservas
BASE_URL = os.getenv("GESTIONRESERVAS_BASE_URL", "http://localhost:5002")


def _get(path: str, **kwargs) -> requests.Response:
    """Helper simple para hacer GET contra GestiónReservas."""
    url = f"{BASE_URL}{path}"
    return requests.get(url, **kwargs)


def _obtener_codigo_reserva_existente() -> str | None:
    """
    Intenta obtener el código de una reserva existente usando:

        GET /get_fake_reservations

    Estrategia:
    - Si el endpoint devuelve 204 -> no hay reservas -> None.
    - Si devuelve 200 y es una lista no vacía -> retorna reservation_code de la primera.
    - Si la respuesta es inesperada o está mal formada -> None.
    """
    r = _get("/get_fake_reservations")

    # Si el servicio indica explícitamente que no hay reservas
    if r.status_code == 204:
        return None

    # Si hay algún error raro, mejor saltar el caso feliz desde el test
    if r.status_code != 200:
        return None

    try:
        data = r.json()
    except Exception:
        return None

    if not isinstance(data, list) or not data:
        return None

    primera = data[0]
    if not isinstance(primera, dict):
        return None

    return primera.get("reservation_code")


@pytest.mark.parametrize(
    "case_id, path, expected_status, expected_msg_sub",
    [
        # Código demasiado corto (< 6 caracteres)
        (
            "GR_GETRES_CODE_CORTO_400",
            "/get_reservation_by_code/ABC12",
            400,
            "string alfanumérico de 6 caracteres",
        ),
        # Carácter inválido (no [A-Z0-9])
        (
            "GR_GETRES_CODE_CHAR_INVALIDO_400",
            "/get_reservation_by_code/ABC12-",
            400,
            "string alfanumérico de 6 caracteres",
        ),
        # Reserva inexistente
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

    - Código con formato inválido -> 400.
    - Reserva inexistente -> 404.
    """
    r = _get(path)

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

    # Verificar que el mensaje contenga al menos el fragmento esperado
    assert expected_msg_sub.lower() in msg_text.lower(), (
        f"[{case_id}] No se encontró el texto esperado en el mensaje. "
        f"Buscaba: '{expected_msg_sub}' en: '{msg_text}'"
    )


def test_gestionreservas_get_reservation_by_code_happy_path():
    """
    Caso feliz para:

        GET /get_reservation_by_code/<reservation_code>

    Estrategia:
    1) Consultar /get_fake_reservations para obtener una reserva generada al inicio.
    2) Tomar su reservation_code.
    3) Llamar GET /get_reservation_by_code/<reservation_code>.
    4) Verificar:
       - status_code == 200
       - La respuesta es un JSON con, al menos:
         - reservation_code igual al consultado.
         - reservation_id entero positivo.
         - airplane_id y airplane_route_id enteros.
         - seat_number string no vacío.
         - status en {"Reservado", "Pagado"}.
    """
    reservation_code = _obtener_codigo_reserva_existente()
    if not reservation_code:
        pytest.skip(
            "[GR_GETRES_OK_200] No se encontró ninguna reserva fake para probar el caso feliz."
        )

    r = _get(f"/get_reservation_by_code/{reservation_code}")
    assert (
        r.status_code == 200
    ), f"[GR_GETRES_OK_200] Código inesperado: {r.status_code} {r.text}"

    resp_json = r.json()
    assert isinstance(
        resp_json, dict
    ), f"[GR_GETRES_OK_200] La respuesta no es un objeto JSON: {resp_json}"

    # reservation_code debe coincidir exactamente
    assert (
        resp_json.get("reservation_code") == reservation_code.upper()
    ), (
        "[GR_GETRES_OK_200] reservation_code de la respuesta no coincide con "
        f"el consultado. Esperado={reservation_code.upper()} Obtenido={resp_json.get('reservation_code')}"
    )

    # reservation_id entero positivo
    reservation_id = resp_json.get("reservation_id")
    assert isinstance(reservation_id, int) and reservation_id > 0, (
        "[GR_GETRES_OK_200] 'reservation_id' inválido en la respuesta: "
        f"{reservation_id}"
    )

    # airplane_id y airplane_route_id como enteros
    airplane_id = resp_json.get("airplane_id")
    route_id = resp_json.get("airplane_route_id")
    assert isinstance(airplane_id, int), (
        "[GR_GETRES_OK_200] 'airplane_id' no es entero: "
        f"{airplane_id}"
    )
    assert isinstance(route_id, int), (
        "[GR_GETRES_OK_200] 'airplane_route_id' no es entero: "
        f"{route_id}"
    )

    # seat_number string no vacío
    seat_number = resp_json.get("seat_number")
    assert isinstance(seat_number, str) and seat_number.strip(), (
        "[GR_GETRES_OK_200] 'seat_number' inválido en la respuesta: "
        f"{seat_number}"
    )

    # status debe ser Reservado o Pagado
    status = resp_json.get("status")
    assert status in {"Reservado", "Pagado"}, (
        "[GR_GETRES_OK_200] 'status' inválido; se esperaba 'Reservado' o "
        f"'Pagado' y se obtuvo: {status}"
    )
