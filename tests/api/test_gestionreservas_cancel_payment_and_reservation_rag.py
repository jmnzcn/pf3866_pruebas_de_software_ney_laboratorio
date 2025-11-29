"""
EXPERIMENTO_RAG_11_gestionreservas_cancel_payment_and_reservation

Pruebas de contrato para el endpoint:
    DELETE /cancel_payment_and_reservation/<string:payment_id>

Comportamiento esperado (según app.py en GestiónReservas):

- payment_id con formato inválido (no 'PAY' + 6 dígitos, tras aplicar .strip().upper()):
    -> 400
    -> {"message": "El formato del payment_id es inválido. Debe ser como PAY123456"}

- payment_id válido pero que NO existe en `payments`:
    -> 404
    -> {"message": "No se encontró el pago con ID: <payment_id>"}

- Caso feliz: payment_id existente con datos completos:
    -> 200
    -> {
         "message": "Cancelación exitosa: pago y reserva eliminados, asiento liberado.",
         "deleted_payment": {...},
         "deleted_reservation": {...}
       }
"""

import pytest

from gestionreservas_common import (
    delete_reservas,
    get_reservas,
    find_existing_payment_with_full_data,
)


def test_gestionreservas_cancel_payment_and_reservation_formato_invalido_400():
    """
    payment_id con formato inválido (no 'PAY' + 6 dígitos, aún tras .upper()) -> 400.
    """
    invalid_ids = [
        "XYZ123",
        "123456",
        "PAY123",
        "PAY12345",
        "PAY1234567",
        "PAYABCDEF",
    ]

    for bad_id in invalid_ids:
        r = delete_reservas(f"/cancel_payment_and_reservation/{bad_id}")

        try:
            resp_json = r.json()
            msg_text = resp_json.get("message", "") or resp_json.get("error", "")
        except Exception:
            resp_json = {}
            msg_text = r.text

        assert (
            r.status_code == 400
        ), f"[GR_CANPAY_FMT_400] Para {bad_id!r} se esperaba 400, vino {r.status_code} {r.text}"

        assert "formato del payment_id es inválido" in msg_text.lower(), (
            f"[GR_CANPAY_FMT_400] Mensaje inesperado para {bad_id!r}. "
            f"message: {msg_text!r}"
        )


def test_gestionreservas_cancel_payment_and_reservation_no_existe_404():
    """
    payment_id con formato válido pero que no existe en `payments` -> 404.
    """
    candidate_id = "PAY999999"

    r = delete_reservas(f"/cancel_payment_and_reservation/{candidate_id}")

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        resp_json = {}
        msg_text = r.text

    assert r.status_code == 404, (
        "[GR_CANPAY_404] Se esperaba 404 para pago inexistente, "
        f"vino {r.status_code} {r.text}"
    )

    assert "no se encontró el pago con id" in msg_text.lower(), (
        "[GR_CANPAY_404] Mensaje inesperado para 404. "
        f"message: {msg_text!r}"
    )


def test_gestionreservas_cancel_payment_and_reservation_happy_path():
    """
    Caso feliz:
        Cancelar un pago y su reserva asociada, liberando el asiento.
    """
    pago = find_existing_payment_with_full_data()
    if pago is None:
        pytest.skip(
            "[GR_CANPAY_OK] No se encontró ningún pago existente con datos completos; "
            "no se puede probar el caso feliz."
        )

    payment_id = pago["payment_id"]
    reservation_id = pago["reservation_id"]

    r = delete_reservas(f"/cancel_payment_and_reservation/{payment_id}")

    assert (
        r.status_code == 200
    ), f"[GR_CANPAY_OK] Se esperaba 200 al cancelar {payment_id}, vino {r.status_code} {r.text}"

    try:
        resp_json = r.json()
    except Exception:
        pytest.fail(
            "[GR_CANPAY_OK] La respuesta no es JSON válido. "
            f"Body crudo: {r.text}"
        )

    assert isinstance(resp_json, dict), (
        "[GR_CANPAY_OK] La respuesta no es un objeto JSON (dict)."
    )

    msg = resp_json.get("message", "")
    msg_lower = msg.lower()
    assert "cancelación exitosa" in msg_lower, (
        "[GR_CANPAY_OK] El mensaje no indica cancelación exitosa. "
        f"message: {msg!r}"
    )

    deleted_payment = resp_json.get("deleted_payment")
    deleted_reservation = resp_json.get("deleted_reservation")

    assert isinstance(deleted_payment, dict), (
        "[GR_CANPAY_OK] No viene un objeto 'deleted_payment' válido en la respuesta."
    )
    assert isinstance(deleted_reservation, dict), (
        "[GR_CANPAY_OK] No viene un objeto 'deleted_reservation' válido en la respuesta."
    )

    assert deleted_payment.get("payment_id") == payment_id, (
        "[GR_CANPAY_OK] payment_id en 'deleted_payment' no coincide con el solicitado. "
        f"esperado={payment_id!r}, respuesta={deleted_payment.get('payment_id')!r}"
    )

    if "reservation_id" in deleted_reservation:
        assert deleted_reservation.get("reservation_id") == reservation_id, (
            "[GR_CANPAY_OK] reservation_id en 'deleted_reservation' "
            "no coincide con el del pago. "
            f"pago_res_id={reservation_id}, "
            f"del_res_id={deleted_reservation.get('reservation_id')}"
        )

    r_check = get_reservas(f"/get_payment_by_id/{payment_id}")
    if r_check.status_code != 400:
        try:
            msg_check = r_check.json().get("message", "")
        except Exception:
            msg_check = r_check.text

        assert r_check.status_code == 404, (
            "[GR_CANPAY_OK] Tras cancelar, se esperaba 404 al consultar "
            f"el pago {payment_id}, vino {r_check.status_code} {r_check.text}"
        )

        msg_check_lower = msg_check.lower()
        assert (
            "no se encontró ningún pago" in msg_check_lower
            or "no hay pagos generados aún" in msg_check_lower
        ), (
            "[GR_CANPAY_OK] Mensaje inesperado al consultar pago luego de cancelar. "
            f"message: {msg_check!r}"
        )
