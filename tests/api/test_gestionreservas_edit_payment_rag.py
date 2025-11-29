"""
EXPERIMENTO_RAG_12_gestionreservas_edit_payment

Pruebas de contrato para el endpoint:
    PUT /edit_payment/<string:payment_id>
"""

import pytest

from gestionreservas_common import (
    put_reservas,
    find_existing_payment_with_full_data,
)

BASE_VALID_BODY = {
    "payment_method": "Tarjeta",
    "payment_date": "Abril 25, 2025 - 17:00:00",
    "transaction_reference": "XYZ123ABC456",
}


@pytest.mark.parametrize(
    "case_id, payment_id, body, expected_status, expected_msg_sub, expect_415",
    [
        (
            "GR_EDITPAY_FMT_400",
            "ABC",
            BASE_VALID_BODY,
            400,
            "formato del payment_id es inválido",
            False,
        ),
        (
            "GR_EDITPAY_NO_EXISTE_404",
            "PAY999999",
            BASE_VALID_BODY,
            404,
            "no se encontró el pago con id",
            False,
        ),
        (
            "GR_EDITPAY_BODY_AUSENTE_415",
            "REAL_FROM_FIXTURE",
            None,
            415,
            "unsupported media type",
            True,
        ),
        (
            "GR_EDITPAY_METODO_INVALIDO_400",
            "REAL_FROM_FIXTURE",
            {"payment_method": "Bitcoin"},
            400,
            "método de pago inválido",
            False,
        ),
    ],
)
def test_gestionreservas_edit_payment_validaciones_basicas(
    case_id,
    payment_id,
    body,
    expected_status,
    expected_msg_sub,
    expect_415,
):
    """
    Casos de error "locales" para:
        PUT /edit_payment/<payment_id>
    """
    if payment_id == "REAL_FROM_FIXTURE":
        pago = find_existing_payment_with_full_data()
        if pago is None:
            pytest.skip(f"[{case_id}] No se encontró ningún pago en el sistema.")
        payment_id = pago.get("payment_id")
        assert payment_id, f"[{case_id}] El pago encontrado no tiene payment_id."

    path = f"/edit_payment/{payment_id}"

    if body is None:
        r = put_reservas(path)
    else:
        r = put_reservas(path, json=body)

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        resp_json = {}
        msg_text = r.text

    assert (
        r.status_code == expected_status
    ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"

    msg_lower = msg_text.lower()

    if expect_415:
        assert "unsupported media type" in msg_lower, (
            f"[{case_id}] Para 415 se esperaba mención de 'Unsupported Media Type'. "
            f"message: {msg_text!r}"
        )
    else:
        assert expected_msg_sub.lower() in msg_lower, (
            f"[{case_id}] No se encontró el texto esperado en el mensaje. "
            f"Buscaba: '{expected_msg_sub}' en: '{msg_text}'"
        )


def test_gestionreservas_edit_payment_happy_path():
    """
    Caso feliz:
        Editar un pago existente (método, fecha y referencia).
    """
    pago = find_existing_payment_with_full_data()
    if pago is None:
        pytest.skip(
            "[GR_EDITPAY_OK] No se encontró ningún pago para probar el caso feliz."
        )

    payment_id = pago["payment_id"]

    nuevo_metodo = "SINPE"
    nueva_fecha = "Mayo 10, 2025 - 12:00:00"
    nueva_ref = "NUEVAREF123456"

    body = {
        "payment_method": nuevo_metodo,
        "payment_date": nueva_fecha,
        "transaction_reference": nueva_ref,
    }

    r = put_reservas(f"/edit_payment/{payment_id}", json=body)

    assert (
        r.status_code == 200
    ), f"[GR_EDITPAY_OK] Código inesperado al editar pago: {r.status_code} {r.text}"

    try:
        resp_json = r.json()
    except Exception:
        pytest.fail(
            "[GR_EDITPAY_OK] La respuesta no es JSON válido. "
            f"Body crudo: {r.text}"
        )

    assert isinstance(resp_json, dict), (
        "[GR_EDITPAY_OK] La respuesta no es un objeto JSON (dict)."
    )

    msg = resp_json.get("message", "")
    msg_lower = msg.lower()
    assert "pago actualizado correctamente" in msg_lower, (
        "[GR_EDITPAY_OK] Mensaje de éxito inesperado: "
        f"{msg}"
    )

    payment = resp_json.get("payment")
    assert isinstance(payment, dict), (
        "[GR_EDITPAY_OK] La respuesta no contiene un objeto 'payment' válido."
    )

    assert payment.get("payment_id") == payment_id, (
        "[GR_EDITPAY_OK] payment_id en la respuesta no coincide con el solicitado. "
        f"esperado={payment_id!r}, respuesta={payment.get('payment_id')!r}"
    )

    assert payment.get("payment_method") == nuevo_metodo
    assert payment.get("payment_date") == nueva_fecha
    assert payment.get("transaction_reference") == nueva_ref
