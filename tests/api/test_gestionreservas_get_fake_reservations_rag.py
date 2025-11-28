"""
EXPERIMENTO_RAG_06_gestionreservas_get_fake_reservations

Pruebas de contrato para el endpoint:
    GET /get_fake_reservations

Comportamiento esperado (según app.py en GestiónReservas):

- Si NO hay reservas en memoria:
    -> 204
    -> body JSON: {"message": "No hay reservas generadas actualmente."}

- Si SÍ hay reservas:
    -> 200
    -> body JSON: lista de reservas, cada una con al menos:
       - reservation_id (int)
       - reservation_code (str)
       - passport_number (str)
       - full_name (str)
       - email (str)
       - phone_number (str)
       - emergency_contact_name (str)
       - emergency_contact_phone (str)
       - airplane_id (int)
       - airplane_route_id (int)
       - seat_number (str)
       - status (str, "Reservado" o "Pagado")
"""

import os
import requests
import pytest

# Base URL del microservicio GestiónReservas
BASE_URL_RESERVAS = os.getenv("GESTIONRESERVAS_BASE_URL", "http://localhost:5002")


def _get_reservas(path: str, **kwargs) -> requests.Response:
    url = f"{BASE_URL_RESERVAS}{path}"
    return requests.get(url, timeout=20, **kwargs)


def test_gestionreservas_get_fake_reservations_status_y_mensaje():
    """
    Verifica el contrato básico de status + mensaje para:

        GET /get_fake_reservations

    Dos comportamientos válidos:

    1) No hay reservas (lista interna vacía):
        - status_code == 204
        - JSON con "message" conteniendo "No hay reservas generadas actualmente."

    2) Hay reservas:
        - status_code == 200
        - JSON es una lista (puede tener uno o más elementos).
    """
    r = _get_reservas("/get_fake_reservations")

    # Intentar parsear JSON; si falla, dejar data en None
    try:
        data = r.json()
    except Exception:
        data = None

    if r.status_code == 204:
        # Caso "sin reservas"
        assert isinstance(data, dict), (
            "[GR_GETFAKE_204] Se esperaba un objeto JSON con 'message'. "
            f"Respuesta cruda: {r.text}"
        )
        msg = str(data.get("message", "")).lower()
        assert "no hay reservas generadas actualmente" in msg, (
            "[GR_GETFAKE_204] Mensaje inesperado para estado 204. "
            f"message: {data.get('message')!r}"
        )

    elif r.status_code == 200:
        # Caso "con reservas"
        assert isinstance(data, list), (
            "[GR_GETFAKE_200] Se esperaba una lista de reservas en el body. "
            f"Tipo real: {type(data)}"
        )

    else:
        pytest.fail(
            f"[GR_GETFAKE_STATUS] Código de estado inesperado: "
            f"{r.status_code} body={r.text}"
        )


def test_gestionreservas_get_fake_reservations_estructura_cuando_hay_reservas():
    """
    Si existen reservas (status 200), se valida la estructura básica
    de al menos una de ellas.

    Si el endpoint devuelve 204 (sin reservas), se hace skip de esta prueba.
    """
    r = _get_reservas("/get_fake_reservations")

    try:
        data = r.json()
    except Exception:
        data = None

    if r.status_code == 204:
        pytest.skip("[GR_GETFAKE_SHAPE] No hay reservas generadas (204); "
                    "no se puede validar estructura de la lista.")

    assert r.status_code == 200, (
        "[GR_GETFAKE_SHAPE] Se esperaba 200 para validar estructura, "
        f"pero se obtuvo {r.status_code} body={r.text}"
    )

    assert isinstance(data, list), (
        "[GR_GETFAKE_SHAPE] Se esperaba una lista de reservas."
    )
    assert data, (
        "[GR_GETFAKE_SHAPE] La lista de reservas vino vacía con status 200, "
        "lo cual contradice la lógica de 204 cuando no hay reservas."
    )

    reserva = data[0]
    assert isinstance(reserva, dict), (
        "[GR_GETFAKE_SHAPE] El primer elemento de la lista no es un objeto JSON."
    )

    # Campos mínimos esperados
    required_keys = [
        "reservation_id",
        "reservation_code",
        "passport_number",
        "full_name",
        "email",
        "phone_number",
        "emergency_contact_name",
        "emergency_contact_phone",
        "airplane_id",
        "airplane_route_id",
        "seat_number",
        "status",
    ]

    missing = [k for k in required_keys if k not in reserva]
    assert not missing, (
        "[GR_GETFAKE_SHAPE] Faltan campos requeridos en la reserva: "
        f"{missing}. Reserva: {reserva}"
    )

    # Validaciones suaves de tipo/valor para algunos campos
    assert isinstance(reserva["reservation_id"], int), (
        "[GR_GETFAKE_SHAPE] reservation_id debe ser int."
    )
    assert isinstance(reserva["reservation_code"], str) and reserva["reservation_code"], (
        "[GR_GETFAKE_SHAPE] reservation_code debe ser string no vacío."
    )
    assert isinstance(reserva["airplane_id"], int), (
        "[GR_GETFAKE_SHAPE] airplane_id debe ser int."
    )
    assert isinstance(reserva["airplane_route_id"], int), (
        "[GR_GETFAKE_SHAPE] airplane_route_id debe ser int."
    )
    assert isinstance(reserva["seat_number"], str) and reserva["seat_number"], (
        "[GR_GETFAKE_SHAPE] seat_number debe ser string no vacío."
    )

    assert reserva["status"] in ("Reservado", "Pagado"), (
        "[GR_GETFAKE_SHAPE] status debe ser 'Reservado' o 'Pagado', "
        f"pero vino: {reserva['status']!r}"
    )
