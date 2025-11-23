"""
EXPERIMENTO_RAG_10_usuario_airplanes_lists

Pruebas de contrato en caja negra para los endpoints:

    GET /get_all_airplanes_routes
    GET /get_all_airplanes_with_seats

del microservicio Usuario.

Estrategia:
- Si el entorno tiene datos cargados:
    - Verificar contrato en caso 200.
- Si el entorno está vacío (sin vuelos / sin aviones):
    - Verificar mensaje 404 esperado y marcar la prueba como SKIP
      (escenario válido pero no útil para validar estructura).
- Cualquier otro código se considera fallo en este laboratorio.
"""

import os
import requests
import pytest

BASE_URL = os.getenv("USUARIO_BASE_URL", "http://localhost:5003")


def _get(path: str, **kwargs) -> requests.Response:
    url = f"{BASE_URL}{path}"
    return requests.get(url, **kwargs)


# ---------------------------------------------------------------------------
# GET /get_all_airplanes_routes
# ---------------------------------------------------------------------------

def test_usuario_get_all_airplanes_routes_contract():
    """
    Valida el contrato de:

        GET /get_all_airplanes_routes

    Comportamiento esperado en este laboratorio:

    - 200:
        - Respuesta es una lista no vacía.
        - Cada elemento es dict con al menos 'airplane_route_id'.
    - 404:
        - Entorno sin vuelos.
        - Mensaje contiene "No hay vuelos registrados actualmente en el sistema".
        - Se marca la prueba como SKIP (caso válido pero no estructural).
    - Otro status:
        - Se considera fallo.
    """
    case_id = "USR_AIRLIST_ROUTES_CONTRACT"

    r = _get("/get_all_airplanes_routes")

    try:
        data = r.json()
    except Exception:
        data = None

    if r.status_code == 200:
        # Debe ser una lista no vacía
        assert isinstance(data, list), (
            f"[{case_id}] Se esperaba una lista JSON, se obtuvo: {type(data)}"
        )
        assert len(data) > 0, (
            f"[{case_id}] La lista de rutas está vacía pero el endpoint devolvió 200."
        )

        # Validar estructura mínima de cada ruta
        for idx, ruta in enumerate(data):
            assert isinstance(ruta, dict), (
                f"[{case_id}] Elemento {idx} no es dict: {ruta}"
            )
            assert "airplane_route_id" in ruta, (
                f"[{case_id}] Elemento {idx} no contiene 'airplane_route_id': {ruta}"
            )

    elif r.status_code == 404:
        # Entorno sin rutas registradas
        assert isinstance(data, dict), (
            f"[{case_id}] Para 404 se esperaba un dict JSON, se obtuvo: {type(data)}"
        )
        msg = (data.get("error") or data.get("message") or "").lower()
        assert "no hay vuelos registrados actualmente en el sistema" in msg, (
            f"[{case_id}] Mensaje 404 inesperado: {data}"
        )
        pytest.skip(
            f"[{case_id}] Entorno sin vuelos. Caso 404 válido, se omite validación estructural."
        )

    else:
        pytest.fail(
            f"[{case_id}] Código inesperado: {r.status_code} {r.text}"
        )


# ---------------------------------------------------------------------------
# GET /get_all_airplanes_with_seats
# ---------------------------------------------------------------------------

def test_usuario_get_all_airplanes_with_seats_contract():
    """
    Valida el contrato de:

        GET /get_all_airplanes_with_seats

    Comportamiento esperado en este laboratorio:

    - 200:
        - Respuesta es una lista no vacía.
        - Cada avión:
            - dict con campos: airplane_id, model, manufacturer, year, capacity, seats.
            - 'seats' es lista (puede estar vacía).
        - Cada asiento (si hay):
            - dict con seat_number y status.
    - 404:
        - Entorno sin aviones.
        - Mensaje contiene "No hay aviones registrados actualmente".
        - Se marca la prueba como SKIP (caso válido pero no estructural).
    - Otro status:
        - Se considera fallo.
    """
    case_id = "USR_AIRLIST_PLANES_WITH_SEATS_CONTRACT"

    r = _get("/get_all_airplanes_with_seats")

    try:
        data = r.json()
    except Exception:
        data = None

    if r.status_code == 200:
        # Debe ser lista no vacía
        assert isinstance(data, list), (
            f"[{case_id}] Se esperaba una lista JSON, se obtuvo: {type(data)}"
        )
        assert len(data) > 0, (
            f"[{case_id}] La lista de aviones está vacía pero el endpoint devolvió 200."
        )

        for idx, avion in enumerate(data):
            assert isinstance(avion, dict), (
                f"[{case_id}] Elemento {idx} de la lista no es dict: {avion}"
            )

            # Campos mínimos del avión
            for field in ("airplane_id", "model", "manufacturer", "year", "capacity", "seats"):
                assert field in avion, (
                    f"[{case_id}] Avión {idx} no contiene el campo obligatorio '{field}': {avion}"
                )

            seats = avion["seats"]
            assert isinstance(seats, list), (
                f"[{case_id}] 'seats' del avión {idx} no es lista: {type(seats)}"
            )

            # Validar algunos campos clave en cada asiento (si hay asientos)
            for jdx, seat in enumerate(seats):
                assert isinstance(seat, dict), (
                    f"[{case_id}] Asiento {jdx} del avión {idx} no es dict: {seat}"
                )
                assert "seat_number" in seat, (
                    f"[{case_id}] Asiento {jdx} del avión {idx} no tiene 'seat_number': {seat}"
                )
                assert "status" in seat, (
                    f"[{case_id}] Asiento {jdx} del avión {idx} no tiene 'status': {seat}"
                )

    elif r.status_code == 404:
        # Entorno sin aviones registrados
        assert isinstance(data, dict), (
            f"[{case_id}] Para 404 se esperaba un dict JSON, se obtuvo: {type(data)}"
        )
        msg = (data.get("message") or data.get("error") or "").lower()
        assert "no hay aviones registrados actualmente" in msg, (
            f"[{case_id}] Mensaje 404 inesperado: {data}"
        )
        pytest.skip(
            f"[{case_id}] Entorno sin aviones. Caso 404 válido, se omite validación estructural."
        )

    else:
        pytest.fail(
            f"[{case_id}] Código inesperado: {r.status_code} {r.text}"
        )
