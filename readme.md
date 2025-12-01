# FlightBooking – Laboratorio PF3866
## Estudiante: NeyFred Jimenez Campos
## ID estudiantil: B03230

Este repositorio contiene el entorno de laboratorio **FlightBooking**, diseñado para practicar y evaluar estrategias de pruebas automatizadas sobre una arquitectura de microservicios. El sistema simula un flujo básico de reserva de vuelos y está compuesto por tres servicios principales:

- **GestiónVuelos** (`http://localhost:5001`): administra aviones, rutas de vuelo y asientos.
- **GestiónReservas** (`http://localhost:5002`): gestiona reservas y pagos asociados.
- **Usuario** (`http://localhost:5003`): actúa como fachada de orquestación, exponiendo operaciones de “usuario final” (crear reservas, crear/cancelar pagos, consultar rutas y asientos, etc.).

Cada microservicio expone una interfaz de prueba manual mediante **Swagger UI** en rutas del tipo:

- `http://localhost:5001/apidocs/#/`
- `http://localhost:5002/apidocs/#/`
- `http://localhost:5003/apidocs/#/`

Sobre este sistema se construyeron:

- Una batería de **pruebas automatizadas de API** en `tests/api/`, incluyendo casos clásicos (CRUD, validaciones, errores de negocio) y casos generados/inspirados mediante un enfoque tipo **RAG** (archivos `_rag.py`).
- Un servidor **MCP** en `pf3866_mcp/server.py` que actúa como “QA Copilot”, permitiendo:
  - Consultar el estado de salud de los microservicios.
  - Invocar endpoints de forma programática.
  - Ejecutar suites de `pytest` (por microservicio o completas).
  - Leer archivos de código, documentación y tests desde el propio repositorio.

Además, el proyecto incluye un mecanismo básico de **recolección de métricas** (reportes JUnit XML y CSVs en la carpeta `metrics/`) para analizar la ejecución de las suites y servir como base para futuros KPIs de tiempo de diseño, cobertura, precisión y estabilidad de las pruebas.
