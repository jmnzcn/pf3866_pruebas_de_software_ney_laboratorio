"""
EXPERIMENTO_RAG_07_gestionreservas_get_all_fake_payments

Pruebas de contrato para el endpoint:
    GET /get_all_fake_payments

Comportamiento esperado (según app.py en GestiónReservas):

- Si NO hay pagos en memoria (lista payments vacía):
    -> 200
    -> body JSON: {"message": "No hay pagos generados actualmente."}

- Si SÍ hay pagos:
    -> 200
    -> body JSON: lista de pagos, cada elemento con al menos:
       - payment_id (str, formato PAYXXXXXX)
       - reservation_id (int)
       - amount (float)
       - currency (str, "USD" o "CRC")
       - payment_method (str, "Tarjeta" | "PayPal" | "Transferencia")
       - status (str, "Pagado")
       - payment_date (str)
       - transaction_reference (str)
    Además, como generate_fake_payments hace {**payment_info, **reserva},
    cada pago incluye también los campos de la reserva asociada.
"""

import os
import requests
import pytest

# Base URL del microservicio GestiónReservas
BASE_URL_RESERVAS = os.getenv("GESTIONRESERVAS_BASE_URL", "http://localhost:5002")


def _get_reservas(path: str, **kwargs) -> requests.Response:
    url = f"{BASE_URL_RESERVAS}{path}"
    return requests.get(url, timeout=20, **kwargs)


def test_gestionreservas_get_all_fake_payments_status_y_formato_basico():
    """
    Verifica el contrato básico de status + tipo de body para:

        GET /get_all_fake_payments

    Comportamiento válido:

    - status_code == 200 SIEMPRE.
    - Si no hay pagos -> body es dict con 'message' que contiene
      "No hay pagos generados actualmente."
    - Si hay pagos   -> body es una lista (posiblemente vacía, pero
      en la lógica actual del servicio, si no hay pagos se devuelve el mensaje,
      así que con lista se espera al menos un elemento).
    """
    r = _get_reservas("/get_all_fake_payments")

    # Debe ser siempre 200
    assert r.status_code == 200, (
        f"[GR_GETPAYS_STATUS] Código de estado inesperado: "
        f"{r.status_code} body={r.text}"
    )

    # Intentar parsear JSON; si falla, es un error de contrato
    try:
        data = r.json()
    except Exception:
        pytest.fail(
            "[GR_GETPAYS_STATUS] La respuesta no es JSON válido. "
            f"Body crudo: {r.text}"
        )

    if isinstance(data, dict):
        # Caso "no hay pagos"
        msg = str(data.get("message", "")).lower()
        assert "no hay pagos generados actualmente" in msg, (
            "[GR_GETPAYS_STATUS] Para dict se esperaba mensaje "
            "'No hay pagos generados actualmente.' "
            f"pero vino: {data!r}"
        )
    elif isinstance(data, list):
        # Caso "hay pagos": la estructura detallada se valida en otra prueba
        pass
    else:
        pytest.fail(
            "[GR_GETPAYS_STATUS] Tipo de body inesperado. "
            f"Se esperaba dict o list, pero vino: {type(data)}"
        )


def test_gestionreservas_get_all_fake_payments_estructura_cuando_hay_pagos():
    """
    Si el endpoint devuelve una lista de pagos (status 200 + body list),
    se valida la estructura básica de al menos uno de ellos.

    Si devuelve dict con mensaje "No hay pagos generados actualmente.",
    se hace skip de esta prueba (no hay datos que validar).
    """
    r = _get_reservas("/get_all_fake_payments")

    try:
        data = r.json()
    except Exception:
        pytest.fail(
            "[GR_GETPAYS_SHAPE] La respuesta no es JSON válido. "
            f"Body crudo: {r.text}"
        )

    # Si es dict con mensaje de "no hay pagos", se omite esta validación
    if isinstance(data, dict):
        msg = str(data.get("message", "")).lower()
        if "no hay pagos generados actualmente" in msg:
            pytest.skip("[GR_GETPAYS_SHAPE] No hay pagos generados; "
                        "no se puede validar estructura de la lista.")
        else:
            pytest.fail(
                "[GR_GETPAYS_SHAPE] Se esperaba una lista de pagos o el mensaje "
                "'No hay pagos generados actualmente.', pero vino: "
                f"{data!r}"
            )

    # A partir de aquí asumimos que data es una lista de pagos
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

    # Campos mínimos esperados (de la parte de pago)
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

    # Validaciones suaves de tipo/valor
    assert isinstance(payment["payment_id"], str) and payment["payment_id"], (
        "[GR_GETPAYS_SHAPE] payment_id debe ser string no vacío."
    )
    assert payment["payment_id"].startswith("PAY"), (
        "[GR_GETPAYS_SHAPE] payment_id debería empezar por 'PAY', "
        f"vino: {payment['payment_id']!r}"
    )

    assert isinstance(payment["reservation_id"], int), (
        "[GR_GETPAYS_SHAPE] reservation_id debe ser int."
    )

    # amount numérico (int o float)
    assert isinstance(payment["amount"], (int, float)), (
        "[GR_GETPAYS_SHAPE] amount debe ser numérico (int o float)."
    )

    assert payment["currency"] in ("USD", "CRC", "Dolares", "Colones"), (
        "[GR_GETPAYS_SHAPE] currency inesperada; se esperaban 'USD', 'CRC', "
        "'Dolares' o 'Colones', vino: "
        f"{payment['currency']!r}"
    )

    assert payment["payment_method"] in ("Tarjeta", "PayPal", "Transferencia"), (
        "[GR_GETPAYS_SHAPE] payment_method inesperado; "
        f"vino: {payment['payment_method']!r}"
    )

    assert payment["status"] == "Pagado", (
        "[GR_GETPAYS_SHAPE] status debe ser 'Pagado' para pagos generados, "
        f"vino: {payment['status']!r}"
    )

    assert isinstance(payment["payment_date"], str) and payment["payment_date"], (
        "[GR_GETPAYS_SHAPE] payment_date debe ser string no vacío."
    )
    assert isinstance(payment["transaction_reference"], str) and payment["transaction_reference"], (
        "[GR_GETPAYS_SHAPE] transaction_reference debe ser string no vacío."
    )
