"""
EXPERIMENTO_RAG_08_gestionreservas_get_payment_by_id

Pruebas de contrato para el endpoint:
    GET /get_payment_by_id/<string:payment_id>

Comportamiento esperado (según app.py en GestiónReservas):

- payment_id con formato inválido (no 'PAY' + 6 dígitos):
    -> 400
    -> {"message": "El formato del payment_id es inválido. Debe ser como PAY123456"}

- Estructura de pagos válida pero:
    - No hay pagos en memoria:
        -> 404
        -> {"message": "No hay pagos generados aún."}
    - Hay pagos, pero el ID no existe:
        -> 404
        -> {"message": "No se encontró ningún pago con ID: <...>"}

- Caso feliz:
    - payment_id de un pago existente:
        -> 200
        -> objeto JSON con los campos del pago.
"""

import os
import re
import requests
import pytest

# Base URL del microservicio GestiónReservas
BASE_URL_RESERVAS = os.getenv("GESTIONRESERVAS_BASE_URL", "http://localhost:5002")


def _get(path: str, **kwargs) -> requests.Response:
    url = f"{BASE_URL_RESERVAS}{path}"
    return requests.get(url, timeout=20, **kwargs)


def _find_existing_payment_id() -> str | None:
    """
    Intenta encontrar un payment_id existente llamando a:
        GET /get_all_fake_payments

    - Si devuelve lista y tiene elementos -> retorna el payment_id del primero.
    - Si devuelve dict con "no hay pagos generados" -> retorna None.
    - En cualquier caso raro -> retorna None.
    """
    try:
        r = _get("/get_all_fake_payments")
    except Exception:
        return None

    try:
        data = r.json()
    except Exception:
        return None

    # Caso "no hay pagos": {"message": "No hay pagos generados actualmente."}
    if isinstance(data, dict):
        msg = str(data.get("message", "")).lower()
        if "no hay pagos" in msg:
            return None
        return None

    if not isinstance(data, list) or not data:
        return None

    first = data[0]
    if isinstance(first, dict):
        pid = first.get("payment_id")
        if isinstance(pid, str) and pid.startswith("PAY"):
            return pid

    return None


def test_gestionreservas_get_payment_by_id_formato_invalido_400():
    """
    payment_id con formato inválido (no 'PAY' + 6 dígitos) -> 400.
    """
    # Algunos ejemplos inválidos (ojo: el servicio acepta PAY en minúsculas por .upper())
    invalid_ids = ["XYZ123", "PAY123", "123456", "PAYABCDEF"]

    for bad_id in invalid_ids:
        r = _get(f"/get_payment_by_id/{bad_id}")

        try:
            resp_json = r.json()
            msg_text = resp_json.get("message", "") or resp_json.get("error", "")
        except Exception:
            resp_json = {}
            msg_text = r.text

        assert (
            r.status_code == 400
        ), f"[GR_GETPAY_FMT_400] Para {bad_id!r} se esperaba 400, vino {r.status_code} {r.text}"

        assert "formato del payment_id es inválido" in msg_text.lower(), (
            f"[GR_GETPAY_FMT_400] Mensaje inesperado para {bad_id!r}. "
            f"message: {msg_text!r}"
        )


def test_gestionreservas_get_payment_by_id_no_existe_o_sin_pagos_404():
    """
    payment_id con formato válido pero que no existe.

    Dos comportamientos válidos según el estado interno de 'payments':

    - Si no hay pagos en memoria:
        -> 404
        -> message contiene "No hay pagos generados aún."

    - Si hay pagos, pero ese ID no existe:
        -> 404
        -> message contiene "No se encontró ningún pago con ID:"
    """
    candidate_id = "PAY999999"  # ID poco probable que exista
    r = _get(f"/get_payment_by_id/{candidate_id}")

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        resp_json = {}
        msg_text = r.text

    assert r.status_code == 404, (
        f"[GR_GETPAY_404] Se esperaba 404 para un pago inexistente, "
        f"vino {r.status_code} {r.text}"
    )

    msg_lower = msg_text.lower()

    # Aceptamos cualquiera de los dos mensajes válidos:
    if "no hay pagos generados aún" in msg_lower:
        # Caso: lista de pagos vacía
        assert True
    elif "no se encontró ningún pago con id" in msg_lower:
        # Caso: hay pagos, pero ese ID no existe
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

    Pasos:
    1) Obtener un payment_id existente mediante GET /get_all_fake_payments.
    2) Llamar a GET /get_payment_by_id/<payment_id>.
    3) Verificar:
       - status_code == 200
       - JSON es un dict con los campos básicos del pago
       - payment_id coincide con el solicitado y tiene el formato PAYxxxxxx
    """
    pid = _find_existing_payment_id()
    if pid is None:
        pytest.skip(
            "[GR_GETPAY_OK] No se encontró ningún pago existente en "
            "/get_all_fake_payments; no se puede probar el caso feliz."
        )

    r = _get(f"/get_payment_by_id/{pid}")

    assert (
        r.status_code == 200
    ), f"[GR_GETPAY_OK] Se esperaba 200 al consultar {pid}, vino {r.status_code} {r.text}"

    try:
        pago = r.json()
    except Exception:
        pytest.fail(
            f"[GR_GETPAY_OK] La respuesta no es JSON válido. Body crudo: {r.text}"
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

    # Campos mínimos esperados
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

    assert isinstance(pago["reservation_id"], int), (
        "[GR_GETPAY_OK] reservation_id debe ser int."
    )
    assert isinstance(pago["amount"], (int, float)), (
        "[GR_GETPAY_OK] amount debe ser numérico."
    )
    assert isinstance(pago["payment_date"], str) and pago["payment_date"], (
        "[GR_GETPAY_OK] payment_date debe ser string no vacío."
    )
    assert isinstance(pago["transaction_reference"], str) and pago["transaction_reference"], (
        "[GR_GETPAY_OK] transaction_reference debe ser string no vacío."
    )

    # status del pago
    assert pago["status"] == "Pagado", (
        "[GR_GETPAY_OK] status esperado 'Pagado', vino: "
        f"{pago['status']!r}"
    )
