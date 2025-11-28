"""
EXPERIMENTO_RAG_12_gestionreservas_edit_payment

Pruebas de contrato para el endpoint:
    PUT /edit_payment/<string:payment_id>

Casos cubiertos (según app.py de GestiónReservas):

- payment_id con formato inválido -> 400.
- payment_id válido pero inexistente -> 404.
- Body ausente / sin JSON (sin Content-Type application/json) -> 415 (Flask).
- payment_method inválido -> 400.
- Caso feliz: edición exitosa de un pago existente -> 200.
"""

import os
import re
import requests
import pytest

# Base URL del microservicio GestiónReservas
BASE_URL_RESERVAS = os.getenv("GESTIONRESERVAS_BASE_URL", "http://localhost:5002")


def _get_reservas(path: str, **kwargs) -> requests.Response:
    url = f"{BASE_URL_RESERVAS}{path}"
    return requests.get(url, timeout=20, **kwargs)


def _put_reservas(path: str, **kwargs) -> requests.Response:
    url = f"{BASE_URL_RESERVAS}{path}"
    return requests.put(url, timeout=20, **kwargs)


def _find_any_payment() -> dict | None:
    """
    Devuelve cualquier pago existente de /get_all_fake_payments
    o None si no hay pagos válidos.
    """
    try:
        r = _get_reservas("/get_all_fake_payments")
    except Exception:
        return None

    if r.status_code != 200:
        return None

    try:
        data = r.json()
    except Exception:
        return None

    if not isinstance(data, list):
        return None

    for p in data:
        if not isinstance(p, dict):
            continue
        pid = p.get("payment_id")
        if isinstance(pid, str) and re.match(r"^PAY\d{6}$", pid):
            return p

    return None


BASE_VALID_BODY = {
    "payment_method": "Tarjeta",
    "payment_date": "Abril 25, 2025 - 17:00:00",
    "transaction_reference": "XYZ123ABC456",
}


@pytest.mark.parametrize(
    "case_id, payment_id, body, expected_status, expected_msg_sub, expect_415",
    [
        # Formato inválido -> 400
        (
            "GR_EDITPAY_FMT_400",
            "ABC",  # no 'PAY' + 6 dígitos
            BASE_VALID_BODY,
            400,
            "formato del payment_id es inválido",
            False,
        ),
        # payment_id válido pero no existente -> 404
        (
            "GR_EDITPAY_NO_EXISTE_404",
            "PAY999999",
            BASE_VALID_BODY,
            404,
            "no se encontró el pago con id",
            False,
        ),
        # Body ausente / sin JSON -> en la práctica Flask devuelve 415
        (
            "GR_EDITPAY_BODY_AUSENTE_415",
            "REAL_FROM_FIXTURE",  # se reemplaza por uno real
            None,
            415,
            "unsupported media type",
            True,
        ),
        # Método de pago inválido -> 400
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

    - Código mal formado -> 400.
    - Pago no existente -> 404.
    - Body ausente / no JSON -> 415 (Flask).
    - payment_method inválido -> 400.
    """
    # Resolver marcador "REAL_FROM_FIXTURE" usando un pago real
    if payment_id == "REAL_FROM_FIXTURE":
        pago = _find_any_payment()
        if pago is None:
            pytest.skip(f"[{case_id}] No se encontró ningún pago en el sistema.")
        payment_id = pago.get("payment_id")
        assert payment_id, f"[{case_id}] El pago encontrado no tiene payment_id."

    path = f"/edit_payment/{payment_id}"

    if body is None:
        # Sin body JSON => Flask suele devolver 415 Unsupported Media Type
        r = _put_reservas(path)
    else:
        r = _put_reservas(path, json=body)

    # Intentar parsear JSON; en 415 es HTML, así que puede fallar
    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        resp_json = {}
        msg_text = r.text

    # Código de estado
    assert (
        r.status_code == expected_status
    ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"

    # Mensaje esperado (substring, case-insensitive)
    msg_lower = msg_text.lower()

    if expect_415:
        # Para 415 basta con detectar "unsupported media type"
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

    Pasos:
    1) Tomar un payment_id existente desde /get_all_fake_payments.
    2) Enviar PUT /edit_payment/<payment_id> con body con nuevos valores.
    3) Verificar:
       - 200
       - message contiene "Pago actualizado correctamente"
       - payment.payment_id == solicitado
       - Campos actualizados en la respuesta.
    """
    pago = _find_any_payment()
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

    r = _put_reservas(f"/edit_payment/{payment_id}", json=body)

    assert (
        r.status_code == 200
    ), f"[GR_EDITPAY_OK] Código inesperado al editar pago: {r.status_code} {r.text}"

    try:
        resp_json = r.json()
    except Exception:
        pytest.fail(
            f"[GR_EDITPAY_OK] La respuesta no es JSON válido. Body crudo: {r.text}"
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

    # Verificar que los campos fueron actualizados
    assert payment.get("payment_method") == nuevo_metodo, (
        "[GR_EDITPAY_OK] payment_method no fue actualizado correctamente."
    )
    assert payment.get("payment_date") == nueva_fecha, (
        "[GR_EDITPAY_OK] payment_date no fue actualizado correctamente."
    )
    assert payment.get("transaction_reference") == nueva_ref, (
        "[GR_EDITPAY_OK] transaction_reference no fue actualizado correctamente."
    )
