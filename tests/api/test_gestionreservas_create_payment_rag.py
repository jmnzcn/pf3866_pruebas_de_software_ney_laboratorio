"""
EXPERIMENTO_RAG_10_gestionreservas_create_payment

Pruebas de contrato para el endpoint:
    POST /create_payment
"""

import re
import pytest

from gestionreservas_common import (
    post_reservas,
    find_reservation_without_payment,
    find_reservation_with_payment,
)


@pytest.mark.parametrize(
    "case_id, body, expected_status, expected_msg_sub",
    [
        (
            "GR_CPAY_RES_ID_INVALIDO_400",
            {
                "reservation_id": 0,
                "payment_method": "Tarjeta",
                "currency": "Dolares",
            },
            400,
            "El reservation_id debe ser un número entero positivo.",
        ),
        (
            "GR_CPAY_METHOD_INVALIDO_400",
            {
                "reservation_id": 1,
                "payment_method": "Bitcoin",
                "currency": "Dolares",
            },
            400,
            "Método de pago inválido.",
        ),
        (
            "GR_CPAY_MONEDA_INVALIDA_400",
            {
                "reservation_id": 1,
                "payment_method": "Tarjeta",
                "currency": "EUR",
            },
            400,
            "Moneda no soportada.",
        ),
        (
            "GR_CPAY_RES_NO_EXISTE_404",
            {
                "reservation_id": 999999,
                "payment_method": "Tarjeta",
                "currency": "Dolares",
            },
            404,
            "no encontrada",
        ),
    ],
)
def test_gestionreservas_create_payment_validaciones_basicas_y_404(
    case_id,
    body,
    expected_status,
    expected_msg_sub,
):
    """
    Casos de error para POST /create_payment en GestiónReservas.
    """
    r = post_reservas("/create_payment", json=body)

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


def test_gestionreservas_create_payment_reserva_ya_tiene_pago_409():
    """
    Caso de error:
        Intentar crear un pago para una reserva que YA tiene un pago.
    """
    reservation_id = find_reservation_with_payment()
    if reservation_id is None:
        pytest.skip(
            "[GR_CPAY_DUP_409] No se encontró ninguna reserva con pago; "
            "no se puede probar el caso de duplicado."
        )

    body = {
        "reservation_id": reservation_id,
        "payment_method": "Tarjeta",
        "currency": "Dolares",
    }

    r = post_reservas("/create_payment", json=body)

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        resp_json = {}
        msg_text = r.text

    assert (
        r.status_code == 409
    ), f"[GR_CPAY_DUP_409] Se esperaba 409, vino {r.status_code} {r.text}"

    assert "ya tiene un pago registrado" in msg_text.lower(), (
        "[GR_CPAY_DUP_409] Mensaje inesperado para pago duplicado. "
        f"message: {msg_text!r}"
    )


def test_gestionreservas_create_payment_happy_path():
    """
    Caso feliz:
        Crear un pago para una reserva existente SIN pago previo.
    """
    reserva = find_reservation_without_payment()
    if reserva is None:
        pytest.skip(
            "[GR_CPAY_OK_201] No se encontraron reservas sin pago para "
            "probar el caso feliz."
        )

    reservation_id = reserva.get("reservation_id")
    assert reservation_id, (
        "[GR_CPAY_OK_201] La reserva seleccionada no tiene un reservation_id válido: "
        f"{reserva}"
    )

    body = {
        "reservation_id": reservation_id,
        "payment_method": "Tarjeta",
        "currency": "Dolares",
    }

    r = post_reservas("/create_payment", json=body)

    assert (
        r.status_code == 201
    ), f"[GR_CPAY_OK_201] Código inesperado en create_payment: {r.status_code} {r.text}"

    try:
        resp_json = r.json()
    except Exception:
        pytest.fail(
            "[GR_CPAY_OK_201] La respuesta no es JSON válido. "
            f"Body crudo: {r.text}"
        )

    assert isinstance(resp_json, dict), (
        "[GR_CPAY_OK_201] La respuesta no es un objeto JSON."
    )

    msg = resp_json.get("message", "")
    msg_lower = msg.lower()

    assert "pago" in msg_lower and "registrado" in msg_lower, (
        "[GR_CPAY_OK_201] Mensaje de éxito inesperado: "
        f"{msg}"
    )

    payment = resp_json.get("payment")
    assert isinstance(payment, dict), (
        "[GR_CPAY_OK_201] La respuesta no contiene un objeto 'payment' válido: "
        f"{resp_json}"
    )

    payment_id = payment.get("payment_id")
    assert isinstance(payment_id, str) and re.match(r"^PAY\d{6}$", payment_id), (
        "[GR_CPAY_OK_201] 'payment_id' no tiene el formato esperado PAYxxxxxx: "
        f"{payment_id!r}"
    )

    assert payment.get("reservation_id") == reservation_id, (
        "[GR_CPAY_OK_201] reservation_id del payment no coincide con el usado en la petición. "
        f"reserv_id_req={reservation_id}, "
        f"reserv_id_resp={payment.get('reservation_id')}"
    )

    assert payment.get("status") == "Pagado", (
        "[GR_CPAY_OK_201] status del payment esperado 'Pagado', vino: "
        f"{payment.get('status')!r}"
    )
