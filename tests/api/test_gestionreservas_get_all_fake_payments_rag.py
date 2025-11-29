"""
EXPERIMENTO_RAG_07_gestionreservas_get_all_fake_payments

Pruebas de contrato para el endpoint:
    GET /get_all_fake_payments
"""

import pytest

from gestionreservas_common import get_reservas


def test_gestionreservas_get_all_fake_payments_status_y_formato_basico():
    """
    Verifica el contrato básico de status + tipo de body para:
        GET /get_all_fake_payments
    """
    r = get_reservas("/get_all_fake_payments")

    assert r.status_code == 200, (
        "[GR_GETPAYS_STATUS] Código de estado inesperado: "
        f"{r.status_code} body={r.text}"
    )

    try:
        data = r.json()
    except Exception:
        pytest.fail(
            "[GR_GETPAYS_STATUS] La respuesta no es JSON válido. "
            f"Body crudo: {r.text}"
        )

    if isinstance(data, dict):
        msg = str(data.get("message", "")).lower()
        assert "no hay pagos generados actualmente" in msg, (
            "[GR_GETPAYS_STATUS] Para dict se esperaba mensaje "
            "'No hay pagos generados actualmente.' "
            f"pero vino: {data!r}"
        )
    elif isinstance(data, list):
        pass
    else:
        pytest.fail(
            "[GR_GETPAYS_STATUS] Tipo de body inesperado. "
            f"Se esperaba dict o list, pero vino: {type(data)}"
        )


def test_gestionreservas_get_all_fake_payments_estructura_cuando_hay_pagos():
    """
    Si el endpoint devuelve una lista de pagos, se valida la estructura
    básica de al menos uno de ellos.
    """
    r = get_reservas("/get_all_fake_payments")

    try:
        data = r.json()
    except Exception:
        pytest.fail(
            "[GR_GETPAYS_SHAPE] La respuesta no es JSON válido. "
            f"Body crudo: {r.text}"
        )

    if isinstance(data, dict):
        msg = str(data.get("message", "")).lower()
        if "no hay pagos generados actualmente" in msg:
            pytest.skip(
                "[GR_GETPAYS_SHAPE] No hay pagos generados; "
                "no se puede validar estructura de la lista."
            )
        else:
            pytest.fail(
                "[GR_GETPAYS_SHAPE] Se esperaba una lista de pagos o el mensaje "
                "'No hay pagos generados actualmente.', pero vino: "
                f"{data!r}"
            )

    assert isinstance(data, list), (
        "[GR_GETPAYS_SHAPE] Se esperaba una lista de pagos."
    )
    assert data, (
        "[GR_GETPAYS_SHAPE] La lista de pagos vino vacía; "
        "esto contradice el caso de mensaje cuando no hay pagos."
    )

    payment = data[0]
    assert isinstance(payment, dict), (
        "[GR_GETPAYS_SHAPE] El primer elemento de la lista no es un objeto JSON."
    )

    required_keys = [
        "payment_id",
        "reservation_id",
        "amount",
        "currency",
        "payment_method",
        "status",
        "payment_date",
        "transaction_reference",
    ]

    missing = [k for k in required_keys if k not in payment]
    assert not missing, (
        "[GR_GETPAYS_SHAPE] Faltan campos requeridos en el pago: "
        f"{missing}. Pago: {payment}"
    )

    assert isinstance(payment["payment_id"], str) and payment["payment_id"]
    assert payment["payment_id"].startswith("PAY")

    assert isinstance(payment["reservation_id"], int)

    assert isinstance(payment["amount"], (int, float))

    assert payment["currency"] in ("USD", "CRC", "Dolares", "Colones")

    assert payment["payment_method"] in ("Tarjeta", "PayPal", "Transferencia")

    assert payment["status"] == "Pagado"

    assert isinstance(payment["payment_date"], str) and payment["payment_date"]
    assert isinstance(payment["transaction_reference"], str) and payment["transaction_reference"]
