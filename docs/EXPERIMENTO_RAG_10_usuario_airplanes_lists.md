# EXPERIMENTO_RAG_10_usuario_airplanes_lists

Pruebas de contrato para los endpoints de **listado de rutas de vuelo** y **listado de aviones con asientos** expuestos por el microservicio **Usuario**, integradas con el enfoque de **RAG/MCP**.

Archivo de pruebas asociado (propuesto):  
`tests/api/test_usuario_airplanes_lists_rag.py`


## 1. Descripción general

Este experimento valida el comportamiento de los endpoints:

- `GET /get_all_airplanes_routes`
- `GET /get_all_airplanes_with_seats`

Estos endpoints actúan como fachada de lectura hacia el microservicio **GestiónVuelos**, agregando:

- Validaciones de estructura (listas, campos requeridos).
- Manejo de errores de conexión / formato.
- Validación de datos usando **Marshmallow** (en el caso de aviones + asientos).

Los `case_id` definidos aquí:

- Documentan el contrato HTTP esperado.
- Sirven como base para generar y ejecutar casos desde un servidor **MCP** y enriquecer un sistema **RAG**.


## 2. Endpoints bajo prueba

### 2.1. `GET /get_all_airplanes_routes`

Devuelve la lista de rutas de vuelo obtenidas desde **GestiónVuelos** mediante la función helper `get_all_flights()`.

Flujo simplificado:

1. Llamar a `get_all_flights()`.
2. Si `get_all_flights()` devuelve `None` → 500  
   `{"error": "No se pudo establecer conexión con el microservicio de vuelos."}`
3. Si devuelve algo que no es lista → 500  
   `{"error": "La respuesta del microservicio no tiene el formato correcto (lista esperada)."}`
4. Si devuelve lista vacía → 404  
   `{"error": "No hay vuelos registrados actualmente en el sistema."}`
5. Si algún elemento no cumple `isinstance(v, dict)` o le falta `airplane_route_id` → 500  
   `{"error": "Uno o más vuelos no contienen la estructura esperada ('airplane_route_id' faltante)."}`
6. Si todo está bien:
   - `200 OK` con la lista de rutas como JSON.

Errores genéricos:

- Cualquier excepción no controlada → 500  
  `{"error": "Se produjo un error inesperado al procesar la solicitud. Inténtalo nuevamente más tarde."}`


### 2.2. `GET /get_all_airplanes_with_seats`

Devuelve todos los aviones con sus asientos asociados, combinando dos llamadas a **GestiónVuelos**:

- `GET {GESTIONVUELOS_SERVICE}/get_airplanes`
- `GET {GESTIONVUELOS_SERVICE}/seats/grouped-by-airplane`

Flujo simplificado:

1. `GET /get_airplanes`
   - Si `status_code != 200` → 500  
     `{"error": "No se pudieron obtener los aviones."}`
   - Si el JSON no es lista o la lista está vacía → 404  
     `{"message": "No hay aviones registrados actualmente."}`

2. `GET /seats/grouped-by-airplane`
   - Si `status_code != 200` → 500  
     `{"error": "No se pudieron obtener los asientos."}`
   - Respuesta se espera como dict:  
     - key: `airplane_id` en string  
     - value: lista de asientos

3. Para cada avión:
   - Validar avión con `airplane_schema` (Marshmallow).
   - Tomar la lista de asientos `seats_grouped[str(airplane_id)]` (o lista vacía si no hay).
   - Validar asientos con `airplane_seats_schema` (`status` ∈ {Libre, Reservado, Pagado}, etc.).
   - Agregar al resultado:

     ```json
     {
       "airplane_id": 1,
       "model": "...",
       "manufacturer": "...",
       "year": 2020,
       "capacity": 150,
       "seats": [
         {"airplane_id": 1, "seat_number": "1A", "status": "Libre"},
         ...
       ]
     }
     ```

4. Si durante la iteración se produce `ValidationError`:
   - 500
   - `{"message": "Error de validación en avión o sus asientos", "errors": {...}}`

5. Si el `resultado` final queda vacío (caso borde) → 404  
   `{"message": "No hay aviones con asientos para mostrar."}`

6. En caso de errores de red (`requests.RequestException`) → 500  
   `{"error": "Error al conectar con el microservicio de vuelos."}`

7. En caso de cualquier otra excepción → 500  
   `{"error": "Error interno del servidor"}`


## 3. Casos de prueba propuestos

### 3.1. `GET /get_all_airplanes_routes`

#### 3.1.1. Casos de error

| case_id                                   | Escenario                                                           | Esperado | Mensaje esperado (substring)                                          |
|-------------------------------------------|---------------------------------------------------------------------|----------|------------------------------------------------------------------------|
| `USR_AIRLIST_ROUTES_NO_CONN_500`         | `get_all_flights()` devuelve `None` (sin conexión / error interno) | 500      | `No se pudo establecer conexión con el microservicio de vuelos`       |
| `USR_AIRLIST_ROUTES_NOT_LIST_500`        | `get_all_flights()` devuelve algo que no es lista                  | 500      | `La respuesta del microservicio no tiene el formato correcto`         |
| `USR_AIRLIST_ROUTES_EMPTY_404`           | Lista de rutas vacía                                                | 404      | `No hay vuelos registrados actualmente en el sistema`                 |
| `USR_AIRLIST_ROUTES_BAD_STRUCT_500`      | Algún elemento no tiene `airplane_route_id`                        | 500      | `Uno o más vuelos no contienen la estructura esperada`                |
| `USR_AIRLIST_ROUTES_UNEXPECTED_500`      | Excepción inesperada en el endpoint                                 | 500      | `Se produjo un error inesperado al procesar la solicitud`             |

Notas:

- En entorno real, algunos de estos casos solo serán fácilmente reproducibles forzando comportamientos en GestiónVuelos o a través de un stub/fake en laboratorio.
- En caja negra, suele ser más realista validar:
  - Caso feliz (cuando hay rutas).
  - Caso de lista vacía (si el sistema permite limpiarlas).

#### 3.1.2. Caso feliz

| case_id                         | Estrategia                                                                               | Esperado |
|--------------------------------|------------------------------------------------------------------------------------------|----------|
| `USR_AIRLIST_ROUTES_OK_200`    | Hay al menos una ruta cargada en GestiónVuelos. Llamar a `/get_all_airplanes_routes`.   | 200      |

Validaciones mínimas:

- `status_code == 200`.
- Respuesta es lista no vacía.
- Cada elemento es dict con al menos `airplane_route_id` (y de preferencia `airplane_id`, `flight_number`, etc.).


### 3.2. `GET /get_all_airplanes_with_seats`

#### 3.2.1. Casos de error

| case_id                                          | Escenario                                                                                           | Esperado | Mensaje esperado (substring)                                      |
|--------------------------------------------------|-----------------------------------------------------------------------------------------------------|----------|--------------------------------------------------------------------|
| `USR_AIRLIST_PLANES_HTTP_ERROR_500`             | `GET /get_airplanes` devuelve código ≠ 200                                                          | 500      | `No se pudieron obtener los aviones`                               |
| `USR_AIRLIST_PLANES_EMPTY_404`                  | `GET /get_airplanes` devuelve lista vacía o no es lista                                             | 404      | `No hay aviones registrados actualmente`                           |
| `USR_AIRLIST_SEATS_HTTP_ERROR_500`              | `GET /seats/grouped-by-airplane` devuelve código ≠ 200                                              | 500      | `No se pudieron obtener los asientos`                              |
| `USR_AIRLIST_VALIDATION_ERROR_500`              | Marshmallow detecta error en avión o en su lista de asientos                                        | 500      | `Error de validación en avión o sus asientos`                      |
| `USR_AIRLIST_RESULT_EMPTY_404`                  | Tras procesar, la lista `resultado` queda vacía                                                     | 404      | `No hay aviones con asientos para mostrar`                         |
| `USR_AIRLIST_NET_ERROR_500`                     | Cualquier `requests.RequestException` al consultar GestiónVuelos                                    | 500      | `Error al conectar con el microservicio de vuelos`                 |
| `USR_AIRLIST_INTERNAL_500`                      | Cualquier otra excepción                                                                             | 500      | `Error interno del servidor`                                      |

En caja negra, lo más típico que se puede reproducir sin manipular datos internos es:

- Caso feliz (con al menos un avión y sus asientos).
- Caso de “no hay aviones registrados” (si el sistema permite iniciar sin datos).
- Algún error de conexión, si deliberadamente se apaga el contenedor de GestiónVuelos.


#### 3.2.2. Caso feliz

| case_id                               | Estrategia                                                                                     | Esperado |
|--------------------------------------|--------------------------------------------------------------------------------------------------|----------|
| `USR_AIRLIST_PLANES_WITH_SEATS_200`  | Hay al menos un avión y asientos en GestiónVuelos. Llamar a `/get_all_airplanes_with_seats`.   | 200      |

Validaciones mínimas:

- `status_code == 200`.
- Respuesta es **lista no vacía**.
- Cada elemento del resultado:
  - Es dict.
  - Contiene al menos:
    - `airplane_id`
    - `model`
    - `manufacturer`
    - `year`
    - `capacity`
    - `seats` (lista, posiblemente vacía).
- Cada elemento de `seats` (cuando existan):
  - Es dict con al menos:
    - `airplane_id`
    - `seat_number`
    - `status` ∈ {`Libre`, `Reservado`, `Pagado`}.


## 4. Precondiciones del entorno

Para ejecutar este experimento se requiere:

1. **Microservicio Usuario** levantado:

   ```bash
   export USUARIO_BASE_URL="http://localhost:5003"
