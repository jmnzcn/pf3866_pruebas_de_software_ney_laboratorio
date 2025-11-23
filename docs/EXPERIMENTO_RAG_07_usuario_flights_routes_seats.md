# EXPERIMENTO_RAG_07_usuario_flights_routes_seats

Pruebas de contrato para los endpoints de **vuelos, rutas y asientos** expuestos por el microservicio **Usuario**, integrados conceptualmente con un enfoque de **RAG/MCP**.

Archivo de pruebas asociado:  
`tests/api/test_usuario_flights_routes_seats_rag.py`


## 1. Descripción general

Este experimento valida el comportamiento del microservicio **Usuario** como fachada de lectura hacia **GestiónVuelos** para:

- Consultar una **ruta de vuelo específica** por su ID.
- Consultar los **asientos** asociados a un avión por su ID.

Además de validar códigos HTTP y mensajes de error, este experimento define **IDs de casos** reutilizables (por ejemplo, `USR_ROUTE_ID_CERO_400`, `USR_SEATS_OK_01`) que pueden ser utilizados por un servidor **MCP** y un pipeline **RAG** para:

- Recuperar automáticamente la documentación relevante (Swagger, fragmentos de código).
- Explicar por qué cada caso existe.
- Sugerir variantes de casos (por ejemplo, nuevos IDs, escenarios límite).


## 2. Objetivo

1. Verificar que el microservicio **Usuario**:
   - Aplique correctamente las **validaciones locales** de entrada (IDs positivos).
   - Propague correctamente respuestas de **no encontrado** (404) procedentes de GestiónVuelos.
   - Devuelva datos bien formados en los casos exitosos.

2. Definir un conjunto de **casos estructurados** con `case_id` que puedan ser usados como **“documentos”** en un índice RAG para apoyar:
   - Diseño de casos de prueba.
   - Navegación semántica de escenarios.
   - Explicación de fallos detectados durante la ejecución.


## 3. Endpoints bajo prueba

| Endpoint                                             | Método | Descripción breve                                                       |
|------------------------------------------------------|--------|-------------------------------------------------------------------------| 
| `/get_airplane_route_by_id/<int:airplane_route_id>`  | GET    | Devuelve una ruta de vuelo específica, validada con Marshmallow.       |
| `/get_seats_by_airplane_id/<int:airplane_id>/seats`  | GET    | Devuelve la lista de asientos de un avión, validada con Marshmallow.   |


## 4. Enfoque RAG/MCP

- Cada caso de prueba tiene un `case_id` del tipo `USR_ROUTE_*` o `USR_SEATS_*`.
- Un servidor **MCP** podría exponer una herramienta como `run_usuario_case(case_id)` que:
  - Busca el caso en una colección (JSON/YAML).
  - Ejecuta la solicitud HTTP contra Usuario.
  - Devuelve `status_code`, cuerpo y metadatos.

- Un componente **RAG** podría:
  - Indexar:
    - El código de `app.py` de Usuario.
    - La documentación Swagger.
    - Este mismo `.md` con la descripción de los casos.
  - Resolver consultas del tipo:
    - “¿Qué prueba valida que el ID de ruta no pueda ser cero?”
    - “Muestra un ejemplo de caso 404 para rutas desde Usuario.”
  - Encontrar el `case_id` correspondiente y la sección relevante de código/documentación.


## 5. Casos de prueba definidos

### 5.1. `/get_airplane_route_by_id/<int:airplane_route_id>`

#### 5.1.1 Casos de error (validaciones y 404)

| case_id                      | Entrada (path)                        | Esperado         | Tipo             | Mensaje esperado (substring)                     |
|------------------------------|--------------------------------------|------------------|------------------|--------------------------------------------------|
| `USR_ROUTE_ID_CERO_400`      | `/get_airplane_route_by_id/0`        | 400 Bad Request  | Validación local | `El ID debe ser un número positivo`             |
| `USR_ROUTE_ID_NEGATIVO_400`  | `/get_airplane_route_by_id/-1`       | 400 Bad Request  | Validación local | `El ID debe ser un número positivo`             |
| `USR_ROUTE_NO_EXISTE_404`    | `/get_airplane_route_by_id/999999`   | 404 Not Found    | No encontrado    | `Ruta de vuelo no encontrada`                    |

Estos casos comprueban:

- Que el endpoint **no delega** al microservicio externo cuando el ID es inválido (≤ 0).
- Que Usuario devuelve un 404 coherente cuando GestiónVuelos indica que la ruta no existe.


#### 5.1.2 Caso feliz

**case_id:** `USR_ROUTE_OK_01` (implícito en la prueba `test_usuario_get_airplane_route_by_id_happy_path`)

**Estrategia:**

1. Llamar a `GET /get_all_airplanes_routes`.
2. Tomar el primer `airplane_route_id` entero y > 0.
3. Ejecutar `GET /get_airplane_route_by_id/<airplane_route_id>`.
4. Validar:
   - `status_code == 200`
   - JSON con `airplane_route_id` igual al solicitado.

Este patrón mantiene la prueba en modo **caja negra**, sin depender de IDs hardcodeados, y es amigable con datos generados dinámicamente.


### 5.2. `/get_seats_by_airplane_id/<int:airplane_id>/seats`

#### 5.2.1 Casos de error (validaciones y 404)

| case_id                        | Entrada (path)                               | Esperado         | Tipo             | Mensaje esperado (substring)                       |
|--------------------------------|---------------------------------------------|------------------|------------------|----------------------------------------------------|
| `USR_SEATS_ID_CERO_400`        | `/get_seats_by_airplane_id/0/seats`         | 400 Bad Request  | Validación local | `Por favor proporciona un ID de avión válido`     |
| `USR_SEATS_ID_NEGATIVO_400`    | `/get_seats_by_airplane_id/-1/seats`        | 400 Bad Request  | Validación local | `Por favor proporciona un ID de avión válido`     |
| `USR_SEATS_AIRPLANE_NO_EXISTE_404` | `/get_seats_by_airplane_id/999999/seats` | 404 Not Found    | No encontrado    | `No se encontraron asientos`                       |

Estos casos comprueban:

- Validación temprana de `airplane_id` en Usuario.
- Manejo de escenarios donde GestiónVuelos devuelve una lista vacía de asientos (avión inexistente o sin asientos).


#### 5.2.2 Caso feliz

**case_id:** `USR_SEATS_OK_01` (implícito en la prueba `test_usuario_get_seats_by_airplane_id_happy_path`)

**Estrategia:**

1. Llamar a `GET /get_all_airplanes_with_seats`.
2. Seleccionar el primer avión que cumpla:
   - `airplane_id` entero y > 0.
   - Lista `seats` no vacía.
3. Ejecutar `GET /get_seats_by_airplane_id/<airplane_id>/seats`.
4. Verificar que:
   - `status_code == 200`
   - Respuesta es una lista no vacía.
   - Cada elemento contiene al menos las claves `seat_number` y `status`.

De nuevo, se evita depender de IDs fijos y se apoya en el propio sistema para “descubrir” datos válidos de prueba.


## 6. Precondiciones del entorno

Para que las pruebas se ejecuten correctamente, se asume:

1. **Microservicio Usuario** levantado en:

   ```text
   http://localhost:5003
