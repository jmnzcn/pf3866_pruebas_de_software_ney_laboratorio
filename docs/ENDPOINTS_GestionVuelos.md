ENDPOINTS – Módulo GestiónVuelos

Este documento resume los endpoints expuestos por el microservicio GestiónVuelos, sus parámetros, respuestas esperadas y reglas de negocio clave para propósitos de pruebas.

Base URL por defecto en local: http://localhost:5001
Variable de entorno usada en pruebas: GV_BASE_URL

1. Endpoints de diagnóstico
GET /health

Descripción: Verifica que el servicio esté vivo.

Request body: Ninguno.

Response (200):

{
  "status": "ok",
  "instance_id": "1234-ABCD..."
}

Headers relevantes:

X-Instance-Id: identificador de proceso/instancia.

Códigos HTTP:

200 OK – servicio operativo.

GET /__state

Descripción: Expone un resumen del estado interno en memoria.

Request body: Ninguno.

Response (200):

{
  "instance_id": "1234-ABCD...",
  "airplanes_count": 3,
  "airplane_ids": [1, 2, 3],
  "routes_count": 3
}
Códigos HTTP:

200 OK – siempre que la estructura interna sea válida.

2. Endpoints de Airplanes
GET /get_airplanes

Descripción: Devuelve la lista completa de aviones en memoria.

Request body: Ninguno.

Reglas:

Valida que airplanes sea una lista.

Si hay IDs duplicados, devuelve error.

Códigos HTTP:

200 OK – lista de aviones o mensaje de “No hay aviones registrados actualmente.”

500 Internal Server Error – estructura interna inválida o errores de validación Marshmallow.

GET /get_airplane_by_id/{airplane_id}

Descripción: Obtiene un avión por su ID.

Parámetros de ruta:

airplane_id (int > 0).

Reglas:

Si airplane_id <= 0 → error 400.

Códigos HTTP:

200 OK – avión encontrado.

400 Bad Request – ID no positivo.

404 Not Found – avión no existe.

500 Internal Server Error – error inesperado.

POST /add_airplane

Descripción: Agrega un nuevo avión y genera sus asientos asociados.

Body esperado (JSON):

{
  "airplane_id": 4,
  "model": "Boeing 737",
  "manufacturer": "Boeing",
  "year": 2019,
  "capacity": 15
}

Reglas de negocio / validaciones:

Se detectan claves JSON duplicadas → 400.

Se valida que el body no sea vacío/mal formado.

Campos esperados: airplane_id, model, manufacturer, year, capacity:

Cualquier campo extra → 400.

Cualquier campo faltante → 400.

year debe ser entero > 0 → 400 si no lo es.

Validación completa con Marshmallow (AirplaneSchema):

Todos los campos requeridos.

airplane_id, year, capacity enteros positivos.

No se permite:

airplane_id duplicado.

Avión con mismos (model, manufacturer, year, capacity) que otro ya existente.

En caso de éxito:

Se agrega el avión a airplanes.

Se generan capacity asientos en seats con estado "Libre".

Códigos HTTP:

201 Created – avión y asientos creados.

400 Bad Request – validaciones fallidas o duplicados.

500 Internal Server Error – error inesperado.
PUT /update_airplane/{airplane_id}

Descripción: Actualiza un avión existente (modelo, fabricante, año, capacidad).

Parámetros de ruta:

airplane_id (int > 0).

Body esperado (JSON):

{
  "model": "Boeing 737",
  "manufacturer": "Boeing",
  "year": 2021,
  "capacity": 20
}
Reglas:

airplane_id debe ser > 0 → si no, 400.

Detecta claves duplicadas en JSON → 400.

Campos esperados: model, manufacturer, year, capacity:

Extras → 400.

Faltantes → 400.

Debe existir el avión (airplanes_by_id) → si no, 404.

Se construye full_payload = {"airplane_id": airplane_id, **data} y se valida con AirplaneSchema.

Si los datos nuevos son idénticos a los actuales → 200 con mensaje de “no se realizaron cambios” (no es error).

Códigos HTTP:

200 OK – actualización exitosa o “no-op” (sin cambios reales).

400 Bad Request – ID inválido o errores de validación.

404 Not Found – avión no existe.

500 Internal Server Error – error inesperado.

DELETE /delete_airplane_by_id/{airplane_id}

Descripción: Elimina un avión y todos sus asientos asociados.

Parámetros de ruta:

airplane_id (int > 0).

Reglas:

airplane_id <= 0 → 400.

Estructuras internas airplanes y seats deben ser listas → si no, 500.

Si no hay aviones → 404.

Si el avión no existe → 404.

Elimina:

El avión de airplanes.

Sus asientos de seats.

Su entrada en airplanes_by_id.

Devuelve cuántos asientos fueron eliminados.

Códigos HTTP:

200 OK – avión y asientos eliminados; incluye campo asientos_eliminados.

400 Bad Request – ID inválido.

404 Not Found – avión no existe o no hay aviones.

500 Internal Server Error – error en estructuras o inesperado.

3. Endpoints de Seats
GET /get_airplane_seats/{airplane_id}/seats

Descripción: Lista todos los asientos de un avión específico.

Parámetros de ruta:

airplane_id (int > 0).

Reglas:

airplane_id <= 0 → 400.

Estructuras airplanes y seats válidas (listas) → si no, 500.

Si el avión no existe → 404.

Si no hay asientos para ese avión → 404.

Valida la lista resultante con AirplaneSeatSchema(many=True).

Códigos HTTP:

200 OK – lista de asientos.

400 Bad Request – ID inválido.

404 Not Found – avión no existe o sin asientos registrados.

500 Internal Server Error – errores de datos o estructuras.

GET /seats/grouped-by-airplane

Descripción: Devuelve todos los asientos agrupados por airplane_id.

Response (200 ejemplo):

{
  "1": [
    { "airplane_id": 1, "seat_number": "1A", "status": "Libre" },
    ...
  ],
  "2": [ ... ]
}
Reglas:

seats debe ser lista; si no, 500.

Si no hay asientos → 200 con mensaje de “No hay asientos registrados en el sistema.”

Agrupa por airplane_id entero > 0.

Cada grupo se valida con AirplaneSeatSchema(many=True).

Códigos HTTP:

200 OK – asientos agrupados o mensaje sin asientos.

500 Internal Server Error – estructuras inválidas o errores de validación.

PUT /update_seat_status/{airplane_id}/seats/{seat_number}

Descripción: Actualiza el estado de un asiento específico.

Parámetros de ruta:

airplane_id (int).

seat_number (string, formato tipo "12A").

Body esperado (JSON):

{
  "status": "Reservado"
}
Valores válidos: "Libre", "Reservado", "Pagado".

Reglas:

seats debe ser lista → si no, 500.

El avión debe existir en airplanes → si no, 404.

seat_number:

Longitud máxima 5 → si no, 400.

No puede ser "ALL" ni "*" → 400.

Debe respetar regex ^\d+[A-F]$ → si no, 400.

Body no puede ser vacío → 400.

status debe estar entre los valores permitidos.

Si el asiento no existe para ese avión → 404.

Si el asiento ya tiene el estado solicitado → 200 (no es error, mensaje informativo).

Códigos HTTP:

200 OK – estado actualizado o sin cambios (si ya estaba en ese estado).

400 Bad Request – formato de asiento o body/estado inválido.

404 Not Found – avión o asiento inexistente.

500 Internal Server Error – error inesperado.

GET /get_random_free_seat/{airplane_id}

Descripción: Devuelve un asiento libre cualquiera de un avión.

Parámetros de ruta:

airplane_id (int).

Reglas:

Busca en seats el primer asiento con status == "Libre" para ese avión.

Si no encuentra ninguno → 404 con mensaje "No hay asientos libres".

Códigos HTTP:

200 OK – devuelve un asiento libre.

404 Not Found – no hay asientos libres.

PUT /free_seat/{airplane_id}/seats/{seat_number}

Descripción: Libera un asiento (pone status = "Libre").

Parámetros:

airplane_id (int).

seat_number (string).

Body: No es obligatorio, solo usa ruta.

Reglas:

seats y airplanes deben ser listas → si no, 500.

airplane_id <= 0 → 400.

Si el avión no existe → 404.

Si el asiento no existe para ese avión → 404.

Si el asiento ya está "Libre" → 200 con mensaje informativo.

Si estaba "Reservado" o "Pagado", se cambia a "Libre".

Códigos HTTP:

200 OK – asiento liberado o ya estaba libre.

400 Bad Request – ID inválido.

404 Not Found – avión o asiento no encontrado.

500 Internal Server Error – error inesperado.

4. Endpoints de Routes
POST /add_airplane_route

Descripción: Crea una nueva ruta de avión.

Body esperado (JSON):

{
  "airplane_route_id": 1,
  "airplane_id": 1,
  "flight_number": "AV-1234",
  "departure": "Aeropuerto Internacional A",
  "departure_time": "Marzo 30, 2025 - 16:46:19",
  "arrival": "Aeropuerto Internacional B",
  "arrival_time": "Marzo 30, 2025 - 19:25:00",
  "price": 98000,
  "Moneda": "Colones"
}
Reglas de validación:

Detecta claves duplicadas en JSON crudo → 400.

Body no puede ser vacío → 400.

AirplaneRouteSchema:

airplane_route_id, airplane_id, price enteros positivos.

flight_number con formato ^[A-Z]{2}-\d{4}$.

Moneda ∈ {"Dolares", "Euros", "Colones"}.

departure, arrival no vacíos.

departure_time, arrival_time:

Aceptan meses en español, se traducen a inglés y se parsean.

El avión (airplane_id) debe existir → si no, 400.

No se permiten duplicados:

airplane_route_id ya registrado → 400.

(flight_number, airplane_id) repetido → 400.

Ruta totalmente idéntica a otra → 400 (se reporta ID existente).

La hora de llegada debe ser posterior a la de salida → si arrival_time <= departure_time → 400.

En éxito:

Se formatean departure_time y arrival_time a inglés tipo "March 30, 2025 - 16:46:19" (capitalizado).

Se calcula flight_time ("X horas Y minutos").

Se agrega la ruta a airplanes_routes.

Códigos HTTP:

201 Created – ruta creada con éxito.

400 Bad Request – errores de validación/duplicados.

500 Internal Server Error – error inesperado.

GET /get_all_airplanes_routes

Descripción: Lista todas las rutas de avión.

Reglas:

airplanes_routes debe ser lista → si no, 500.

Si no hay rutas → 200 con mensaje "No hay rutas registradas actualmente."

En caso normal → lista serializada con AirplaneRouteSchema(many=True).

Códigos HTTP:

200 OK – lista de rutas o mensaje sin rutas.

500 Internal Server Error – estructura inválida o error inesperado.

GET /get_airplanes_route_by_id/{airplane_route_id}

Descripción: Obtiene una ruta por su ID.

Parámetros:

airplane_route_id (int > 0).

Reglas:

Si airplane_route_id <= 0 → 400.

airplanes_routes debe ser lista → si no, 500.

Si no se encuentra la ruta → 404.

Se serializa con AirplaneRouteSchema().dump(route).

Códigos HTTP:

200 OK – ruta encontrada.

400 Bad Request – ID inválido.

404 Not Found – ruta no existe.

500 Internal Server Error – error inesperado.

PUT /update_airplane_route_by_id/{airplane_route_id}

Descripción: Actualiza una ruta existente.

Parámetros:

airplane_route_id (int > 0).

Body esperado: JSON que cumpla con AirplaneRouteSchema.
(La ruta del body debe mantener el mismo airplane_route_id).

Reglas:

airplane_route_id <= 0 → 400.

airplanes_routes debe ser lista → si no, 500.

Debe existir la ruta que se quiere actualizar → si no, 404.

Se detectan claves duplicadas en JSON → 400.

Body no puede ser vacío → 400.

No se permite cambiar el airplane_route_id en el body:

Si se incluye y no coincide con el de la URL → 400.

Se valida y deserializa con AirplaneRouteSchema().load(data).

Se validan fechas (departure_time, arrival_time):

Se traducen meses español → inglés.

Se parsean y se verifica que arrival > departure; si no, 400.

Se recalculan departure_time, arrival_time y flight_time.

Si todos los campos relevantes son idénticos a los actuales → 200 con mensaje de “no hay cambios”.

Si hay cambios → se actualiza la ruta en memoria.

Códigos HTTP:

200 OK – actualización exitosa o sin cambios (no-op).

400 Bad Request – datos inválidos, JSON duplicado, ID inconsistente.

404 Not Found – ruta no existe.

500 Internal Server Error – error inesperado.

DELETE /delete_airplane_route_by_id/{airplane_route_id}

Descripción: Elimina una ruta de avión.

Parámetros:

airplane_route_id (int > 0).

Reglas:

airplane_route_id <= 0 → 400.

airplanes_routes debe ser lista → si no, 500.

Si la ruta no existe → 404.

Si existe → se elimina de airplanes_routes.

Códigos HTTP:

200 OK – ruta eliminada con éxito.

400 Bad Request – ID inválido.

404 Not Found – ruta no encontrada.

500 Internal Server Error – error inesperado.

5. Manejo genérico de errores

404 genérico:
Devuelto cuando se llama a un endpoint inexistente.

{ "message": "Endpoint no encontrado.", "errors": {} }
405 genérico:
Devuelto cuando se usa un método HTTP no permitido para un endpoint existente.

{ "message": "Método HTTP no permitido para este endpoint.", "errors": {} }
