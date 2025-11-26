# pf3866_mcp/server.py
"""
Servidor MCP para el laboratorio PF3866.

Expone herramientas que llaman a los microservicios:
- GestionVuelos   -> http://localhost:5001
- GestionReservas -> http://localhost:5002
- Usuario         -> http://localhost:5003

Estas herramientas se usarán desde ChatGPT/QA-Copilot como apoyo
para diseñar y ejecutar pruebas sobre los endpoints.
"""

from typing import Any, Literal
import subprocess
from pathlib import Path

import requests
from fastmcp import FastMCP

# Crear el servidor MCP
mcp = FastMCP("pf3866-microservicios")

# Mapear nombres lógicos de servicio a sus URLs locales
BASE_URLS: dict[str, str] = {
    "vuelos": "http://localhost:5001",
    "reservas": "http://localhost:5002",
    "usuario": "http://localhost:5003",
}

SERVER_DIR = Path(__file__).resolve().parent
REPO_ROOT = SERVER_DIR.parent           # carpeta raíz del repo (LABORATORIO)
DOCS_DIR = REPO_ROOT / "docs"
TESTS_API_DIR = REPO_ROOT / "tests" / "api"


def _call_service(
    service: Literal["vuelos", "reservas", "usuario"],
    method: str,
    path: str,
    json_body: dict[str, Any] | None = None,
    timeout: float = 5.0,
) -> dict[str, Any]:
    """
    Llama a un endpoint de cualquiera de los microservicios
    y devuelve un resultado estructurado.
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


# ---------- TOOLS: LLAMADAS A MICROSERVICIOS ----------

@mcp.tool()
def get_health(
    service: Literal["vuelos", "reservas", "usuario"],
) -> dict[str, Any]:
    """Obtiene el estado de salud (/health) de uno de los microservicios."""
    return _call_service(service, "GET", "/health")


@mcp.tool()
def add_airplane(
    model: str,
    manufacturer: str,
    year: int,
    capacity: int,
) -> dict[str, Any]:
    """Crea un avión de prueba llamando a /add_airplane en GestionVuelos."""
    body = {
        "airplane_id": "",
        "model": model,
        "manufacturer": manufacturer,
        "year": year,
        "capacity": capacity,
    }
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
    """Crea una reserva de prueba llamando al microservicio GestionReservas."""
    body = {
        "reservation_code": reservation_code,
        "passport_number": passport_number,
        "full_name": full_name,
        "email": email,
        "phone_number": phone_number,
        "flight_id": flight_id,
        "seat_number": seat_number,
    }
    return _call_service("reservas", "POST", "/add_reservation", json_body=body)


@mcp.tool()
def call_endpoint(
    service: Literal["vuelos", "reservas", "usuario"],
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
    path: str,
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Herramienta genérica para probar cualquier endpoint de los microservicios."""
    return _call_service(service, method, path, json_body=payload)


@mcp.tool()
def edit_payment(
    payment_id: str,
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Edita un pago en el microservicio Usuario llamando a /edit_payment/<payment_id>."""
    path = f"/edit_payment/{payment_id}"
    return _call_service(
        service="usuario",
        method="PUT",
        path=path,
        json_body=body,
    )


@mcp.tool()
def edit_payment_sin_body(payment_id: str) -> dict[str, Any]:
    """Escenario de prueba: editar un pago SIN cuerpo JSON."""
    path = f"/edit_payment/{payment_id}"
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
    """Escenario de prueba: editar un pago con un body JSON mínimo válido."""
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


# ---------- HELPER: EJECUTAR PYTEST ----------

def _run_pytest(pytest_args: list[str]) -> dict[str, Any]:
    """
    Ejecuta pytest con los argumentos dados y devuelve un resumen estructurado.

    - pytest_args: lista de argumentos, por ejemplo:
      ["tests/api"] o ["tests/api/test_usuario_add_reservation_rag.py"].
    """
    cmd = ["pytest", "-q"] + pytest_args
    try:
        result = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=180,  # ajusta si necesitas más tiempo
        )
    except Exception as e:
        return {
            "ok": False,
            "command": " ".join(cmd),
            "error": f"Error al ejecutar pytest: {e}",
        }

    return {
        "ok": result.returncode == 0,
        "exit_code": result.returncode,
        "command": " ".join(cmd),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


# ---------- TOOLS: EJECUTAR TESTS ----------

@mcp.tool()
def run_all_api_tests() -> dict[str, Any]:
    """
    Ejecuta todos los tests de la carpeta tests/api con pytest.

    Útil para lanzar la batería completa de pruebas de API.
    """
    return _run_pytest(["tests/api"])


@mcp.tool()
def run_api_test_file(test_file: str) -> dict[str, Any]:
    """
    Ejecuta un archivo de test dentro de tests/api con pytest.

    Ejemplo de uso:
    - 'test_usuario_add_reservation_rag.py'
    """
    if "/" in test_file or "\\" in test_file:
        return {
            "ok": False,
            "error": "Solo se permite el nombre del archivo, sin rutas.",
        }

    path = f"tests/api/{test_file}"
    return _run_pytest([path])


@mcp.tool()
def run_api_tests_by_keyword(keyword: str) -> dict[str, Any]:
    """
    Ejecuta tests de tests/api filtrados con pytest -k <keyword>.

    Ejemplos:
    - keyword='edit_payment'
    - keyword='rag'
    """
    return _run_pytest(["tests/api", "-k", keyword])


@mcp.tool()
def run_single_api_test(test_file: str, test_name: str) -> dict[str, Any]:
    """
    Ejecuta una sola prueba dentro de tests/api usando su nombre de función.

    Ejemplo:
    - test_file='test_usuario_add_reservation_rag.py'
    - test_name='test_add_reservation_happy_path'
    """
    # Solo nombre de archivo, sin rutas
    if "/" in test_file or "\\" in test_file:
        return {
            "ok": False,
            "error": "Solo se permite el nombre del archivo, sin rutas.",
        }

    # Node id de pytest: tests/api/archivo.py::nombre_de_test
    node_id = f"tests/api/{test_file}::{test_name}"
    return _run_pytest([node_id])


# ---------- TOOLS: LEER TESTS Y DOCS ----------

@mcp.tool()
def read_api_test_file(test_file: str) -> dict[str, Any]:
    """
    Lee un archivo de tests en tests/api y devuelve su contenido.

    Ejemplo:
    - 'test_usuario_add_reservation_rag.py'
    """
    if "/" in test_file or "\\" in test_file:
        return {
            "ok": False,
            "error": "Solo se permite el nombre del archivo, sin rutas.",
        }

    path = TESTS_API_DIR / test_file

    if not path.is_file():
        return {
            "ok": False,
            "path": str(path),
            "error": "No se encontró el archivo de test en la ruta esperada.",
        }

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return {
            "ok": False,
            "path": str(path),
            "error": f"Error al leer el archivo: {e}",
        }

    return {
        "ok": True,
        "path": str(path),
        "content": content,
    }


@mcp.tool()
def read_experimento_doc(nombre_md: str) -> dict[str, Any]:
    """
    Lee un archivo de docs/ y devuelve su contenido.

    Ejemplos:
    - 'EXPERIMENTO_RAG_01_usuario_add_reservation.md'
    - 'ENDPOINTS_Usuario.md'
    """
    if "/" in nombre_md or "\\" in nombre_md:
        return {
            "ok": False,
            "error": "Solo se permite el nombre del archivo, sin rutas.",
        }

    path = DOCS_DIR / nombre_md

    if not path.is_file():
        return {
            "ok": False,
            "path": str(path),
            "error": "No se encontró el archivo .md en la ruta esperada.",
        }

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return {
            "ok": False,
            "path": str(path),
            "error": f"Error al leer el archivo: {e}",
        }

    return {
        "ok": True,
        "path": str(path),
        "content": content,
    }


if __name__ == "__main__":
    mcp.run()
