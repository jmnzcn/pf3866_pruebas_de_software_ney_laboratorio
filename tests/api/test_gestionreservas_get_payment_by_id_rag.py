"""
EXPERIMENTO_RAG_08_gestionreservas_get_payment_by_id

Pruebas de contrato para el endpoint:
    GET /get_payment_by_id/<string:payment_id>
"""

import re
import pytest

from gestionreservas_common import (
    get_reservas,
    find_existing_payment_with_full_data,
)


def _find_existing_payment_id() -> str | None:
    pago = find_existing_payment_with_full_data()
    if not pago:
        return None
    pid = pago.get("payment_id")
    if isinstance(pid, str) and pid.startswith("PAY"):
        return pid
    return None


@pytest.mark.parametrize(
    "case_id, payment_id",
    [
        ("GR_GETPAY_FMT_400_XYZ123", "XYZ123"),
        ("GR_GETPAY_FMT_400_PAY123", "PAY123"),
        ("GR_GETPAY_FMT_400_123456", "123456"),
        ("GR_GETPAY_FMT_400_PAYABCDEF", "PAYABCDEF"),
    ],
)
def test_gestionreservas_get_payment_by_id_formato_invalido_400(case_id, payment_id):
    """
    payment_id con formato inválido (no 'PAY' + 6 dígitos) -> 400.
    """
    r = get_reservas(f"/get_payment_by_id/{payment_id}")

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        resp_json = {}
        msg_text = r.text

    assert (
        r.status_code == 400
    ), f"[{case_id}] Para {payment_id!r} se esperaba 400, vino {r.status_code} {r.text}"

    assert "formato del payment_id es inválido" in msg_text.lower(), (
        f"[{case_id}] Mensaje inesperado para {payment_id!r}. "
        f"message: {msg_text!r}"
    )


def test_gestionreservas_get_payment_by_id_no_existe_o_sin_pagos_404():
    """
    payment_id con formato válido pero que no existe.

    Dos comportamientos válidos según el estado interno de 'payments':
    - No hay pagos -> 404 + "No hay pagos generados aún."
    - Hay pagos pero ese ID no existe -> 404 + "No se encontró ningún pago con ID:"
    """
    candidate_id = "PAY999999"
    r = get_reservas(f"/get_payment_by_id/{candidate_id}")

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        resp_json = {}
        msg_text = r.text

    assert r.status_code == 404, (
        "[GR_GETPAY_404] Se esperaba 404 para un pago inexistente, "
        f"vino {r.status_code} {r.text}"
    )

    msg_lower = msg_text.lower()

    if "no hay pagos generados aún" in msg_lower:
        assert True
    elif "no se encontró ningún pago con id" in msg_lower:
        assert True
    else:
        pytest.fail(
            "[GR_GETPAY_404] Mensaje inesperado para 404. "
            f"message: {msg_text!r}"
        )


def test_gestionreservas_get_payment_by_id_happy_path():
    """
    Caso feliz:
        Consultar un payment_id que sí existe.
    """
    pid = _find_existing_payment_id()
    if pid is None:
        pytest.skip(
            "[GR_GETPAY_OK] No se encontró ningún pago existente en "
            "/get_all_fake_payments; no se puede probar el caso feliz."
        )

    r = get_reservas(f"/get_payment_by_id/{pid}")

    assert (
        r.status_code == 200
    ), f"[GR_GETPAY_OK] Se esperaba 200 al consultar {pid}, vino {r.status_code} {r.text}"

    try:
        pago = r.json()
    except Exception:
        pytest.fail(
            "[GR_GETPAY_OK] La respuesta no es JSON válido. "
            f"Body crudo: {r.text}"
        )

    assert isinstance(pago, dict), (
        "[GR_GETPAY_OK] Se esperaba un objeto JSON (dict) como pago."
    )

    payment_id = pago.get("payment_id")
    assert payment_id == pid, (
        "[GR_GETPAY_OK] payment_id en la respuesta no coincide con el solicitado. "
        f"pid_solicitado={pid!r}, pid_respuesta={payment_id!r}"
    )

    assert isinstance(payment_id, str) and re.match(r"^PAY\d{6}$", payment_id), (
        "[GR_GETPAY_OK] payment_id no cumple el formato PAYxxxxxx. "
        f"payment_id={payment_id!r}"
    )

    required_keys = [
        "reservation_id",
        "amount",
        "currency",
        "payment_method",
        "status",
        "payment_date",
        "transaction_reference",
    ]

    missing = [k for k in required_keys if k not in pago]
    assert not missing, (
        "[GR_GETPAY_OK] Faltan campos mínimos en el pago: "
        f"{missing}. Pago completo: {pago}"
    )

    assert isinstance(pago["reservation_id"], int)
    assert isinstance(pago["amount"], (int, float))
    assert isinstance(pago["payment_date"], str) and pago["payment_date"]
    assert isinstance(pago["transaction_reference"], str) and pago["transaction_reference"]

    assert pago["status"] == "Pagado"
