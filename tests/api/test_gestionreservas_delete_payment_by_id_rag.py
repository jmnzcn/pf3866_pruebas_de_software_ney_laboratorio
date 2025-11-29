"""
EXPERIMENTO_RAG_09_gestionreservas_delete_payment_by_id

Pruebas de contrato para el endpoint:
    DELETE /delete_payment_by_id/<string:payment_id>
"""

import pytest

from gestionreservas_common import (
    delete_reservas,
    find_existing_payment_with_full_data,
)


def test_gestionreservas_delete_payment_by_id_formato_invalido_400():
    """
    payment_id con formato inválido (no 'PAY' + 6 dígitos, aún tras upper())
    -> 400.
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
        r = delete_reservas(f"/delete_payment_by_id/{bad_id}")

        try:
            resp_json = r.json()
            msg_text = resp_json.get("message", "") or resp_json.get("error", "")
        except Exception:
            resp_json = {}
            msg_text = r.text

        assert (
            r.status_code == 400
        ), f"[GR_DELPAY_FMT_400] Para {bad_id!r} se esperaba 400, vino {r.status_code} {r.text}"

        assert "formato del payment_id es inválido" in msg_text.lower(), (
            f"[GR_DELPAY_FMT_400] Mensaje inesperado para {bad_id!r}. "
            f"message: {msg_text!r}"
        )


def test_gestionreservas_delete_payment_by_id_no_existe_404():
    """
    payment_id con formato válido pero que no existe en la lista `payments`
    -> 404 con mensaje "No se encontró ningún pago con ID: ...".
    """
    candidate_id = "PAY999999"

    r = delete_reservas(f"/delete_payment_by_id/{candidate_id}")

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        resp_json = {}
        msg_text = r.text

    assert r.status_code == 404, (
        "[GR_DELPAY_404] Se esperaba 404 para pago inexistente, "
        f"vino {r.status_code} {r.text}"
    )

    assert "no se encontró ningún pago con id" in msg_text.lower(), (
        "[GR_DELPAY_404] Mensaje inesperado para 404. "
        f"message: {msg_text!r}"
    )


def test_gestionreservas_delete_payment_by_id_happy_path():
    """
    Caso feliz:
        Eliminar un pago existente.
    """
    pago = find_existing_payment_with_full_data()
    if pago is None:
        pytest.skip(
            "[GR_DELPAY_OK] No se encontró ningún pago existente en "
            "/get_all_fake_payments; no se puede probar el caso feliz."
        )

    pid = pago["payment_id"]

    r = delete_reservas(f"/delete_payment_by_id/{pid}")

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        resp_json = {}
        msg_text = r.text

    assert (
        r.status_code == 200
    ), f"[GR_DELPAY_OK] Se esperaba 200 al eliminar {pid}, vino {r.status_code} {r.text}"

    msg_lower = msg_text.lower()
    assert "fue eliminado con éxito" in msg_lower, (
        "[GR_DELPAY_OK] El mensaje de éxito no contiene "
        "'fue eliminado con éxito'. "
        f"message: {msg_text!r}"
    )
    assert pid in msg_text, (
        "[GR_DELPAY_OK] El mensaje de éxito no incluye el ID del pago. "
        f"payment_id={pid!r}, message={msg_text!r}"
    )
