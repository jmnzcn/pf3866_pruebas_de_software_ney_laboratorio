# Uso del servidor MCP como apoyo a las pruebas (`docs/MCP_TESTING.md`)

## 1. Objetivo

Este documento explica cómo se usa el servidor MCP (`pf3866_mcp/server.py`) como **apoyo para las pruebas de software** en el sistema basado en microservicios del laboratorio PF3866.

Con este servidor MCP se puede, desde un cliente MCP (por ejemplo, ChatGPT configurado con este servidor):

- Llamar a los microservicios reales (`GestionVuelos`, `GestionReservas`, `Usuario`).
- Leer y analizar pruebas automatizadas en `tests/api`.
- Ejecutar tests con `pytest` (todos, por archivo, por keyword o una sola prueba concreta).
- Leer documentación de pruebas y experimentos RAG en `docs/`.

---

## 2. Estructura relevante del proyecto

Rutas principales usadas por `server.py`:

```text
LABORATORIO/
├─ pf3866_mcp/
│  └─ server.py
├─ docs/
│  ├─ MCP_TESTING.md              (este archivo)
│  ├─ ENDPOINTS_Usuario.md
│  ├─ EXPERIMENTO_RAG_01_....md
│  └─ ...
└─ tests/
   └─ api/
      ├─ test_usuario_add_reservation_rag.py
      ├─ test_usuario_edit_payment_rag.py
      └─ ...


Dentro de server.py se calculan las rutas así:

SERVER_DIR = Path(__file__).resolve().parent
REPO_ROOT = SERVER_DIR.parent
DOCS_DIR = REPO_ROOT / "docs"
TESTS_API_DIR = REPO_ROOT / "tests" / "api"


3. Requisitos previos

En un entorno Python 3.11+:

python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt

Donde requirements.txt debe incluir, como mínimo:

fastmcp
requests
pytest

Además, para que las pruebas tengan sentido, los microservicios deben estar levantados. Por ejemplo, usando docker-compose en la raíz del proyecto:

docker-compose up -d


Esto debe dejar disponibles (según BASE_URLS en server.py):

GestionVuelos → http://localhost:5001

GestionReservas → http://localhost:5002

Usuario → http://localhost:5003

4. Levantar el servidor MCP

Desde la carpeta pf3866_mcp/:


cd pf3866_mcp
python server.py

Esto inicia el servidor MCP llamado pf3866-microservicios.

En el cliente MCP (por ejemplo ChatGPT con la opción de servidores MCP), se debe configurar este servidor para que quede disponible con ese nombre. Una vez configurado, el modelo podrá descubrir y usar todas las tools definidas en server.py.


5. Tools MCP disponibles
5.1 Llamadas a microservicios
get_health(service)

Parámetro:
service: "vuelos" | "reservas" | "usuario"

Función: hace GET /health en el microservicio correspondiente.

Uso típico (desde el modelo):

Comprueba el estado de salud del servicio usuario usando get_health.
Si el estado es correcto (HTTP 200), ejecuta las pruebas de API relacionadas con pagos.

add_airplane(model, manufacturer, year, capacity)

Llama a POST /add_airplane en GestionVuelos.

Se usa para generar datos de prueba (aviones de ejemplo) y verificar validaciones.

add_reservation(...)

Llama a POST /add_reservation en GestionReservas.

Permite crear reservas de prueba completas (código, pasaporte, vuelo, asiento, etc.).

call_endpoint(service, method, path, payload)

Tool genérica para cualquier endpoint de los microservicios.

Ejemplo de uso:

Llama con call_endpoint al endpoint GET /get_airplanes del servicio vuelos y analiza la respuesta.

edit_payment(...), edit_payment_sin_body(payment_id), edit_payment_body_minimo(...)

Llaman a PUT /edit_payment/<payment_id> en el servicio usuario.

Se usan para probar casos:

Sin cuerpo JSON (errores de validación).

Body mínimo válido (happy path).

Variaciones de monto, estado, método de pago, etc.

5.2 Ejecución de tests con pytest

Todas estas tools usan internamente:

def _run_pytest(pytest_args: list[str]) -> dict[str, Any]:
    # Ejecuta: pytest -q <pytest_args> en REPO_ROOT


La respuesta incluye:

ok: True si returncode == 0, False en caso contrario.

exit_code: código de salida de pytest.

command: comando exacto ejecutado.

stdout y stderr: salida textual de pytest.

run_all_api_tests()

Ejecuta todos los tests de tests/api:

Comando interno:

pytest -q tests/api


Uso típico:

Ejecuta run_all_api_tests y dime cuántos tests pasaron y cuáles fallaron.

run_api_test_file(test_file)

Ejecuta todos los tests de un archivo concreto de tests/api.

test_file es solo el nombre del archivo, por ejemplo:

"test_usuario_add_reservation_rag.py"

"test_usuario_edit_payment_rag.py"

Comando interno:

pytest -q tests/api/<test_file>


Uso típico:

Ejecuta solo el archivo test_usuario_add_reservation_rag.py con run_api_test_file y analiza los resultados.

run_api_tests_by_keyword(keyword)

Ejecuta tests filtrados con pytest -k <keyword> dentro de tests/api.

Comando interno:

pytest -q tests/api -k <keyword>


Uso típico:

Usa run_api_tests_by_keyword con keyword="edit_payment" y dime qué casos de pago fallan.

run_single_api_test(test_file, test_name)

Ejecuta una sola prueba dentro de tests/api, usando su nombre de función.

Parámetros:

test_file: nombre del archivo, por ejemplo:
"test_usuario_add_reservation_rag.py"

test_name: nombre de la función de test, por ejemplo:
"test_add_reservation_happy_path"

Comando interno:

pytest -q tests/api/test_usuario_add_reservation_rag.py::test_add_reservation_happy_path


Uso típico:

Ejecuta únicamente la prueba test_add_reservation_happy_path del archivo test_usuario_add_reservation_rag.py usando run_single_api_test.

5.3 Lectura de tests y documentación de pruebas

Estas tools no ejecutan nada; solo devuelven contenido de archivos para que el modelo lo lea y razone sobre él.

read_api_test_file(test_file)

Lee un archivo de tests/api y devuelve:

ok, path, content.

Ejemplo de test_file:

"test_usuario_add_reservation_rag.py"

"test_usuario_edit_payment_rag.py"

Uso típico:

Usa read_api_test_file("test_usuario_add_reservation_rag.py") para revisar qué casos se están probando y propón nuevos casos de borde.

read_experimento_doc(nombre_md)

Lee un archivo .md dentro de docs/ y devuelve:

ok, path, content.

Ejemplos de nombre_md:

"EXPERIMENTO_RAG_01_usuario_add_reservation.md"

"ENDPOINTS_Usuario.md"

Uso típico:

Lee EXPERIMENTO_RAG_01_usuario_add_reservation.md con read_experimento_doc y, basándote en esa descripción, revisa si las pruebas implementadas en test_usuario_add_reservation_rag.py son suficientes.

6. Flujos de trabajo recomendados
6.1 Flujo A: pruebas completas del servicio Usuario (pagos)

Comprobar que el microservicio está arriba:

Tool: get_health(service="usuario").

Revisar el diseño de pruebas / experimentos RAG (opcional):

Tool: read_experimento_doc("EXPERIMENTO_RAG_XX_usuario_edit_payment.md") (si existe).

Revisar el archivo de tests:

Tool: read_api_test_file("test_usuario_edit_payment_rag.py").

Ejecutar todas las pruebas de pagos:

Tool: run_api_tests_by_keyword("edit_payment")
o

Tool: run_api_test_file("test_usuario_edit_payment_rag.py").

Analizar stdout/stderr de pytest para ver qué casos fallan y por qué.

6.2 Flujo B: diseño y ejecución de pruebas para /add_reservation

Leer el experimento RAG/documentación del endpoint:

Tool: read_experimento_doc("EXPERIMENTO_RAG_01_usuario_add_reservation.md").

Leer el archivo de pruebas actual:

Tool: read_api_test_file("test_usuario_add_reservation_rag.py").

Proponer nuevos casos de pruebas (modelo) y, si es necesario, actualizar el archivo de tests en el repositorio.

Ejecutar una sola prueba concreta de happy path:

Tool:
run_single_api_test("test_usuario_add_reservation_rag.py", "test_add_reservation_happy_path").

Ejecutar todas las pruebas de ese archivo:

Tool: run_api_test_file("test_usuario_add_reservation_rag.py").

6.3 Flujo C: regresión completa de API

Cuando se hace un cambio grande en la lógica de negocio:

Asegurar que todos los microservicios están levantados (docker-compose up -d).

Ejecutar todas las pruebas de API:

Tool: run_all_api_tests().

Revisar el resumen de pytest (ok, stdout, stderr) y, si hay fallos, usar las otras tools (read_api_test_file, call_endpoint, etc.) para investigar.

7. Conclusión

El servidor MCP de pf3866_mcp/server.py integra:

Microservicios reales (vuelos, reservas, usuarios).

Pruebas automatizadas en tests/api (ejecutadas vía pytest).

Documentación y experimentos RAG en docs/.

Desde un cliente MCP, esto permite un flujo completo donde el modelo:

Lee documentación y experimentos RAG.

Inspecciona y mejora las pruebas automatizadas.

Ejecuta las pruebas (todas, por archivo, por keyword o una sola).

Llama a los endpoints de los microservicios para validar comportamientos en tiempo real.

::contentReference[oaicite:0]{index=0}
