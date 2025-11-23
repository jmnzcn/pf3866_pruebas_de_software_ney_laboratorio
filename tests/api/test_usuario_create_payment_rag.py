"""
EXPERIMENTO_RAG_04_usuario_create_payment

Pruebas de contrato para el endpoint:
    POST /usuario/create_payment

Casos cubiertos:
- Body vacío o ausente -> 400.
- reservation_id inválido -> 400.
- payment_method inválido -> 400.
- currency inválida -> 400.
- Reserva no existente -> 404.
- Caso feliz: creación exitosa del pago -> 201.
"""

import os
import requests
import pytest

# Base URL del microservicio Usuario
BASE_URL = os.getenv("USUARIO_BASE_URL", "http://localhost:5003")


def _get(path: str, **kwargs) -> requests.Response:
    url = f"{BASE_URL}{path}"
    return requests.get(url, **kwargs)


def _post(path: str, **kwargs) -> requests.Response:
    url = f"{BASE_URL}{path}"
    return requests.post(url, **kwargs)


def _find_reservation_without_payment():
    """
    Busca una reserva que NO tenga pago asociado.

    Estrategia:
    1) GET /get_all_reservations  -> lista de reservas.
    2) GET /get_all_payments      -> lista de pagos (cada uno con reservation_id).
    3) Elegir la primera reserva cuyo reservation_id no esté en la lista de pagos.
    4) Si no se puede determinar, retorna None.
    """
    # 1) Obtener todas las reservas desde Usuario
    r_res = _get("/get_all_reservations")
    assert r_res.status_code == 200, (
        f"[USR_PAY_OK_PRE] No se pudieron obtener reservas: "
        f"{r_res.status_code} {r_res.text}"
    )

    try:
        reservas = r_res.json()
    except Exception:
        return None

    if not isinstance(reservas, list) or not reservas:
        # No hay reservas para probar pagos
        return None

    # 2) Obtener todos los pagos desde Usuario
    r_pay = _get("/get_all_payments")
    if r_pay.status_code != 200:
        # Si el endpoint de pagos no está bien, devolvemos la primera reserva
        # (mejor que fallar por aquí).
        return reservas[0]

    try:
        pagos = r_pay.json()
    except Exception:
        return reservas[0]

    reservation_ids_con_pago = set()

    # 3) Construir el conjunto de reservation_id que YA tienen pago
    if isinstance(pagos, list):
        for p in pagos:
            if isinstance(p, dict) and "reservation_id" in p:
                reservation_ids_con_pago.add(p["reservation_id"])
    elif isinstance(pagos, dict):
        # Caso mensaje tipo {"message": "No hay pagos generados actualmente."}
        msg = str(pagos.get("message", "")).lower()
        if "no hay pagos" in msg:
            reservation_ids_con_pago = set()
        else:
            # Respuesta no esperada, mejor simplemente usar la primera reserva
            return reservas[0]

    # 4) Elegir la primera reserva SIN pago
    for r in reservas:
        rid = r.get("reservation_id")
        if isinstance(rid, int) and rid not in reservation_ids_con_pago:
            return r

    # Si todas las reservas tienen pago, no se puede probar el caso feliz de creación
    return None


@pytest.mark.parametrize(
    "case_id, body, expected_status, expected_msg_sub",
    [
        # Body vacío o ausente
        (
            "USR_PAY_BODY_VACIO",
            None,
            400,
            "No se recibió cuerpo JSON",
        ),
        # reservation_id inválido
        (
            "USR_PAY_ID_INVALIDO",
            {
                "reservation_id": 0,
                "payment_method": "Tarjeta",
                "currency": "Dolares",
            },
            400,
            "El reservation_id debe ser un entero positivo.",
        ),
        # payment_method inválido
        (
            "USR_PAY_METHOD_INV",
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
            "USR_PAY_CURRENCY_INV",
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
            "USR_PAY_RES_NO_EXIST",
            {
                "reservation_id": 999999,  # ID muy grande, poco probable que exista
                "payment_method": "Tarjeta",
                "currency": "Dolares",
            },
            404,
            "no encontrada",
        ),
    ],
)
def test_usuario_create_payment_validaciones_basicas_y_404(
    case_id,
    body,
    expected_status,
    expected_msg_sub,
):
    """
    Casos de error para /usuario/create_payment:

    - Body vacío o ausente -> 400.
    - reservation_id inválido -> 400.
    - payment_method inválido -> 400.
    - currency inválida -> 400.
    - reserva no existente -> 404.
    """
    if body is None:
        # Sin body JSON
        r = _post("/usuario/create_payment")
    else:
        r = _post("/usuario/create_payment", json=body)

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

    # Mensaje esperado (solo substring, no exacto)
    assert expected_msg_sub.lower() in msg_text.lower(), (
        f"[{case_id}] No se encontró el texto esperado en el mensaje. "
        f"Buscaba: '{expected_msg_sub}' en: '{msg_text}'"
    )


def test_usuario_create_payment_happy_path():
    """
    Caso feliz: crear un pago para una reserva existente SIN pago previo.

    Pasos:
    1) Buscar una reserva que no tenga pagos asociados (helper de caja negra).
    2) Usar su reservation_id para llamar a POST /usuario/create_payment con:
       - reservation_id existente
       - payment_method válido
       - currency válida
    3) Verificar que:
       - Devuelva 201
       - El mensaje indique éxito
       - Venga un objeto 'payment' con payment_id no vacío
    """
    # 1) Encontrar una reserva sin pago
    reserva = _find_reservation_without_payment()
    if reserva is None:
        pytest.skip(
            "[USR_PAY_OK_01] No se encontraron reservas sin pago para probar el caso feliz."
        )

    reservation_id = reserva.get("reservation_id")
    assert reservation_id, (
        "[USR_PAY_OK_01] La reserva seleccionada no tiene un reservation_id válido: "
        f"{reserva}"
    )

    body = {
        "reservation_id": reservation_id,
        "payment_method": "Tarjeta",
        "currency": "Dolares",
    }

    # 2) Llamar al endpoint de Usuario
    r = _post("/usuario/create_payment", json=body)

    assert (
        r.status_code == 201
    ), f"[USR_PAY_OK_01] Código inesperado en create_payment: {r.status_code} {r.text}"

    # 3) Validar estructura de la respuesta
    resp_json = r.json()
    msg = resp_json.get("message", "")
    msg_lower = msg.lower()

    # El mensaje debería dejar claro que el pago fue registrado
    assert (
        "pago" in msg_lower
        and ("registrado" in msg_lower or "pagado" in msg_lower)
    ), (
        "[USR_PAY_OK_01] Mensaje de éxito inesperado en create_payment: "
        f"{msg}"
    )

    payment = resp_json.get("payment")
    assert isinstance(payment, dict), (
        "[USR_PAY_OK_01] La respuesta no contiene un objeto 'payment' válido: "
        f"{resp_json}"
    )

    payment_id = payment.get("payment_id")
    assert payment_id, (
        "[USR_PAY_OK_01] El objeto 'payment' no contiene un 'payment_id' válido: "
        f"{payment}"
    )
