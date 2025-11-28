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
import logging


logger = logging.getLogger(__name__)

# Crear el servidor MCP
mcp = FastMCP("pf3866-microservicios", stateless_http=True)

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
    method: Literal["GET", "POST", "PUT", "PATCH", "DELETE"],
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

    if not path.startswith("/"):
        path = "/" + path

    url = f"{base_url}{path}"
    try:
        resp = requests.request(method=method, url=url, json=json_body, timeout=timeout)
    except requests.RequestException as e:
        logger.error("Error de red llamando %s%s: %s", base_url, path, e)
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
    """Obtiene el estado de salud (/health) del microservicio especificado."""
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
def add_reservation_gestionreservas(
    airplane_id: int,
    airplane_route_id: int,
    passport_number: str,
    full_name: str,
    email: str,
    phone_number: str,
    emergency_contact_name: str,
    emergency_contact_phone: str,
    seat_number: str,
    status: str = "Reservado",
) -> dict[str, Any]:
    """
    Crea una reserva en GestionReservas llamando a /add_reservation.
    """
    body = {
        "airplane_id": airplane_id,
        "airplane_route_id": airplane_route_id,
        "passport_number": passport_number,
        "full_name": full_name,
        "email": email,
        "phone_number": phone_number,
        "emergency_contact_name": emergency_contact_name,
        "emergency_contact_phone": emergency_contact_phone,
        "seat_number": seat_number,
        "status": status,
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
    """Edita un pago en el microservicio Usuario llamando a /usuario/edit_payment/<payment_id>."""
    path = f"/usuario/edit_payment/{payment_id}"
    return _call_service(
        service="usuario",
        method="PUT",
        path=path,
        json_body=body,
    )


@mcp.tool()
def edit_payment_sin_body(payment_id: str) -> dict[str, Any]:
    """Escenario de prueba: editar un pago SIN cuerpo JSON en Usuario."""
    path = f"/usuario/edit_payment/{payment_id}"
    return _call_service(
        service="usuario",
        method="PUT",
        path=path,
        json_body=None,
    )



@mcp.tool()
def smoke_test_usuario() -> dict[str, Any]:
    """
    Ejecuta un pequeño smoke test sobre el microservicio Usuario:
    - GET /get_all_airplanes_routes
    - GET /get_all_reservations
    - GET /get_all_payments
    """
    results = {}

    results["routes"] = _call_service("usuario", "GET", "/get_all_airplanes_routes")
    results["reservations"] = _call_service("usuario", "GET", "/get_all_reservations")
    results["payments"] = _call_service("usuario", "GET", "/get_all_payments")

    return results


@mcp.tool()
def get_all_reservations_from_reservas() -> dict[str, Any]:
    """
    Envuelve GET /get_fake_reservations en GestiónReservas.
    Útil para inspeccionar las reservas de prueba generadas al arrancar.
    """
    return _call_service("reservas", "GET", "/get_fake_reservations")


@mcp.tool()
def get_all_fake_payments_from_reservas() -> dict[str, Any]:
    """
    Envuelve GET /get_all_fake_payments en GestiónReservas.
    """
    return _call_service("reservas", "GET", "/get_all_fake_payments")


@mcp.tool()
def get_all_airplanes_routes_from_vuelos() -> dict[str, Any]:
    """
    Envuelve GET /get_all_airplanes_routes en GestiónVuelos.
    """
    return _call_service("vuelos", "GET", "/get_all_airplanes_routes")



# ---------- HELPER: EJECUTAR PYTEST ----------

def _run_pytest(pytest_args: list[str]) -> dict[str, Any]:
    """
    Ejecuta pytest con los argumentos dados y devuelve un resumen estructurado.

    - pytest_args: lista de argumentos, por ejemplo:
      ["tests/api"] o ["tests/api/test_usuario_add_reservation_rag.py"].
    """
    cmd = ["pytest", "-vv", "-s"] + pytest_args  # -vv para detalle, -s para mostrar prints
    try:
        result = subprocess.run(
            cmd,
            cwd=REPO_ROOT,
            capture_output=True,  # seguimos capturando para devolverlo por MCP
            text=True,
            timeout=300,
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
    """
    return _read_text_from_dir(TESTS_API_DIR, test_file, "archivo de test")


@mcp.tool()
def read_experimento_doc(nombre_md: str) -> dict[str, Any]:
    """
    Lee un archivo de docs/ y devuelve su contenido.
    """
    return _read_text_from_dir(DOCS_DIR, nombre_md, "archivo .md")


@mcp.tool()
def list_experimento_docs(prefix: str = "EXPERIMENTO_RAG") -> dict[str, Any]:
    """
    Lista los archivos .md de docs/ que empiezan por cierto prefijo,
    por ejemplo 'EXPERIMENTO_RAG' o 'ENDPOINTS_'.
    """
    docs = sorted(f.name for f in DOCS_DIR.glob(f"{prefix}*.md"))
    return {
        "ok": True,
        "prefix": prefix,
        "count": len(docs),
        "docs": docs,
    }


@mcp.tool()
def list_api_test_files(pattern: str = "test_usuario_*") -> dict[str, Any]:
    """
    Lista archivos de tests en tests/api según un patrón glob.

    Ejemplos:
    - pattern='test_usuario_*_rag.py'
    - pattern='test_gestionreservas_*'
    """
    tests = sorted(f.name for f in TESTS_API_DIR.glob(pattern))
    return {
        "ok": True,
        "pattern": pattern,
        "count": len(tests),
        "tests": tests,
    }


@mcp.tool()
def list_rag_docs(
    servicio: Literal["usuario", "gestionreservas", "vuelos"] | None = None
) -> dict[str, Any]:
    """
    Lista los markdown de experimentos RAG, opcionalmente filtrados por microservicio.
    - servicio=None → todos los EXPERIMENTO_RAG_*.md
    - servicio="usuario" → EXPERIMENTO_RAG_*_usuario_*.md
    etc.
    """
    if servicio is None:
        pattern = "EXPERIMENTO_RAG_*.md"
    else:
        pattern = f"EXPERIMENTO_RAG_*_{servicio}_*.md"

    docs = sorted(f.name for f in DOCS_DIR.glob(pattern))
    return {
        "ok": True,
        "servicio": servicio,
        "count": len(docs),
        "docs": docs,
    }


def _read_repo_file(relative_path: str) -> dict[str, Any]:
    """
    Lee un archivo dentro del repositorio usando una ruta relativa a REPO_ROOT.

    Ejemplos válidos:
    - 'GestionVuelos/app.py'
    - 'GestionReservas/app.py'

    No permite rutas absolutas ni subir directorios (..).
    """
    rel = Path(relative_path)

    # Proteger contra rutas absolutas o traversal tipo "../"
    if rel.is_absolute() or ".." in rel.parts:
        return {
            "ok": False,
            "error": "La ruta debe ser relativa al repo y no puede contener '..'.",
        }

    path = REPO_ROOT / rel

    if not path.is_file():
        return {
            "ok": False,
            "path": str(path),
            "error": "No se encontró el archivo en la ruta esperada.",
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
def run_usuario_rag_tests() -> dict[str, Any]:
    """
    Ejecuta solo los tests RAG del microservicio Usuario
    (asumiendo que sus nombres contienen 'usuario' y '_rag').
    """
    return _run_pytest(["tests/api", "-k", "usuario and rag"])


@mcp.tool()
def run_gestionreservas_rag_tests() -> dict[str, Any]:
    """
    Ejecuta solo los tests RAG del microservicio GestiónReservas.
    """
    return _run_pytest(["tests/api", "-k", "gestionreservas and rag"])


@mcp.tool()
def run_gestionvuelos_rag_tests() -> dict[str, Any]:
    """
    Ejecuta solo los tests RAG del microservicio GestiónVuelos.
    """
    return _run_pytest(["tests/api", "-k", "vuelos and rag"])


def _read_text_from_dir(base_dir: Path, name: str, description: str) -> dict[str, Any]:
    """
    Helper genérico para leer un archivo de texto desde un directorio base.
    description: texto para mensajes de error, por ejemplo 'archivo de test' o 'archivo .md'.
    """
    if "/" in name or "\\" in name:
        return {
            "ok": False,
            "error": "Solo se permite el nombre del archivo, sin rutas.",
        }

    path = base_dir / name

    if not path.is_file():
        return {
            "ok": False,
            "path": str(path),
            "error": f"No se encontró el {description} en la ruta esperada.",
        }

    try:
        content = path.read_text(encoding="utf-8")
    except Exception as e:
        return {
            "ok": False,
            "path": str(path),
            "error": f"Error al leer el {description}: {e}",
        }

    return {
        "ok": True,
        "path": str(path),
        "content": content,
    }


@mcp.tool()
def list_all_md_docs() -> dict[str, Any]:
    """
    Lista todos los archivos .md dentro de docs/.

    Útil para comandos tipo:
    - "lista todos los documentos .md que hay en la carpeta docs"
    """
    docs = sorted(f.name for f in DOCS_DIR.glob("*.md"))
    return {
        "ok": True,
        "count": len(docs),
        "docs": docs,
    }


@mcp.tool()
def read_all_md_docs() -> dict[str, Any]:
    """
    Devuelve el contenido de todos los archivos .md dentro de docs/.
    """
    results: list[dict[str, Any]] = []
    for path in sorted(DOCS_DIR.glob("*.md")):
        try:
            content = path.read_text(encoding="utf-8")
            results.append({
                "name": path.name,
                "ok": True,
                "content": content,
            })
        except Exception as e:
            results.append({
                "name": path.name,
                "ok": False,
                "error": f"Error al leer el archivo: {e}",
            })

    return {
        "ok": True,
        "count": len(results),
        "docs": results,
    }


@mcp.tool()
def read_repo_file(relative_path: str) -> dict[str, Any]:
    """
    Lee un archivo arbitrario del repositorio usando una ruta relativa a REPO_ROOT.

    Ejemplos de uso:
    - 'GestionVuelos/app.py'
    - 'GestionReservas/app.py'
    """
    return _read_repo_file(relative_path)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    mcp.run(
        transport="streamable-http",
        host="0.0.0.0",  # para exponerlo fuera de la máquina
        port=8000,
        path="/mcp",     # ruta HTTP del endpoint MCP
    )
