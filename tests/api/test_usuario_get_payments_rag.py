"""
EXPERIMENTO_RAG_09_usuario_get_payments

Pruebas de contrato para los endpoints de consulta de pagos del
microservicio Usuario:

    GET /get_payment_by_id/<string:payment_id>
    GET /get_all_payments

Casos cubiertos:

- payment_id con formato inválido -> 400.
- payment_id inexistente -> 404.
- Caso feliz por ID -> 200.
- Contrato general de /get_all_payments -> 200 (mensaje o lista).
"""

import os
import requests
import pytest

# Base URL del microservicio Usuario
BASE_URL = os.getenv("USUARIO_BASE_URL", "http://localhost:5003")


def _get(path: str, **kwargs) -> requests.Response:
    url = f"{BASE_URL}{path}"
    return requests.get(url, **kwargs)


def _get_any_payment():
    """
    Devuelve un pago cualquiera obtenido desde:

        GET /get_all_payments

    Si no hay pagos (o la respuesta no es una lista válida),
    retorna None para que el test feliz haga pytest.skip.
    """
    r = _get("/get_all_payments")
    if r.status_code != 200:
        return None

    try:
        data = r.json()
    except Exception:
        return None

    # Caso: no hay pagos -> dict con {"message": "No hay pagos generados actualmente."}
    if isinstance(data, dict):
        msg = str(data.get("message", "")).lower()
        if "no hay pagos generados actualmente" in msg:
            return None
        return None

    # Caso: lista de pagos
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict) and "payment_id" in first:
            return first

    return None


# ---------------------------------------------------------------------------
# GET /get_payment_by_id/<string:payment_id>
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "case_id, path, expected_status, expected_msg_sub",
    [
        (
            "USR_PAY_GET_ID_FORMATO_INVALIDO_400",
            "/get_payment_by_id/ABC123",
            400,
            "El formato del payment_id es inválido. Debe ser como PAY123456",
        ),
        (
            "USR_PAY_GET_ID_NO_EXISTE_404",
            "/get_payment_by_id/PAY999999",
            404,
            "No se encontró ningún pago con ID: PAY999999",
        ),
    ],
)
def test_usuario_get_payment_by_id_validaciones_y_404(
    case_id,
    path,
    expected_status,
    expected_msg_sub,
):
    """
    Casos de error para:
        GET /get_payment_by_id/<string:payment_id>

    - payment_id con formato inválido -> 400.
    - payment_id bien formado pero inexistente -> 404.
    """
    r = _get(path)

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        resp_json = {}
        msg_text = r.text

    assert (
        r.status_code == expected_status
    ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"

    assert expected_msg_sub.lower() in msg_text.lower(), (
        f"[{case_id}] No se encontró el texto esperado en el mensaje. "
        f"Buscaba: '{expected_msg_sub}' en: '{msg_text}'"
    )


def test_usuario_get_payment_by_id_happy_path():
    """
    Caso feliz para:
        GET /get_payment_by_id/<string:payment_id>

    Pasos:
    1) Obtener cualquier pago existente usando /get_all_payments.
    2) Tomar su payment_id.
    3) Invocar /get_payment_by_id/<payment_id>.
    4) Verificar que:
       - Devuelva 200.
       - La respuesta sea un dict.
       - El payment_id devuelto coincida.
    """
    pago = _get_any_payment()
    if pago is None:
        pytest.skip(
            "[USR_PAY_GET_ID_OK_200] No se encontró ningún pago en /get_all_payments."
        )

    pid = pago.get("payment_id")
    assert pid, (
        "[USR_PAY_GET_ID_OK_200] El pago obtenido no tiene payment_id válido: "
        f"{pago}"
    )

    r = _get(f"/get_payment_by_id/{pid}")

    assert (
        r.status_code == 200
    ), f"[USR_PAY_GET_ID_OK_200] Código inesperado: {r.status_code} {r.text}"

    resp_json = r.json()
    assert isinstance(resp_json, dict), (
        "[USR_PAY_GET_ID_OK_200] La respuesta no es un objeto JSON: "
        f"{resp_json}"
    )

    assert resp_json.get("payment_id") == pid, (
        "[USR_PAY_GET_ID_OK_200] El payment_id devuelto no coincide con el solicitado. "
        f"Esperado: {pid}, recibido: {resp_json.get('payment_id')}"
    )


# ---------------------------------------------------------------------------
# GET /get_all_payments
# ---------------------------------------------------------------------------

def test_usuario_get_all_payments_contract():
    """
    Contrato general para:
        GET /get_all_payments

    Se espera:
    - status_code == 200
    - Cuerpo JSON que sea:
        a) dict con {"message": "No hay pagos generados actualmente."}, o
        b) lista de pagos (cada uno con payment_id y campos clave).
    """
    r = _get("/get_all_payments")

    assert (
        r.status_code == 200
    ), f"[USR_PAY_ALL_CONTRACT] Código inesperado: {r.status_code} {r.text}"

    try:
        data = r.json()
    except Exception:
        pytest.fail(
            f"[USR_PAY_ALL_CONTRACT] La respuesta no es JSON válido: {r.text[:200]}"
        )

    if isinstance(data, dict):
        # Caso "no hay pagos"
        msg = str(data.get("message", "")).lower()
        assert "no hay pagos generados actualmente" in msg, (
            "[USR_PAY_ALL_CONTRACT] Se esperaba un mensaje indicando que no hay "
            f"pagos generados actualmente. Mensaje recibido: {data}"
        )
    elif isinstance(data, list):
        # Caso lista de pagos
        assert data, (
            "[USR_PAY_ALL_CONTRACT] Se recibió una lista vacía; según el contrato "
            "Usuario debería devolver un mensaje cuando no hay pagos."
        )

        first = data[0]
        assert isinstance(first, dict), (
            "[USR_PAY_ALL_CONTRACT] El primer elemento de la lista no es un objeto JSON: "
            f"{first}"
        )

        # Validación mínima de campos clave
        assert "payment_id" in first, (
            "[USR_PAY_ALL_CONTRACT] Falta 'payment_id' en el pago: "
            f"{first}"
        )
        assert "reservation_id" in first, (
            "[USR_PAY_ALL_CONTRACT] Falta 'reservation_id' en el pago: "
            f"{first}"
        )
        assert "amount" in first, (
            "[USR_PAY_ALL_CONTRACT] Falta 'amount' en el pago: "
            f"{first}"
        )
        assert "currency" in first, (
            "[USR_PAY_ALL_CONTRACT] Falta 'currency' en el pago: "
            f"{first}"
        )
        assert "payment_method" in first, (
            "[USR_PAY_ALL_CONTRACT] Falta 'payment_method' en el pago: "
            f"{first}"
        )
    else:
        pytest.fail(
            "[USR_PAY_ALL_CONTRACT] La respuesta no es ni dict ni list. "
            f"Tipo recibido: {type(data)}"
        )
