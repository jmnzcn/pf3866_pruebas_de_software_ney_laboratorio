"""
EXPERIMENTO_RAG_08_usuario_get_reservations

Pruebas de contrato para los endpoints de consulta de reservas del
microservicio Usuario:

    GET /get_reservation_by_code/<string:reservation_code>
    GET /get_reservation_by_id/<int:reservation_id>
    GET /get_all_reservations

Casos cubiertos:

- Código de reserva vacío -> 400.
- Código de reserva inexistente -> 404.
- Caso feliz por código -> 200.
- ID de reserva 0 -> 400.
- ID de reserva negativo -> 404 (HTML Not Found de Flask).
- ID de reserva inexistente -> 404.
- Caso feliz por ID -> 200.
- Contrato general de /get_all_reservations -> 200 (mensaje o lista).
"""

import os
import requests
import pytest

# Base URL del microservicio Usuario
BASE_URL = os.getenv("USUARIO_BASE_URL", "http://localhost:5003")


def _get(path: str, **kwargs) -> requests.Response:
    url = f"{BASE_URL}{path}"
    return requests.get(url, **kwargs)


def _get_any_reservation():
    """
    Devuelve una reserva cualquiera obtenida desde:

        GET /get_all_reservations

    Si no hay reservas (o la respuesta no es una lista válida),
    retorna None para que el test feliz haga pytest.skip.
    """
    r = _get("/get_all_reservations")
    if r.status_code != 200:
        return None

    try:
        data = r.json()
    except Exception:
        return None

    # Caso: no hay reservas -> dict con {"message": "No hay reservas registradas."}
    if isinstance(data, dict):
        msg = str(data.get("message", "")).lower()
        if "no hay reservas registradas" in msg:
            return None
        return None

    # Caso: lista de reservas
    if isinstance(data, list) and data:
        first = data[0]
        if isinstance(first, dict) and "reservation_id" in first:
            return first

    return None


# ---------------------------------------------------------------------------
# GET /get_reservation_by_code/<reservation_code>
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "case_id, path, expected_status, expected_msg_sub",
    [
        (
            "USR_RES_CODE_VACIO_400",
            "/get_reservation_by_code/%20%20%20",  # "   "
            400,
            "El código de reserva es obligatorio y debe ser texto válido.",
        ),
        (
            "USR_RES_CODE_NO_EXISTE_404",
            "/get_reservation_by_code/ZZZ999",
            404,
            "Reserva no encontrada en GestiónReservas",
        ),
    ],
)
def test_usuario_get_reservation_by_code_validaciones_y_404(
    case_id,
    path,
    expected_status,
    expected_msg_sub,
):
    """
    Casos de error para:
        GET /get_reservation_by_code/<string:reservation_code>

    - Código vacío -> 400.
    - Código inexistente -> 404.
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


def test_usuario_get_reservation_by_code_happy_path():
    """
    Caso feliz para:
        GET /get_reservation_by_code/<string:reservation_code>

    Pasos:
    1) Obtener cualquier reserva existente usando /get_all_reservations.
    2) Tomar su reservation_code.
    3) Invocar /get_reservation_by_code/<reservation_code>.
    4) Verificar que:
       - Devuelva 200.
       - La respuesta sea un dict.
       - El reservation_code devuelto coincida.
    """
    reserva = _get_any_reservation()
    if reserva is None:
        pytest.skip(
            "[USR_RES_CODE_OK_200] No se encontró ninguna reserva en /get_all_reservations."
        )

    code = reserva.get("reservation_code")
    assert code, (
        "[USR_RES_CODE_OK_200] La reserva obtenida no tiene reservation_code válido: "
        f"{reserva}"
    )

    r = _get(f"/get_reservation_by_code/{code}")

    assert (
        r.status_code == 200
    ), f"[USR_RES_CODE_OK_200] Código inesperado: {r.status_code} {r.text}"

    resp_json = r.json()
    assert isinstance(resp_json, dict), (
        "[USR_RES_CODE_OK_200] La respuesta no es un objeto JSON: "
        f"{resp_json}"
    )

    assert resp_json.get("reservation_code") == code, (
        "[USR_RES_CODE_OK_200] El reservation_code devuelto no coincide con el solicitado. "
        f"Esperado: {code}, recibido: {resp_json.get('reservation_code')}"
    )


# ---------------------------------------------------------------------------
# GET /get_reservation_by_id/<reservation_id>
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "case_id, path, expected_status, expected_msg_sub",
    [
        (
            "USR_RES_ID_CERO_400",
            "/get_reservation_by_id/0",
            400,
            "El ID debe ser un número entero positivo.",
        ),
        (
            "USR_RES_ID_NEGATIVO_404",
            "/get_reservation_by_id/-1",
            404,
            "not found",  # HTML genérico de Flask
        ),
        (
            "USR_RES_ID_NO_EXISTE_404",
            "/get_reservation_by_id/999999",
            404,
            "Reserva no encontrada en GestiónReservas",
        ),
    ],
)
def test_usuario_get_reservation_by_id_validaciones_y_404(
    case_id,
    path,
    expected_status,
    expected_msg_sub,
):
    """
    Casos de error para:
        GET /get_reservation_by_id/<int:reservation_id>

    - ID == 0 -> 400 (validación local).
    - ID negativo -> 404 (no matchea la ruta, Flask responde Not Found).
    - ID muy grande inexistente -> 404 (propagado desde GestiónReservas).
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


def test_usuario_get_reservation_by_id_happy_path():
    """
    Caso feliz para:
        GET /get_reservation_by_id/<int:reservation_id>

    Pasos:
    1) Obtener cualquier reserva existente usando /get_all_reservations.
    2) Tomar su reservation_id.
    3) Invocar /get_reservation_by_id/<reservation_id>.
    4) Verificar que:
       - Devuelva 200.
       - La respuesta sea un dict.
       - El reservation_id devuelto coincida.
    """
    reserva = _get_any_reservation()
    if reserva is None:
        pytest.skip(
            "[USR_RES_ID_OK_200] No se encontró ninguna reserva en /get_all_reservations."
        )

    rid = reserva.get("reservation_id")
    assert isinstance(rid, int) and rid > 0, (
        "[USR_RES_ID_OK_200] La reserva obtenida no tiene reservation_id válido: "
        f"{reserva}"
    )

    r = _get(f"/get_reservation_by_id/{rid}")

    assert (
        r.status_code == 200
    ), f"[USR_RES_ID_OK_200] Código inesperado: {r.status_code} {r.text}"

    resp_json = r.json()
    assert isinstance(resp_json, dict), (
        "[USR_RES_ID_OK_200] La respuesta no es un objeto JSON: "
        f"{resp_json}"
    )

    assert resp_json.get("reservation_id") == rid, (
        "[USR_RES_ID_OK_200] El reservation_id devuelto no coincide con el solicitado. "
        f"Esperado: {rid}, recibido: {resp_json.get('reservation_id')}"
    )


# ---------------------------------------------------------------------------
# GET /get_all_reservations
# ---------------------------------------------------------------------------

def test_usuario_get_all_reservations_contract():
    """
    Contrato general para:
        GET /get_all_reservations

    Se espera:
    - status_code == 200
    - Cuerpo JSON que sea:
        a) dict con {"message": "No hay reservas registradas."}, o
        b) lista de reservas (cada una con reservation_id y campos clave).
    """
    r = _get("/get_all_reservations")

    assert (
        r.status_code == 200
    ), f"[USR_RES_ALL_CONTRACT] Código inesperado: {r.status_code} {r.text}"

    try:
        data = r.json()
    except Exception:
        pytest.fail(
            f"[USR_RES_ALL_CONTRACT] La respuesta no es JSON válido: {r.text[:200]}"
        )

    if isinstance(data, dict):
        # Caso "no hay reservas"
        msg = str(data.get("message", "")).lower()
        assert "no hay reservas registradas" in msg, (
            "[USR_RES_ALL_CONTRACT] Se esperaba un mensaje indicando que no hay "
            f"reservas registradas. Mensaje recibido: {data}"
        )
    elif isinstance(data, list):
        # Caso lista de reservas
        assert data, (
            "[USR_RES_ALL_CONTRACT] Se recibió una lista vacía; según el contrato "
            "Usuario debería devolver un mensaje cuando no hay reservas."
        )

        first = data[0]
        assert isinstance(first, dict), (
            "[USR_RES_ALL_CONTRACT] El primer elemento de la lista no es un objeto JSON: "
            f"{first}"
        )

        # Validación mínima de campos clave
        assert "reservation_id" in first, (
            "[USR_RES_ALL_CONTRACT] Falta 'reservation_id' en la reserva: "
            f"{first}"
        )
        assert "airplane_id" in first, (
            "[USR_RES_ALL_CONTRACT] Falta 'airplane_id' en la reserva: "
            f"{first}"
        )
        assert "seat_number" in first, (
            "[USR_RES_ALL_CONTRACT] Falta 'seat_number' en la reserva: "
            f"{first}"
        )
    else:
        pytest.fail(
            "[USR_RES_ALL_CONTRACT] La respuesta no es ni dict ni list. "
            f"Tipo recibido: {type(data)}"
        )
