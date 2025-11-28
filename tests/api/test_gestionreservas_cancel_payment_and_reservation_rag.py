"""
EXPERIMENTO_RAG_11_gestionreservas_cancel_payment_and_reservation

Pruebas de contrato para el endpoint:
    DELETE /cancel_payment_and_reservation/<string:payment_id>

Comportamiento esperado (según app.py en GestiónReservas):

- payment_id con formato inválido (no 'PAY' + 6 dígitos, tras aplicar .strip().upper()):
    -> 400
    -> {"message": "El formato del payment_id es inválido. Debe ser como PAY123456"}

- payment_id válido pero que NO existe en `payments`:
    -> 404
    -> {"message": "No se encontró el pago con ID: <payment_id>"}

- Caso feliz: payment_id existente con datos completos:
    -> 200
    -> {
         "message": "Cancelación exitosa: pago y reserva eliminados, asiento liberado.",
         "deleted_payment": {...},
         "deleted_reservation": {...}
       }
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


def _delete_reservas(path: str, **kwargs) -> requests.Response:
    url = f"{BASE_URL_RESERVAS}{path}"
    return requests.delete(url, timeout=20, **kwargs)


def _find_existing_payment_with_full_data() -> dict | None:
    """
    Retorna un pago existente con los campos mínimos necesarios
    para que /cancel_payment_and_reservation funcione:

        - payment_id (formato PAYxxxxxx)
        - reservation_id (int)
        - airplane_id
        - seat_number

    Si no encuentra, retorna None.
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
        rid = p.get("reservation_id")
        aid = p.get("airplane_id")
        seat = p.get("seat_number")
        if (
            isinstance(pid, str)
            and re.match(r"^PAY\d{6}$", pid)
            and isinstance(rid, int)
            and aid is not None
            and isinstance(seat, str)
        ):
            return p

    return None


def test_gestionreservas_cancel_payment_and_reservation_formato_invalido_400():
    """
    payment_id con formato inválido (no 'PAY' + 6 dígitos, aún tras .upper()) -> 400.
    """
    # Ojo: el endpoint hace payment_id.strip().upper() antes de validar,
    # así que 'pay123456' se considera válido.
    invalid_ids = [
        "XYZ123",      # no empieza en PAY
        "123456",      # solo dígitos
        "PAY123",      # menos de 6 dígitos
        "PAY12345",    # menos de 6 dígitos
        "PAY1234567",  # más de 6 dígitos
        "PAYABCDEF",   # la parte numérica no son dígitos
    ]

    for bad_id in invalid_ids:
        r = _delete_reservas(f"/cancel_payment_and_reservation/{bad_id}")

        try:
            resp_json = r.json()
            msg_text = resp_json.get("message", "") or resp_json.get("error", "")
        except Exception:
            resp_json = {}
            msg_text = r.text

        assert (
            r.status_code == 400
        ), f"[GR_CANPAY_FMT_400] Para {bad_id!r} se esperaba 400, vino {r.status_code} {r.text}"

        assert "formato del payment_id es inválido" in msg_text.lower(), (
            f"[GR_CANPAY_FMT_400] Mensaje inesperado para {bad_id!r}. "
            f"message: {msg_text!r}"
        )


def test_gestionreservas_cancel_payment_and_reservation_no_existe_404():
    """
    payment_id con formato válido pero que no existe en `payments` -> 404.
    """
    candidate_id = "PAY999999"  # ID poco probable que exista

    r = _delete_reservas(f"/cancel_payment_and_reservation/{candidate_id}")

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        resp_json = {}
        msg_text = r.text

    assert r.status_code == 404, (
        f"[GR_CANPAY_404] Se esperaba 404 para pago inexistente, "
        f"vino {r.status_code} {r.text}"
    )

    assert "no se encontró el pago con id" in msg_text.lower(), (
        "[GR_CANPAY_404] Mensaje inesperado para 404. "
        f"message: {msg_text!r}"
    )


def test_gestionreservas_cancel_payment_and_reservation_happy_path():
    """
    Caso feliz:
        Cancelar un pago y su reserva asociada, liberando el asiento.

    Pasos:
    1) Buscar un pago existente con datos completos (helper).
    2) DELETE /cancel_payment_and_reservation/<payment_id>.
    3) Verificar:
       - status_code == 200
       - message contiene "cancelación exitosa"
       - deleted_payment.payment_id == solicitado
       - deleted_reservation.reservation_id == reservation_id del pago
    4) Verificar opcionalmente que el pago y la reserva ya no existan.
    """
    pago = _find_existing_payment_with_full_data()
    if pago is None:
        pytest.skip(
            "[GR_CANPAY_OK] No se encontró ningún pago existente con datos completos; "
            "no se puede probar el caso feliz."
        )

    payment_id = pago["payment_id"]
    reservation_id = pago["reservation_id"]

    r = _delete_reservas(f"/cancel_payment_and_reservation/{payment_id}")

    assert (
        r.status_code == 200
    ), f"[GR_CANPAY_OK] Se esperaba 200 al cancelar {payment_id}, vino {r.status_code} {r.text}"

    try:
        resp_json = r.json()
    except Exception:
        pytest.fail(
            f"[GR_CANPAY_OK] La respuesta no es JSON válido. Body crudo: {r.text}"
        )

    assert isinstance(resp_json, dict), (
        "[GR_CANPAY_OK] La respuesta no es un objeto JSON (dict)."
    )

    msg = resp_json.get("message", "")
    msg_lower = msg.lower()
    assert "cancelación exitosa" in msg_lower, (
        "[GR_CANPAY_OK] El mensaje no indica cancelación exitosa. "
        f"message: {msg!r}"
    )

    deleted_payment = resp_json.get("deleted_payment")
    deleted_reservation = resp_json.get("deleted_reservation")

    assert isinstance(deleted_payment, dict), (
        "[GR_CANPAY_OK] No viene un objeto 'deleted_payment' válido en la respuesta."
    )
    assert isinstance(deleted_reservation, dict), (
        "[GR_CANPAY_OK] No viene un objeto 'deleted_reservation' válido en la respuesta."
    )

    assert deleted_payment.get("payment_id") == payment_id, (
        "[GR_CANPAY_OK] payment_id en 'deleted_payment' no coincide con el solicitado. "
        f"esperado={payment_id!r}, respuesta={deleted_payment.get('payment_id')!r}"
    )

    # Si había reserva asociada, debe coincidir el reservation_id
    if "reservation_id" in deleted_reservation:
        assert deleted_reservation.get("reservation_id") == reservation_id, (
            "[GR_CANPAY_OK] reservation_id en 'deleted_reservation' "
            "no coincide con el del pago. "
            f"pago_res_id={reservation_id}, del_res_id={deleted_reservation.get('reservation_id')}"
        )

    # Comprobación opcional: el pago ya no debe existir
    r_check = _get_reservas(f"/get_payment_by_id/{payment_id}")
    if r_check.status_code != 400:  # 400 sería solo por formato raro, aquí es válido
        try:
            msg_check = r_check.json().get("message", "")
        except Exception:
            msg_check = r_check.text

        assert r_check.status_code == 404, (
            "[GR_CANPAY_OK] Tras cancelar, se esperaba 404 al consultar "
            f"el pago {payment_id}, vino {r_check.status_code} {r_check.text}"
        )

        msg_check_lower = msg_check.lower()
        # Aceptamos ambas variantes: sin pagos o sin ese pago específico
        assert (
            "no se encontró ningún pago" in msg_check_lower
            or "no hay pagos generados aún" in msg_check_lower
        ), (
            "[GR_CANPAY_OK] Mensaje inesperado al consultar pago luego de cancelar. "
            f"message: {msg_check!r}"
        )
