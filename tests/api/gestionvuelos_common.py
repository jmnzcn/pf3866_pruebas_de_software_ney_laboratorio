# tests/api/gestionvuelos_common.py
"""
Helpers compartidos para los tests RAG de GestiónVuelos.
"""
import os
import random
import string

import pytest
import requests

BASE_URL = os.getenv("GV_BASE_URL", "http://localhost:5001")


# ---------------------------------------------------------------------------
# Utilidades simples HTTP
# ---------------------------------------------------------------------------

def _get(path, timeout=10):
    return requests.get(f"{BASE_URL}{path}", timeout=timeout)


def _post(path, json=None, timeout=10):
    return requests.post(f"{BASE_URL}{path}", json=json, timeout=timeout)


def _put(path, json=None, timeout=10):
    return requests.put(f"{BASE_URL}{path}", json=json, timeout=timeout)


def _delete(path, timeout=10):
    return requests.delete(f"{BASE_URL}{path}", timeout=timeout)


def _random_suffix(n=4):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))


# -------------------------------------------------------------------
# Helper para construir un payload válido de /add_airplane_route
# -------------------------------------------------------------------
def _build_valid_route_payload(airplane_id, route_id=None):
    """
    Construye un payload válido para /add_airplane_route, usando:
    - meses en español (para que pase el validador de fecha),
    - flight_number con formato 'AA-1234',
    - Moneda válida ('Colones').
    """
    if route_id is None:
        route_id = random.randint(30_000, 39_999)

    flight_number = (
        f"{random.choice(string.ascii_uppercase)}"
        f"{random.choice(string.ascii_uppercase)}-"
        f"{random.randint(1000, 9999)}"
    )

    return {
        "airplane_route_id": route_id,
        "airplane_id": airplane_id,
        "flight_number": flight_number,
        "departure": "Aeropuerto Internacional A",
        "departure_time": "Marzo 30, 2025 - 16:46:19",
        "arrival": "Aeropuerto Internacional B",
        "arrival_time": "Marzo 30, 2025 - 19:25:00",
        "price": 98000,
        "Moneda": "Colones",
    }


# ---------------------------------------------------------------------------
# Fixture: servicio arriba
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def service_up():
    """
    Verifica que GestiónVuelos esté disponible en /health.
    Si no responde 200, se hace skip de toda la suite.
    """
    try:
        r = _get("/health", timeout=5)
        if r.status_code != 200:
            pytest.skip("GestiónVuelos no responde 200 en /health")
    except Exception:
        pytest.skip("GestiónVuelos no está disponible en BASE_URL")
    return True
