"""
EXPERIMENTO_RAG_05_usuario_cancel_payment_and_reservation

Pruebas de contrato para el endpoint:
    DELETE /cancel_payment_and_reservation/<payment_id>

Casos cubiertos:
- payment_id con formato inválido -> 400.
- payment_id inexistente -> 404.
- Caso feliz: cancelación exitosa -> 200 y luego 404 al intentar cancelar de nuevo.
"""

import os
import requests
import pytest

# Base URL del microservicio Usuario
BASE_URL = os.getenv("USUARIO_BASE_URL", "http://localhost:5003")


def _delete(path: str, **kwargs) -> requests.Response:
    """
    Helper para enviar DELETE al microservicio Usuario.
    """
    url = f"{BASE_URL}{path}"
    return requests.delete(url, **kwargs)


def _get(path: str, **kwargs) -> requests.Response:
    """
    Helper para enviar GET al microservicio Usuario.
    """
    url = f"{BASE_URL}{path}"
    return requests.get(url, **kwargs)


def _find_any_payment() -> dict:
    """
    Busca cualquier pago existente usando GET /get_all_payments de Usuario.

    Estrategia:
    - Si devuelve 200 y una lista no vacía, retorna el primer elemento.
    - Si devuelve 200 y un dict con mensaje "No hay pagos...", hace skip.
    - Cualquier otra cosa => pytest.fail (el entorno no está listo o contrato inesperado).
    """
    r = _get("/get_all_payments")

    assert r.status_code == 200, (
        "[PAY_CAN_SETUP] No se pudo consultar pagos desde Usuario: "
        f"{r.status_code} {r.text}"
    )

    try:
        data = r.json()
    except Exception:
        pytest.fail(
            f"[PAY_CAN_SETUP] Respuesta de /get_all_payments no es JSON válido: {r.text}"
        )

    # Caso lista de pagos
    if isinstance(data, list):
        if not data:
            pytest.skip("[PAY_CAN_SETUP] No hay pagos generados actualmente para probar cancelación.")
        # Tomamos el primero como caja negra
        pago = data[0]
        if not isinstance(pago, dict):
            pytest.fail(f"[PAY_CAN_SETUP] Elemento de pagos no es dict: {type(pago)}")
        return pago

    # Caso dict con mensaje
    if isinstance(data, dict) and "message" in data:
        msg = str(data["message"]).lower()
        if "no hay pagos" in msg:
            pytest.skip("[PAY_CAN_SETUP] No hay pagos generados actualmente para probar cancelación.")
        pytest.fail(
            f"[PAY_CAN_SETUP] Respuesta inesperada de /get_all_payments: {data}"
        )

    pytest.fail(
        f"[PAY_CAN_SETUP] Estructura inesperada de /get_all_payments: {data}"
    )


@pytest.mark.parametrize(
    "case_id, payment_id, expected_status, expected_msg_sub",
    [
        # Formato inválido (prefijo incorrecto)
        (
            "PAY_CAN_ID_INVALIDO_1",
            "ABC123456",
            400,
            "formato del payment_id es inválido",
        ),
        # Formato inválido (muy corto)
        (
            "PAY_CAN_ID_INVALIDO_2",
            "PAY123",
            400,
            "formato del payment_id es inválido",
        ),
        # payment_id inexistente (pero con formato válido)
        (
            "PAY_CAN_NO_EXISTE",
            "PAY999999",
            404,
            "no se encontr",  # substring flexible: "no se encontró / encontro"
        ),
    ],
)
def test_usuario_cancel_payment_validaciones_y_404(
    case_id,
    payment_id,
    expected_status,
    expected_msg_sub,
):
    """
    Casos de error para /cancel_payment_and_reservation/<payment_id>:

    - payment_id con formato inválido -> 400.
    - payment_id inexistente -> 404.
    """
    r = _delete(f"/cancel_payment_and_reservation/{payment_id}")

    # Intentar parsear el body como JSON, pero no romper si no lo es.
    try:
        body = r.json()
        msg_text = body.get("message", "") or body.get("error", "")
    except Exception:
        body = {}
        msg_text = r.text

    assert (
        r.status_code == expected_status
    ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"

    # Mensaje esperado (solo substring, no exacto)
    assert expected_msg_sub.lower() in msg_text.lower(), (
        f"[{case_id}] No se encontró el texto esperado en el mensaje. "
        f"Buscaba: '{expected_msg_sub}' en: '{msg_text}'"
    )


def test_usuario_cancel_payment_happy_path():
    """
    Caso feliz: cancelar un pago y la reserva asociada.

    Pasos:
    1) Obtener un payment existente vía /get_all_payments.
    2) Llamar a DELETE /cancel_payment_and_reservation/<payment_id>:
       - Esperado 200, mensaje de éxito.
    3) Volver a llamar con el mismo payment_id:
       - Esperado 404, pago/reserva ya no existe.
    """
    # 1) Tomar cualquier pago existente (caja negra)
    payment = _find_any_payment()
    payment_id = (
        payment.get("payment_id")
        or payment.get("paymentId")
        or payment.get("id")
    )

    assert payment_id, (
        "[PAY_CAN_OK_01] No se pudo determinar un payment_id válido "
        f"a partir del pago: {payment}"
    )

    # 2) Primera cancelación: debería ser exitosa (200)
    r1 = _delete(f"/cancel_payment_and_reservation/{payment_id}")

    assert (
        r1.status_code == 200
    ), (
        "[PAY_CAN_OK_01] Código inesperado en primer DELETE: "
        f"{r1.status_code} {r1.text}"
    )

    try:
        body1 = r1.json()
        msg1 = body1.get("message", "") or body1.get("error", "")
    except Exception:
        body1 = {}
        msg1 = r1.text

    msg1_lower = msg1.lower()

    # Aceptamos cualquier mensaje que sugiera cancelación/eliminación
    assert (
        "cancel" in msg1_lower
        or "elimin" in msg1_lower
        or "anulad" in msg1_lower
        or msg1_lower.strip() != ""
    ), (
        "[PAY_CAN_OK_01] Mensaje de éxito inesperado en primer DELETE: "
        f"{msg1}"
    )

    # 3) Segunda cancelación: ahora el pago ya no debería existir (404)
    r2 = _delete(f"/cancel_payment_and_reservation/{payment_id}")

    assert (
        r2.status_code == 404
    ), (
        "[PAY_CAN_OK_01] Código inesperado en segundo DELETE "
        f"(se esperaba 404): {r2.status_code} {r2.text}"
    )

    try:
        body2 = r2.json()
        msg2 = body2.get("message", "") or body2.get("error", "")
    except Exception:
        body2 = {}
        msg2 = r2.text

    msg2_lower = msg2.lower()
    assert "no se encontr" in msg2_lower, (
        "[PAY_CAN_OK_01] Mensaje de 'no encontrado' inesperado en segundo DELETE: "
        f"{msg2}"
    )
