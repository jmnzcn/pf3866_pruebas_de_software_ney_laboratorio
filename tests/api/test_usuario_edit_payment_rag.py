"""
EXPERIMENTO_RAG_06_usuario_edit_payment

Pruebas de contrato para el endpoint:
    PUT /usuario/edit_payment/<payment_id>
"""

import os
import pytest
import requests


# Base URL del microservicio Usuario
BASE_URL = os.getenv("USUARIO_BASE_URL", "http://localhost:5003")


def _get(path: str, **kwargs) -> requests.Response:
    """Helper para enviar GET al microservicio Usuario."""
    url = f"{BASE_URL}{path}"
    return requests.get(url, timeout=20, **kwargs)


def _put(path: str, **kwargs) -> requests.Response:
    """Helper para enviar PUT al microservicio Usuario."""
    url = f"{BASE_URL}{path}"
    return requests.put(url, timeout=20, **kwargs)


def _find_any_payment():
    """
    Helper de caja negra:
    Obtiene algún pago existente usando /get_all_payments.
    Si no hay pagos válidos, hace skip del test.
    """
    r = _get("/get_all_payments")
    assert (
        r.status_code == 200
    ), f"[USR_EDIT_PAY_PRECOND] No se pudieron obtener pagos: {r.status_code} {r.text}"

    data = r.json()
    # El endpoint puede devolver:
    # - una lista de pagos
    # - o un dict con 'message' si no hay pagos
    if isinstance(data, dict) and "message" in data:
        pytest.skip(
            f"[USR_EDIT_PAY_PRECOND] No hay pagos disponibles: {data.get('message')}"
        )

    assert isinstance(data, list) and data, (
        "[USR_EDIT_PAY_PRECOND] Lista de pagos vacía o inválida: "
        f"{data}"
    )

    for p in data:
        if isinstance(p, dict) and p.get("payment_id"):
            return p

    pytest.skip(
        "[USR_EDIT_PAY_PRECOND] No se encontró ningún pago con payment_id válido."
    )


@pytest.mark.parametrize(
    "case_id, payment_id, body, expected_status, expected_msg_sub",
    [
        # Body vacío o ausente
        (
            "USR_EDIT_PAY_BODY_VACIO",
            "PAY123456",  # formato válido, pero no importa que exista
            None,
            400,
            "No se recibió cuerpo JSON",
        ),
        # payment_id inválido
        (
            "USR_EDIT_PAY_ID_INVALIDO",
            "ABC123",  # no cumple regex PAY\d{6}
            {"payment_method": "Tarjeta"},
            400,
            "El formato del payment_id es inválido. Debe ser PAY123456",
        ),
        # Body con campos extra no permitidos
        (
            "USR_EDIT_PAY_BODY_CAMPOS_EXTRA",
            "PAY123456",
            {
                "payment_method": "Tarjeta",
                "amount": 100.0,  # campo no permitido
            },
            400,
            "Solo se pueden actualizar: payment_method, payment_date, transaction_reference",
        ),
        # payment_id no existente en GestiónReservas
        (
            "USR_EDIT_PAY_NO_EXISTE",
            "PAY999999",  # formato válido, pero probablemente no existe
            {"payment_method": "Tarjeta"},
            404,
            "No se encontró",  # coincide con el mensaje real
        ),
    ],
)
def test_usuario_edit_payment_validaciones_y_404(
    case_id,
    payment_id,
    body,
    expected_status,
    expected_msg_sub,
):
    """
    Casos de error para /usuario/edit_payment/<payment_id>:

    - Body vacío o ausente -> 400.
    - payment_id con formato inválido -> 400.
    - Body con campos extra no permitidos -> 400.
    - payment_id no existente -> 404.
    """
    path = f"/usuario/edit_payment/{payment_id}"

    if body is None:
        # Enviar un JSON vacío para evitar 415 (Content-Type correcto)
        r = _put(path, json={})
    else:
        r = _put(path, json=body)

    # Intentar parsear el body como JSON, pero no romper si no lo es.
    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        resp_json = {}
        msg_text = r.text

    assert (
        r.status_code == expected_status
    ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"

    # Para los casos 400/404, al menos que aparezca el fragmento esperado
    msg_lower = (msg_text or "").lower()
    expected_lower = expected_msg_sub.lower()
    assert expected_lower in msg_lower, (
        f"[{case_id}] No se encontró el texto esperado en el mensaje. "
        f"Buscaba: '{expected_msg_sub}' en: '{msg_text}'"
    )


def test_usuario_edit_payment_happy_path():
    """
    Caso feliz: editar (actualizar) un pago existente.

    Pasos:
    1) Obtener un pago existente con /get_all_payments (helper _find_any_payment).
    2) Tomar su payment_id.
    3) Construir un body con al menos un campo permitido (p.ej. transaction_reference)
       con un valor claramente distinto.
    4) Hacer PUT /usuario/edit_payment/<payment_id>.
       - Esperado: 200.
       - Mensaje de éxito no vacío.
    """
    # 1) Obtener un pago existente
    pago = _find_any_payment()
    payment_id = pago["payment_id"]

    # 2) Preparar body de actualización
    old_ref = pago.get("transaction_reference") or ""
    new_ref = f"REF-ACT-{payment_id}"
    if new_ref == old_ref:
        new_ref = f"REF-ACT-ALT-{payment_id}"

    body = {
        "transaction_reference": new_ref,
    }

    # 3) Llamar al endpoint de Usuario
    r = _put(f"/usuario/edit_payment/{payment_id}", json=body)

    assert (
        r.status_code == 200
    ), f"[USR_EDIT_PAY_OK_01] Código inesperado en edit_payment: {r.status_code} {r.text}"

    # 4) Validaciones mínimas sobre el body
    try:
        resp_json = r.json()
    except Exception:
        pytest.fail(
            f"[USR_EDIT_PAY_OK_01] La respuesta no es JSON válido: {r.text}"
        )

    assert isinstance(resp_json, dict), (
        "[USR_EDIT_PAY_OK_01] La respuesta JSON no es un objeto (dict): "
        f"{type(resp_json)}"
    )

    msg = resp_json.get("message", "") or resp_json.get("status", "")
    assert msg, (
        "[USR_EDIT_PAY_OK_01] No se encontró un mensaje de éxito en la respuesta: "
        f"{resp_json}"
    )

    # Si el backend retorna un objeto 'payment', intentamos una aserción suave
    payment_obj = resp_json.get("payment")
    if isinstance(payment_obj, dict):
        nueva_ref_resp = payment_obj.get("transaction_reference", "")
        if nueva_ref_resp:
            assert (
                nueva_ref_resp == new_ref
            ), (
                "[USR_EDIT_PAY_OK_01] La transaction_reference devuelta no coincide "
                f"con la enviada. Esperado: {new_ref}, obtenido: {nueva_ref_resp}"
            )
