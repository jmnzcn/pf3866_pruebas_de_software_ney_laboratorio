"""
EXPERIMENTO_RAG_06_gestionreservas_get_fake_reservations

Pruebas de contrato para el endpoint:
    GET /get_fake_reservations
"""

import pytest

from gestionreservas_common import get_reservas


def test_gestionreservas_get_fake_reservations_status_y_mensaje():
    """
    Verifica el contrato básico de status + mensaje para:
        GET /get_fake_reservations
    """
    r = get_reservas("/get_fake_reservations")

    try:
        data = r.json()
    except Exception:
        data = None

    if r.status_code == 204:
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
        assert isinstance(data, list), (
            "[GR_GETFAKE_200] Se esperaba una lista de reservas en el body. "
            f"Tipo real: {type(data)}"
        )
    else:
        pytest.fail(
            "[GR_GETFAKE_STATUS] Código de estado inesperado: "
            f"{r.status_code} body={r.text}"
        )


def test_gestionreservas_get_fake_reservations_estructura_cuando_hay_reservas():
    """
    Si existen reservas (status 200), se valida la estructura básica
    de al menos una de ellas.
    """
    r = get_reservas("/get_fake_reservations")

    try:
        data = r.json()
    except Exception:
        data = None

    if r.status_code == 204:
        pytest.skip(
            "[GR_GETFAKE_SHAPE] No hay reservas generadas (204); "
            "no se puede validar estructura de la lista."
        )

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

    assert isinstance(reserva["reservation_id"], int)
    assert isinstance(reserva["reservation_code"], str) and reserva["reservation_code"]
    assert isinstance(reserva["airplane_id"], int)
    assert isinstance(reserva["airplane_route_id"], int)
    assert isinstance(reserva["seat_number"], str) and reserva["seat_number"]

    assert reserva["status"] in ("Reservado", "Pagado")
