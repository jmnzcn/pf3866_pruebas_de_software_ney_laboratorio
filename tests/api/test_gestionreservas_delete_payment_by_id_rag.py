"""
EXPERIMENTO_RAG_09_gestionreservas_delete_payment_by_id

Pruebas de contrato para el endpoint:
    DELETE /delete_payment_by_id/<string:payment_id>

Comportamiento esperado (según app.py en GestiónReservas):

- payment_id con formato inválido (no 'PAY' + 6 dígitos, case-insensitive):
    -> 400
    -> {"message": "El formato del payment_id es inválido. Debe ser como PAY123456"}

- payment_id válido pero que NO existe en `payments`:
    -> 404
    -> {"message": "No se encontró ningún pago con ID: <payment_id>"}

- Caso feliz: payment_id existente:
    -> 200
    -> {"message": "El pago con ID <payment_id> fue eliminado con éxito."}
"""

import os
import re
import requests
import pytest

# Base URL del microservicio GestiónReservas
BASE_URL_RESERVAS = os.getenv("GESTIONRESERVAS_BASE_URL", "http://localhost:5002")


def _delete_reservas(path: str, **kwargs) -> requests.Response:
    url = f"{BASE_URL_RESERVAS}{path}"
    return requests.delete(url, timeout=20, **kwargs)


def _get_reservas(path: str, **kwargs) -> requests.Response:
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
        r = _get_reservas("/get_all_fake_payments")
    except Exception:
        return None

    try:
        data = r.json()
    except Exception:
        return None

    # Caso "no hay pagos": {"message": "No hay pagos generados actualmente."}
    if isinstance(data, dict):
        msg = str(data.get("message", "")).lower()
        if "no hay pagos generados actualmente" in msg:
            return None
        return None

    if not isinstance(data, list) or not data:
        return None

    first = data[0]
    if isinstance(first, dict):
        pid = first.get("payment_id")
        if isinstance(pid, str) and re.match(r"^PAY\d{6}$", pid):
            return pid

    return None


def test_gestionreservas_delete_payment_by_id_formato_invalido_400():
    """
    payment_id con formato inválido (no 'PAY' + 6 dígitos, aún tras upper())
    -> 400.
    """
    # Ojo: el endpoint hace payment_id.strip().upper() antes de validar,
    # así que 'pay123456' se considera válido. Probamos casos que siguen
    # siendo inválidos incluso tras upper().
    invalid_ids = [
        "XYZ123",     # no empieza en PAY
        "123456",     # solo dígitos
        "PAY123",     # menos de 6 dígitos
        "PAY12345",   # menos de 6 dígitos
        "PAY1234567", # más de 6 dígitos
        "PAYABCDEF",  # parte numérica no son dígitos
    ]

    for bad_id in invalid_ids:
        r = _delete_reservas(f"/delete_payment_by_id/{bad_id}")

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
    candidate_id = "PAY999999"  # poco probable que exista

    r = _delete_reservas(f"/delete_payment_by_id/{candidate_id}")

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        resp_json = {}
        msg_text = r.text

    assert r.status_code == 404, (
        f"[GR_DELPAY_404] Se esperaba 404 para pago inexistente, "
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

    Pasos:
    1) Obtener un payment_id existente mediante GET /get_all_fake_payments.
    2) Llamar a DELETE /delete_payment_by_id/<payment_id>.
    3) Verificar:
       - status_code == 200
       - El mensaje indica que se eliminó el pago con ese ID.
    """
    pid = _find_existing_payment_id()
    if pid is None:
        pytest.skip(
            "[GR_DELPAY_OK] No se encontró ningún pago existente en "
            "/get_all_fake_payments; no se puede probar el caso feliz."
        )

    r = _delete_reservas(f"/delete_payment_by_id/{pid}")

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
