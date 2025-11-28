"""
EXPERIMENTO_RAG_03_gestionreservas_get_reservation_by_id

Pruebas de contrato para el endpoint de GestiónReservas:
    GET /get_reservation_by_id/<reservation_id>

Casos cubiertos:
- reservation_id no numérico -> 400.
- reservation_id == 0 -> 400.
- reservation_id < 0 -> 400.
- Reserva no existente -> 404.
- Caso feliz: reserva existente (usando /get_fake_reservations) -> 200.
"""

import os
import requests
import pytest

# Base URL del microservicio GestiónReservas
BASE_URL = os.getenv("GESTIONRESERVAS_BASE_URL", "http://localhost:5002")


def _get(path: str, **kwargs) -> requests.Response:
    url = f"{BASE_URL}{path}"
    return requests.get(url, **kwargs)


def _find_any_fake_reservation():
    """
    Intenta obtener al menos una reserva generada por GestiónReservas
    usando el endpoint /get_fake_reservations.

    - Si devuelve 200 y una lista no vacía, retorna el primer elemento.
    - Si devuelve 204 o la estructura no es la esperada, retorna None.
    """
    r = _get("/get_fake_reservations")

    # Si no hay reservas generadas
    if r.status_code == 204:
        return None

    if r.status_code != 200:
        # Estructura inesperada o error: mejor no fallar aquí; dejamos que el test haga skip.
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
        # ID no numérico
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
        # ID == 0
        (
            "GR_GETRESID_CERO_400",
            "/get_reservation_by_id/0",
            400,
            "El ID de reserva debe ser un número positivo mayor que cero.",
        ),
        # ID negativo
        (
            "GR_GETRESID_NEGATIVO_400",
            "/get_reservation_by_id/-1",
            400,
            "El ID de reserva debe ser un número positivo mayor que cero.",
        ),
        # Reserva no existente
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

    - ID no numérico -> 400.
    - ID == 0 -> 400.
    - ID < 0 -> 400.
    - ID muy grande (no existe) -> 404.
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

    # Solo validamos que el mensaje contenga el fragmento esperado (substring).
    assert expected_msg_sub.lower() in msg_text.lower(), (
        f"[{case_id}] No se encontró el texto esperado en el mensaje. "
        f"Buscaba: '{expected_msg_sub}' en: '{msg_text}'"
    )


def test_gestionreservas_get_reservation_by_id_happy_path():
    """
    Caso feliz: obtener una reserva existente por ID.

    Estrategia:
    1) Usar GET /get_fake_reservations para obtener al menos una reserva.
    2) Tomar su reservation_id.
    3) Llamar GET /get_reservation_by_id/<reservation_id>.
    4) Verificar que:
       - Devuelva 200.
       - El JSON contenga reservation_id, reservation_code, airplane_id,
         airplane_route_id, seat_number y status.
       - reservation_id coincida con el utilizado.
       - status ∈ {"Reservado", "Pagado"}.
    """
    reserva = _find_any_fake_reservation()
    if reserva is None:
        pytest.skip(
            "[GR_GETRESID_OK_200] No hay reservas fake disponibles desde /get_fake_reservations."
        )

    reservation_id = reserva.get("reservation_id")
    assert isinstance(reservation_id, int) and reservation_id > 0, (
        "[GR_GETRESID_OK_200] La reserva fake no tiene un 'reservation_id' entero positivo: "
        f"{reserva}"
    )

    r = _get(f"/get_reservation_by_id/{reservation_id}")

    assert (
        r.status_code == 200
    ), f"[GR_GETRESID_OK_200] Código inesperado: {r.status_code} {r.text}"

    resp_json = r.json()
    assert isinstance(resp_json, dict), (
        "[GR_GETRESID_OK_200] La respuesta no es un objeto JSON: "
        f"{resp_json}"
    )

    # Campos mínimos esperados
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

    # ID debe coincidir
    assert resp_json["reservation_id"] == reservation_id, (
        "[GR_GETRESID_OK_200] El reservation_id de la respuesta no coincide con el solicitado. "
        f"Esperado: {reservation_id}, Recibido: {resp_json['reservation_id']}"
    )

    # status debe ser Reservado o Pagado
    status = resp_json.get("status")
    assert status in ("Reservado", "Pagado"), (
        "[GR_GETRESID_OK_200] El campo 'status' no es válido: "
        f"{status}"
    )
