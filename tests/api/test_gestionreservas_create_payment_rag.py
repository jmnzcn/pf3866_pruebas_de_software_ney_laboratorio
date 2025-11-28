"""
EXPERIMENTO_RAG_10_gestionreservas_create_payment

Pruebas de contrato para el endpoint:
    POST /create_payment

Comportamiento esperado (según app.py en GestiónReservas):

- reservation_id inválido (<= 0):
    -> 400
    -> "El reservation_id debe ser un número entero positivo."

- payment_method inválido:
    -> 400
    -> "Método de pago inválido."

- currency inválida:
    -> 400
    -> "Moneda no soportada."

- Reserva no existente:
    -> 404
    -> "Reserva con ID <id> no encontrada."

- Reserva ya tiene pago:
    -> 409
    -> "Esta reserva ya tiene un pago registrado."

- Caso feliz:
    - Reserva existente sin pago previo
    -> 201
    -> {"message": "...Pago...registrado...", "payment": {...}}
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


def _post_reservas(path: str, **kwargs) -> requests.Response:
    url = f"{BASE_URL_RESERVAS}{path}"
    return requests.post(url, timeout=20, **kwargs)


def _find_reservation_without_payment():
    """
    Busca una reserva que NO tenga pago asociado.

    Estrategia:
    1) GET /get_fake_reservations  -> lista de reservas.
    2) GET /get_all_fake_payments  -> lista de pagos (cada uno con reservation_id).
    3) Elegir la primera reserva cuyo reservation_id no esté en la lista de pagos.
    4) Si no se puede determinar, retorna None.
    """
    # 1) Obtener reservas
    r_res = _get_reservas("/get_fake_reservations")
    if r_res.status_code == 204:
        # No hay reservas generadas
        return None

    assert r_res.status_code == 200, (
        f"[GR_CPAY_FIND_NOPAY] No se pudieron obtener reservas: "
        f"{r_res.status_code} {r_res.text}"
    )

    try:
        reservas = r_res.json()
    except Exception:
        return None

    if not isinstance(reservas, list) or not reservas:
        return None

    # 2) Obtener pagos
    r_pay = _get_reservas("/get_all_fake_payments")
    if r_pay.status_code != 200:
        # Si algo falla al consultar pagos, devolvemos alguna reserva cualquiera
        return reservas[0]

    try:
        pagos = r_pay.json()
    except Exception:
        return reservas[0]

    reservation_ids_con_pago = set()

    if isinstance(pagos, list):
        for p in pagos:
            if isinstance(p, dict) and "reservation_id" in p:
                reservation_ids_con_pago.add(p["reservation_id"])
    elif isinstance(pagos, dict):
        msg = str(pagos.get("message", "")).lower()
        if "no hay pagos" in msg:
            reservation_ids_con_pago = set()
        else:
            # Respuesta no esperada; tomamos la primera reserva
            return reservas[0]

    # 3) Elegir la primera reserva SIN pago
    for r in reservas:
        rid = r.get("reservation_id")
        if isinstance(rid, int) and rid not in reservation_ids_con_pago:
            return r

    return None


def _find_reservation_with_payment():
    """
    Busca una reserva que SÍ tenga pago asociado.

    Estrategia:
    1) GET /get_all_fake_payments  -> lista de pagos.
    2) Si hay pagos, devolvemos el reservation_id del primero.
    """
    r_pay = _get_reservas("/get_all_fake_payments")
    if r_pay.status_code != 200:
        return None

    try:
        pagos = r_pay.json()
    except Exception:
        return None

    if not isinstance(pagos, list) or not pagos:
        return None

    first = pagos[0]
    if isinstance(first, dict):
        rid = first.get("reservation_id")
        if isinstance(rid, int):
            return rid

    return None


@pytest.mark.parametrize(
    "case_id, body, expected_status, expected_msg_sub",
    [
        # reservation_id inválido
        (
            "GR_CPAY_RES_ID_INVALIDO_400",
            {
                "reservation_id": 0,
                "payment_method": "Tarjeta",
                "currency": "Dolares",
            },
            400,
            "El reservation_id debe ser un número entero positivo.",
        ),
        # payment_method inválido
        (
            "GR_CPAY_METHOD_INVALIDO_400",
            {
                "reservation_id": 1,  # cualquier entero positivo
                "payment_method": "Bitcoin",
                "currency": "Dolares",
            },
            400,
            "Método de pago inválido.",
        ),
        # currency inválida
        (
            "GR_CPAY_MONEDA_INVALIDA_400",
            {
                "reservation_id": 1,
                "payment_method": "Tarjeta",
                "currency": "EUR",
            },
            400,
            "Moneda no soportada.",
        ),
        # reserva no existente
        (
            "GR_CPAY_RES_NO_EXISTE_404",
            {
                "reservation_id": 999999,  # muy grande
                "payment_method": "Tarjeta",
                "currency": "Dolares",
            },
            404,
            "no encontrada",
        ),
    ],
)
def test_gestionreservas_create_payment_validaciones_basicas_y_404(
    case_id,
    body,
    expected_status,
    expected_msg_sub,
):
    """
    Casos de error para POST /create_payment en GestiónReservas:

    - reservation_id inválido -> 400.
    - payment_method inválido -> 400.
    - currency inválida       -> 400.
    - reserva no existente    -> 404.
    """
    r = _post_reservas("/create_payment", json=body)

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


def test_gestionreservas_create_payment_reserva_ya_tiene_pago_409():
    """
    Caso de error:
        Intentar crear un pago para una reserva que YA tiene un pago.

    Pasos:
    1) Buscar una reserva con pago asociado (usando /get_all_fake_payments).
    2) POST /create_payment con ese reservation_id.
    3) Verificar:
       - status_code == 409
       - mensaje contenga "ya tiene un pago registrado".
    """
    reservation_id = _find_reservation_with_payment()
    if reservation_id is None:
        pytest.skip(
            "[GR_CPAY_DUP_409] No se encontró ninguna reserva con pago; "
            "no se puede probar el caso de duplicado."
        )

    body = {
        "reservation_id": reservation_id,
        "payment_method": "Tarjeta",
        "currency": "Dolares",
    }

    r = _post_reservas("/create_payment", json=body)

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        resp_json = {}
        msg_text = r.text

    assert (
        r.status_code == 409
    ), f"[GR_CPAY_DUP_409] Se esperaba 409, vino {r.status_code} {r.text}"

    assert "ya tiene un pago registrado" in msg_text.lower(), (
        "[GR_CPAY_DUP_409] Mensaje inesperado para pago duplicado. "
        f"message: {msg_text!r}"
    )


def test_gestionreservas_create_payment_happy_path():
    """
    Caso feliz:
        Crear un pago para una reserva existente SIN pago previo.

    Pasos:
    1) Buscar una reserva que no tenga pagos asociados (helper de caja negra).
    2) Usar su reservation_id para llamar a POST /create_payment con:
       - reservation_id existente
       - payment_method válido
       - currency válida
    3) Verificar que:
       - Devuelva 201
       - El mensaje indique éxito (contenga "pago" y "registrado")
       - Venga un objeto 'payment' con payment_id no vacío y formato PAYxxxxxx
       - reservation_id del payment coincida con el utilizado.
    """
    reserva = _find_reservation_without_payment()
    if reserva is None:
        pytest.skip(
            "[GR_CPAY_OK_201] No se encontraron reservas sin pago para "
            "probar el caso feliz."
        )

    reservation_id = reserva.get("reservation_id")
    assert reservation_id, (
        "[GR_CPAY_OK_201] La reserva seleccionada no tiene un reservation_id válido: "
        f"{reserva}"
    )

    body = {
        "reservation_id": reservation_id,
        "payment_method": "Tarjeta",
        "currency": "Dolares",
    }

    r = _post_reservas("/create_payment", json=body)

    assert (
        r.status_code == 201
    ), f"[GR_CPAY_OK_201] Código inesperado en create_payment: {r.status_code} {r.text}"

    try:
        resp_json = r.json()
    except Exception:
        pytest.fail(
            f"[GR_CPAY_OK_201] La respuesta no es JSON válido. Body crudo: {r.text}"
        )

    assert isinstance(resp_json, dict), (
        "[GR_CPAY_OK_201] La respuesta no es un objeto JSON."
    )

    msg = resp_json.get("message", "")
    msg_lower = msg.lower()

    assert "pago" in msg_lower and "registrado" in msg_lower, (
        "[GR_CPAY_OK_201] Mensaje de éxito inesperado: "
        f"{msg}"
    )

    payment = resp_json.get("payment")
    assert isinstance(payment, dict), (
        "[GR_CPAY_OK_201] La respuesta no contiene un objeto 'payment' válido: "
        f"{resp_json}"
    )

    payment_id = payment.get("payment_id")
    assert isinstance(payment_id, str) and re.match(r"^PAY\d{6}$", payment_id), (
        "[GR_CPAY_OK_201] 'payment_id' no tiene el formato esperado PAYxxxxxx: "
        f"{payment_id!r}"
    )

    assert payment.get("reservation_id") == reservation_id, (
        "[GR_CPAY_OK_201] reservation_id del payment no coincide con el usado en la petición. "
        f"reserv_id_req={reservation_id}, reserv_id_resp={payment.get('reservation_id')}"
    )

    assert payment.get("status") == "Pagado", (
        "[GR_CPAY_OK_201] status del payment esperado 'Pagado', vino: "
        f"{payment.get('status')!r}"
    )
