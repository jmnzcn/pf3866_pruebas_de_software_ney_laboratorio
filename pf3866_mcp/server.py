# mcp/server.py
"""
Servidor MCP para el laboratorio PF3866.

Expone herramientas que llaman a los microservicios:
- GestionVuelos   -> http://localhost:5001
- GestionReservas -> http://localhost:5002
- Usuario         -> http://localhost:5003

Estas herramientas se usarán desde ChatGPT/QA-Copilot como apoyo
para diseñar y ejecutar pruebas sobre los endpoints.
"""

import os
from typing import Any, Literal

import requests
from fastmcp import FastMCP # FastMCP del SDK oficial MCP :contentReference[oaicite:1]{index=1}

# Crear el servidor MCP
mcp = FastMCP("pf3866-microservicios")

# Mapear nombres lógicos de servicio a sus URLs locales
BASE_URLS: dict[str, str] = {
    "vuelos": "http://localhost:5001",
    "reservas": "http://localhost:5002",
    "usuario": "http://localhost:5003",
}


def _call_service(
    service: Literal["vuelos", "reservas", "usuario"],
    method: str,
    path: str,
    json_body: dict[str, Any] | None = None,
    timeout: float = 5.0,
) -> dict[str, Any]:
    """
    Función interna para llamar a un endpoint de cualquiera de los microservicios.

    Devuelve un dict estructurado para que el modelo pueda razonar sobre:
    - status: código HTTP
    - ok: True/False
    - url: URL llamada
    - body: JSON o texto devuelto por el servicio
    """
    base_url = BASE_URLS.get(service)
    if base_url is None:
        raise ValueError(f"Servicio desconocido: {service}")

    url = f"{base_url}{path}"
    try:
        resp = requests.request(method=method, url=url, json=json_body, timeout=timeout)
    except requests.RequestException as e:
        return {
            "status": 0,
            "ok": False,
            "url": url,
            "body": f"Error de red al llamar {url}: {e}",
        }

    try:
        body: Any = resp.json()
    except ValueError:
        body = resp.text

    return {
        "status": resp.status_code,
        "ok": resp.ok,
        "url": url,
        "body": body,
    }


@mcp.tool()
def get_health(
    service: Literal["vuelos", "reservas", "usuario"],
) -> dict[str, Any]:
    """
    Obtiene el estado de salud (/health) de uno de los microservicios.

    Útil para:
    - Verificar si el servicio está arriba antes de correr pruebas.
    - Usar desde ChatGPT para decidir qué pruebas ejecutar.
    """
    # Ajusta la ruta si tu endpoint de salud se llama distinto
    return _call_service(service, "GET", "/health")


@mcp.tool()
def add_airplane(
    model: str,
    manufacturer: str,
    year: int,
    capacity: int,
) -> dict[str, Any]:
    """
    Crea un avión de prueba llamando a /add_airplane en GestionVuelos.

    Desde ChatGPT se puede usar para:
    - Generar datos previos a una prueba (precondiciones).
    - Verificar validaciones de año/capacidad/modelo.
    """
    body = {
        "airplane_id": "",  # si en tu API se genera automáticamente, puedes omitirlo
        "model": model,
        "manufacturer": manufacturer,
        "year": year,
        "capacity": capacity,
    }
    # Ajusta la ruta al endpoint real si es necesario
    return _call_service("vuelos", "POST", "/add_airplane", json_body=body)


@mcp.tool()
def add_reservation(
    reservation_code: str,
    passport_number: str,
    full_name: str,
    email: str,
    phone_number: str,
    flight_id: str,
    seat_number: str,
) -> dict[str, Any]:
    """
    Crea una reserva de prueba llamando al microservicio GestionReservas.

    Permite que el modelo:
    - Genere casos de prueba completos de flujo de reserva.
    - Testee validaciones de campos obligatorios/formato.
    """
    body = {
        "reservation_code": reservation_code,
        "passport_number": passport_number,
        "full_name": full_name,
        "email": email,
        "phone_number": phone_number,
        "flight_id": flight_id,
        "seat_number": seat_number,
        # Puedes añadir aquí más campos según tu API:
        # "emergency_contact_name": "...",
        # "emergency_contact_phone": "...",
        # "status": "PENDING",
        # "issued_at": "2025-01-01T00:00:00Z",
    }
    # Ajusta la ruta al endpoint real de creación de reservas
    return _call_service("reservas", "POST", "/add_reservation", json_body=body)


@mcp.tool()
def call_endpoint(
    service: Literal["vuelos", "reservas", "usuario"],
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
    path: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Herramienta genérica para probar cualquier endpoint de los microservicios.

    Ejemplos de uso desde el modelo (en lenguaje natural):
    - "Llama al endpoint POST /add_airplanes_routes en el servicio 'vuelos'
       con este body JSON..."
    - "Haz un GET /get_airplanes en 'vuelos' para ver qué devuelve"
    """
    return _call_service(service, method, path, json_body=payload)


@mcp.tool()
def edit_payment(
    payment_id: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Edita un pago en el microservicio Usuario llamando al endpoint /edit_payment/<payment_id>.

    Uso típico desde ChatGPT / QA-Copilot:
    - Probar validaciones cuando el cuerpo JSON está vacío o ausente
    - Probar cambios válidos de un pago existente
    - Reproducir los casos cubiertos en tests/api/test_usuario_edit_payment_rag.py

    Parámetros:
    - payment_id: identificador del pago (por ejemplo 'PAY123456')
    - body: JSON con los cambios del pago. Si es None, se simula el caso
      de "no se recibió cuerpo JSON".
    """
    path = f"/edit_payment/{payment_id}"
    return _call_service(
        service="usuario",
        method="PUT",
        path=path,
        json_body=body,
    )


@mcp.tool()
def edit_payment_sin_body(payment_id: str) -> dict[str, Any]:
    """
    Escenario de prueba: editar un pago SIN cuerpo JSON.

    Equivale a llamar PUT /edit_payment/<payment_id> sin JSON.
    Se usa para verificar que el servicio devuelve 400 y el mensaje
    tipo "No se recibió cuerpo JSON" u otro mensaje de error esperado.
    """
    path = f"/edit_payment/{payment_id}"
    # Notar que pasamos json_body=None para simular ausencia de JSON
    return _call_service(
        service="usuario",
        method="PUT",
        path=path,
        json_body=None,
    )


@mcp.tool()
def edit_payment_body_minimo(
    payment_id: str,
    monto: float,
    estado: str,
    metodo: str | None = None,
) -> dict[str, Any]:
    """
    Escenario de prueba: editar un pago con un body JSON mínimo válido.

    Ajusta los nombres de los campos según tu API real.
    Ejemplo de uso: probar el caso "happy path" y luego construir
    variantes con valores inválidos (monto negativo, estado raro, etc.).
    """
    body: dict[str, Any] = {
        "amount": monto,
        "status": estado,
    }
    if metodo is not None:
        body["method"] = metodo

    path = f"/edit_payment/{payment_id}"
    return _call_service(
        service="usuario",
        method="PUT",
        path=path,
        json_body=body,
    )




