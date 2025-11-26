# test_usuario_health_rag.py
"""
Experimento RAG 00 – Healthcheck del microservicio Usuario.

Basado en: EXPERIMENTO_RAG_00_usuario_health.md

Objetivo:
- Verificar que el endpoint GET /health del microservicio Usuario
  está disponible y devuelve el JSON esperado.
- Este test sirve como smoke test antes de ejecutar el resto de
  pruebas RAG sobre Usuario.
"""

import os
import requests
import pytest


# URL base del microservicio Usuario.
# Se puede sobreescribir con la variable de entorno USUARIO_SERVICE_URL.
USUARIO_BASE_URL = os.getenv("USUARIO_SERVICE_URL", "http://localhost:5003")


@pytest.mark.rag
@pytest.mark.healthcheck
def test_usuario_health_ok():
    """
    Caso esperado (happy path):

    - Llamar a GET /health
    - Verificar:
      - status_code == 200
      - Content-Type JSON
      - body == {"status": "ok", "service": "usuario"} (al menos esas claves)
    """
    url = f"{USUARIO_BASE_URL}/health"

    response = requests.get(url, timeout=10)

    # 1) Código HTTP
    assert response.status_code == 200, (
        f"Se esperaba 200 en {url}, pero se obtuvo {response.status_code} "
        f"con cuerpo: {response.text}"
    )

    # 2) Content-Type
    content_type = response.headers.get("Content-Type", "")
    assert "application/json" in content_type, (
        f"Se esperaba JSON en {url}, pero Content-Type fue: {content_type}"
    )

    # 3) Cuerpo JSON
    data = response.json()
    assert data.get("status") == "ok", (
        f"Campo 'status' inesperado en /health: {data}"
    )
    assert data.get("service") == "usuario", (
        f"Campo 'service' inesperado en /health: {data}"
    )
