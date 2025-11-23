"""
EXPERIMENTO_RAG_07_usuario_flights_routes_seats

Pruebas de contrato para los endpoints:
    GET /get_airplane_route_by_id/<int:airplane_route_id>
    GET /get_seats_by_airplane_id/<int:airplane_id>/seats

Casos cubiertos:
- ID de ruta 0 -> 400.
- ID de ruta negativo -> 404 (no hace match con el converter <int:> de Flask).
- Ruta no existente -> 404.
- Caso feliz: ruta existente -> 200.
- ID de avión 0 -> 400.
- ID de avión negativo -> 404 (ruta no encontrada).
- Avión inexistente (ID muy grande) -> 500 (error de formato/conexión).
- Caso feliz: avión existente con asientos -> 200.
"""

import os
import requests
import pytest

# Base URL del microservicio Usuario
BASE_URL = os.getenv("USUARIO_BASE_URL", "http://localhost:5003")


def _get(path: str, **kwargs) -> requests.Response:
    url = f"{BASE_URL}{path}"
    return requests.get(url, **kwargs)


def _find_existing_route_id():
    """
    Busca una ruta de vuelo existente usando:
        GET /get_all_airplanes_routes

    Retorna:
        - int airplane_route_id si encuentra uno válido
        - None si no se puede determinar
    """
    r = _get("/get_all_airplanes_routes")
    if r.status_code != 200:
        return None

    try:
        rutas = r.json()
    except Exception:
        return None

    if not isinstance(rutas, list) or not rutas:
        return None

    # Tomar la primera ruta que tenga un airplane_route_id entero positivo
    for ruta in rutas:
        rid = ruta.get("airplane_route_id")
        if isinstance(rid, int) and rid > 0:
            return rid

    return None


def _find_airplane_with_seats():
    """
    Busca un avión que tenga al menos un asiento asociado usando:
        GET /get_all_airplanes_with_seats

    Retorna:
        - int airplane_id si encuentra uno válido con asientos
        - None si no se puede determinar
    """
    r = _get("/get_all_airplanes_with_seats")
    if r.status_code != 200:
        return None

    try:
        aviones = r.json()
    except Exception:
        return None

    if not isinstance(aviones, list) or not aviones:
        return None

    for avion in aviones:
        aid = avion.get("airplane_id")
        seats = avion.get("seats", [])
        if isinstance(aid, int) and aid > 0 and isinstance(seats, list) and seats:
            return aid

    return None


@pytest.mark.parametrize(
    "case_id, path, expected_status, expected_msg_sub",
    [
        # ID == 0 -> entra al endpoint y dispara validación local -> 400
        (
            "USR_ROUTE_ID_CERO_400",
            "/get_airplane_route_by_id/0",
            400,
            "El ID debe ser un número positivo",
        ),
        # ID negativo -> no matchea el converter <int:> y Flask responde 404 HTML
        (
            "USR_ROUTE_ID_NEGATIVO_404",
            "/get_airplane_route_by_id/-1",
            404,
            "not found",
        ),
        # ID muy grande -> GestionVuelos devuelve 404, Usuario lo propaga
        (
            "USR_ROUTE_NO_EXISTE_404",
            "/get_airplane_route_by_id/999999",
            404,
            "Ruta de vuelo no encontrada",
        ),
    ],
)
def test_usuario_get_airplane_route_by_id_validaciones_y_404(
    case_id,
    path,
    expected_status,
    expected_msg_sub,
):
    """
    Casos de error para:
        GET /get_airplane_route_by_id/<int:airplane_route_id>

    - ID == 0 -> 400 (validación local en Usuario).
    - ID negativo -> 404 (no entra al endpoint; Flask devuelve Not Found).
    - ID muy grande (no existe) -> 404 (propagado desde GestiónVuelos).
    """
    r = _get(path)

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

    assert expected_msg_sub.lower() in msg_text.lower(), (
        f"[{case_id}] No se encontró el texto esperado en el mensaje. "
        f"Buscaba: '{expected_msg_sub}' en: '{msg_text}'"
    )


def test_usuario_get_airplane_route_by_id_happy_path():
    """
    Caso feliz para:
        GET /get_airplane_route_by_id/<int:airplane_route_id>

    Pasos:
    1) Buscar una ruta existente usando GET /get_all_airplanes_routes.
    2) Invocar GET /get_airplane_route_by_id/<id>.
    3) Verificar que:
       - Devuelva 200
       - El JSON contenga airplane_route_id == id
    """
    route_id = _find_existing_route_id()
    if route_id is None:
        pytest.skip(
            "[USR_ROUTE_OK_01] No se encontró ninguna ruta válida en /get_all_airplanes_routes."
        )

    r = _get(f"/get_airplane_route_by_id/{route_id}")

    assert (
        r.status_code == 200
    ), f"[USR_ROUTE_OK_01] Código inesperado: {r.status_code} {r.text}"

    resp_json = r.json()
    assert isinstance(resp_json, dict), (
        "[USR_ROUTE_OK_01] La respuesta no es un objeto JSON válido: "
        f"{resp_json}"
    )

    assert resp_json.get("airplane_route_id") == route_id, (
        "[USR_ROUTE_OK_01] El airplane_route_id devuelto no coincide con el solicitado. "
        f"Esperado: {route_id}, recibido: {resp_json.get('airplane_route_id')}"
    )


@pytest.mark.parametrize(
    "case_id, path, expected_status, expected_msg_sub",
    [
        # ID == 0 -> validación local en Usuario -> 400
        (
            "USR_SEATS_ID_CERO_400",
            "/get_seats_by_airplane_id/0/seats",
            400,
            "Por favor proporciona un ID de avión válido",
        ),
        # ID negativo -> no entra al endpoint por el converter <int:> -> 404 HTML
        (
            "USR_SEATS_ID_NEGATIVO_404",
            "/get_seats_by_airplane_id/-1/seats",
            404,
            "not found",
        ),
        # ID muy grande -> el helper devuelve None y Usuario responde 500
        (
            "USR_SEATS_AIRPLANE_NO_EXISTE_500",
            "/get_seats_by_airplane_id/999999/seats",
            500,
            "Error al procesar los datos: formato inválido o sin conexión.",
        ),
    ],
)
def test_usuario_get_seats_by_airplane_id_validaciones_y_errores(
    case_id,
    path,
    expected_status,
    expected_msg_sub,
):
    """
    Casos de error para:
        GET /get_seats_by_airplane_id/<int:airplane_id>/seats

    - ID == 0 -> 400 (validación local).
    - ID negativo -> 404 (no matchea la ruta, Flask responde Not Found).
    - ID muy grande -> 500 (Usuario detecta que la respuesta no es lista y
      devuelve "Error al procesar los datos: formato inválido o sin conexión.").
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


def test_usuario_get_seats_by_airplane_id_happy_path():
    """
    Caso feliz para:
        GET /get_seats_by_airplane_id/<int:airplane_id>/seats

    Pasos:
    1) Buscar un avión que tenga al menos un asiento usando
       GET /get_all_airplanes_with_seats.
    2) Invocar GET /get_seats_by_airplane_id/<airplane_id>/seats.
    3) Verificar que:
       - Devuelva 200
       - La respuesta sea una lista
       - Cada asiento tenga 'seat_number' y 'status'
    """
    airplane_id = _find_airplane_with_seats()
    if airplane_id is None:
        pytest.skip(
            "[USR_SEATS_OK_01] No se encontró ningún avión con asientos en /get_all_airplanes_with_seats."
        )

    r = _get(f"/get_seats_by_airplane_id/{airplane_id}/seats")

    assert (
        r.status_code == 200
    ), f"[USR_SEATS_OK_01] Código inesperado: {r.status_code} {r.text}"

    try:
        seats = r.json()
    except Exception:
        seats = None

    assert isinstance(seats, list) and seats, (
        "[USR_SEATS_OK_01] La respuesta no es una lista de asientos válida: "
        f"{seats}"
    )

    for seat in seats:
        assert isinstance(seat, dict), (
            "[USR_SEATS_OK_01] Uno de los elementos no es un objeto JSON: "
            f"{seat}"
        )
        assert "seat_number" in seat, (
            "[USR_SEATS_OK_01] Falta 'seat_number' en un asiento: "
            f"{seat}"
        )
        assert "status" in seat, (
            "[USR_SEATS_OK_01] Falta 'status' en un asiento: "
            f"{seat}"
        )
