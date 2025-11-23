# EXPERIMENTO_RAG_08_usuario_get_reservations

Pruebas de contrato para los endpoints de **consulta de reservas** expuestos por el microservicio **Usuario**, integrados con el enfoque de **RAG/MCP**.

Archivo de pruebas asociado (propuesto):  
`tests/api/test_usuario_get_reservations_rag.py`


## 1. Descripción general

Este experimento valida el comportamiento del microservicio **Usuario** cuando actúa como fachada de lectura hacia **GestiónReservas** para:

- Consultar una reserva específica por su **código**.
- Consultar una reserva específica por su **ID numérico**.
- Listar todas las reservas existentes (o indicar claramente que no hay reservas).

Además, se definen **IDs de casos** (`case_id`) reutilizables como unidades de conocimiento que pueden ser usadas por un servidor **MCP** y un pipeline **RAG** para:

- Recuperar automáticamente documentación relevante (Swagger, código, este `.md`).
- Explicar por qué cada caso existe.
- Sugerir nuevos casos de prueba o variaciones de entrada.


## 2. Objetivo

1. Verificar que el microservicio **Usuario**:
   - Aplique correctamente las validaciones de entrada para **código** e **ID** de reserva.
   - Propague adecuadamente los códigos de error provenientes de **GestiónReservas** (`404`, códigos 5xx, etc.).
   - Devuelva respuestas consistentes en los casos felices (`200`) y cuando no existan reservas.

2. Definir un set de casos de prueba estructurados que puedan ser:
   - Ejecutados vía `pytest` como pruebas de contrato.
   - Consumidos por un asistente de pruebas basado en **RAG/MCP** para razonar sobre escenarios y fallos.


## 3. Endpoints bajo prueba

| Endpoint                                         | Método | Descripción breve                                                            |
|--------------------------------------------------|--------|-------------------------------------------------------------------------------|
| `/get_reservation_by_code/<string:reservation_code>` | GET    | Devuelve una reserva específica, validada con `ReservationSchema`.           |
| `/get_reservation_by_id/<int:reservation_id>`    | GET    | Devuelve una reserva específica por ID numérico, validada con `ReservationSchema`. |
| `/get_all_reservations`                          | GET    | Lista todas las reservas o indica claramente que no hay reservas registradas. |


## 4. Casos de prueba propuestos

A continuación se listan los casos de prueba pensados tanto para automatización con `pytest` como para indexación RAG.  
Los `case_id` sugeridos pueden usarse literal en el código de pruebas y en las consultas al MCP.


### 4.1. `GET /get_reservation_by_code/<string:reservation_code>`

#### 4.1.1 Casos de error

| case_id                            | Entrada (path)                                        | Esperado       | Tipo                  | Mensaje esperado (substring)                                   |
|------------------------------------|-------------------------------------------------------|----------------|-----------------------|-----------------------------------------------------------------|
| `USR_RES_CODE_VACIO_400`          | `/get_reservation_by_code/%20%20%20`                  | 400            | Validación local      | `El código de reserva es obligatorio y debe ser texto válido.` |
| `USR_RES_CODE_NO_EXISTE_404`      | `/get_reservation_by_code/ZZZ999`                     | 404            | No encontrado         | `Reserva no encontrada en GestiónReservas`                      |
| `USR_RES_CODE_BACKEND_ERROR_5XX`  | (cualquier code que provoque error en GestiónReservas)| 500            | Error backend         | `Error consultando reserva. Código:`                           |
| `USR_RES_CODE_VALIDACION_500`     | Código que exista pero cuyos datos no pasen Marshmallow | 500         | Error de validación   | `Error de validación en los datos de la reserva`               |

Notas:

- `USR_RES_CODE_VACIO_400` simula un código compuesto solo por espacios (URL-encoded). Dentro de Usuario, el `strip()` deja la cadena vacía ⇒ 400.
- `USR_RES_CODE_BACKEND_ERROR_5XX` y `USR_RES_CODE_VALIDACION_500` pueden ser difíciles de provocar de forma “natural”; se consideran escenarios de interés para RAG (análisis de código y diseño de pruebas), aunque el test automatizado puede o no implementarlos explícitamente según el entorno.


#### 4.1.2 Caso feliz

| case_id                     | Estrategia                                                                          | Esperado |
|-----------------------------|--------------------------------------------------------------------------------------|----------|
| `USR_RES_CODE_OK_200`      | 1) Obtener una reserva existente (p. ej. desde `/get_all_reservations`).<br>2) Tomar su `reservation_code`.<br>3) Llamar a `/get_reservation_by_code/<code>`. | 200      |

Validaciones mínimas en el caso feliz:

- `status_code == 200`
- La respuesta es un objeto JSON (`dict`).
- Contiene al menos: `reservation_id`, `reservation_code`, `airplane_id`, `seat_number`, `status`, etc.
- El `reservation_code` devuelto coincide con el solicitado.


### 4.2. `GET /get_reservation_by_id/<int:reservation_id>`

#### 4.2.1 Casos de error

| case_id                            | Entrada (path)                             | Esperado       | Tipo                    | Mensaje esperado (substring)                         |
|------------------------------------|--------------------------------------------|----------------|-------------------------|------------------------------------------------------|
| `USR_RES_ID_CERO_400`             | `/get_reservation_by_id/0`                 | 400            | Validación local        | `El ID debe ser un número entero positivo.`         |
| `USR_RES_ID_NEGATIVO_404`         | `/get_reservation_by_id/-1`                | 404            | Ruta no encontrada (Flask) | `Not Found` (HTML)                                |
| `USR_RES_ID_NO_EXISTE_404`        | `/get_reservation_by_id/999999`            | 404            | No encontrado           | `Reserva no encontrada en GestiónReservas`          |
| `USR_RES_ID_BACKEND_ERROR_5XX`    | (ID que cause error en GestiónReservas)    | 5xx            | Error backend           | `Error consultando reserva. Código:`                |
| `USR_RES_ID_VALIDACION_500`       | ID existente pero con datos inválidos      | 500            | Error de validación     | `Error de validación en los datos de la reserva`    |

Notas:

- Debido al converter `<int:reservation_id>`, un ID negativo **no matchea** la ruta y Flask responde directamente 404 HTML; por eso `USR_RES_ID_NEGATIVO_404` se considera un caso de contrato (aunque no tenga JSON).
- `USR_RES_ID_BACKEND_ERROR_5XX` y `USR_RES_ID_VALIDACION_500` nuevamente son útiles a nivel de análisis RAG, aunque en automatización podrían omitirse o marcarse como pendientes.


#### 4.2.2 Caso feliz

| case_id                   | Estrategia                                                                          | Esperado |
|---------------------------|--------------------------------------------------------------------------------------|----------|
| `USR_RES_ID_OK_200`      | 1) Obtener una reserva existente desde `/get_all_reservations`.<br>2) Tomar su `reservation_id`.<br>3) Llamar a `/get_reservation_by_id/<id>`. | 200      |

Validaciones mínimas:

- `status_code == 200`
- La respuesta es un `dict`.
- El `reservation_id` devuelto coincide con el solicitado.
- Campos clave presentes y con formato coherente (según `ReservationSchema`).


### 4.3. `GET /get_all_reservations`

Este endpoint encapsula varias posibles respuestas según lo que devuelva **GestiónReservas** (`/get_fake_reservations`).

#### 4.3.1 Casos principales

| case_id                             | Escenario                                                          | Esperado | Tipo                         | Mensaje / Validación esperada                                      |
|-------------------------------------|--------------------------------------------------------------------|----------|------------------------------|----------------------------------------------------------------------|
| `USR_RES_ALL_SIN_RESERVAS_200`     | GestiónReservas devuelve 204 o lista vacía                         | 200      | No hay datos                 | `{"message": "No hay reservas registradas."}`                       |
| `USR_RES_ALL_OK_LIST_200`          | GestiónReservas devuelve lista no vacía de reservas válidas        | 200      | Lista de reservas            | JSON es lista; cada elemento pasa `ReservationSchema(many=True)`    |
| `USR_RES_ALL_BACKEND_ERROR_PROPAGADO` | GestiónReservas devuelve código diferente de 200/204           | mismo código que backend | Propagación de error | Body: `{"message": "Error al consultar reservas. Código de respuesta: X"}` |
| `USR_RES_ALL_VALIDACION_500`       | Lista de reservas con estructura inválida                          | 500      | Error de validación          | `{"message": "Error de validación en las reservas", "errors": ...}` |

Notas:

- Para `USR_RES_ALL_OK_LIST_200`, el test puede limitarse a comprobar que:
  - `status_code == 200`
  - `type(response.json()) is list`
  - lista no vacía
  - algunos campos clave existen en el primer elemento (`reservation_id`, `airplane_id`, `seat_number`, etc.).


## 5. Precondiciones del entorno

Para ejecutar correctamente estos casos se asume:

1. **Microservicio Usuario** levantado, por ejemplo en:

   ```bash
   export USUARIO_BASE_URL="http://localhost:5003"
