# ENDPOINTS – Microservicio GestiónReservas

Microservicio encargado de gestionar **reservas** y **pagos** de vuelos,
usando datos en memoria e integrándose con el microservicio **GestiónVuelos**.

- Puerto por defecto: `5002`
- Base URL local típica: `http://localhost:5002`
- Integración con GestiónVuelos mediante variable de entorno:
  - `GESTIONVUELOS_SERVICE` (ej: `http://localhost:5001`)

---

## Índice de endpoints

### Reservations

1. `GET  /get_fake_reservations`
2. `GET  /get_reservation_by_code/<reservation_code>`
3. `GET  /get_reservation_by_id/<reservation_id>`
4. `DELETE /delete_reservation_by_id/<reservation_id>`
5. `POST /add_reservation`
6. `PUT  /reservations/<reservation_code>`

### Payments

7.  `GET    /get_all_fake_payments`
8.  `GET    /get_payment_by_id/<payment_id>`
9.  `DELETE /delete_payment_by_id/<payment_id>`
10. `POST   /create_payment`
11. `DELETE /cancel_payment_and_reservation/<payment_id>`
12. `PUT    /edit_payment/<payment_id>`

---

## Esquema base de Reservation (ReservationSchema)

Campos principales (Marshmallow):

- `reservation_id` (int) – generado en backend.
- `reservation_code` (str) – 6 caracteres alfanuméricos, generado en backend.
- `passport_number` (str, requerido).
- `full_name` (str, requerido).
- `email` (email válido, requerido).
- `phone_number` (str, requerido).
- `emergency_contact_name` (str, requerido).
- `emergency_contact_phone` (str, requerido).
- `airplane_id` (int, requerido).
- `airplane_route_id` (int, requerido).
- `flight_number` (str, opcional).
- `seat_number` (str, requerido).
- `status` (str, requerido, `"Reservado"` o `"Pagado"`).
- `reservation_date` (str, opcional).
- `issued_at` (str, generado en backend).
- `price` (float, opcional).

Cualquier campo **desconocido** en el JSON de entrada → `ValidationError`
por `unknown = RAISE`.

---

## 1. GET /get_fake_reservations

Obtiene todas las reservas actualmente almacenadas en memoria.

- **Método:** `GET`
- **Path:** `/get_fake_reservations`
- **Body:** ninguno.

### Comportamiento

- Si `reservations` está vacío:
  - HTTP `204`
  - Body:
    ```json
    { "message": "No hay reservas generadas actualmente." }
    ```
- Si hay reservas:
  - HTTP `200`
  - Body: lista de reservas completas.

---

## 2. GET /get_reservation_by_code/<reservation_code>

Obtiene una reserva por su `reservation_code` (string alfanumérico de 6 caracteres).

- **Método:** `GET`
- **Path:** `/get_reservation_by_code/<reservation_code>`
- **Parámetro de ruta:**
  - `reservation_code` (string) – Ej: `"ABC123"`

### Validaciones

1. Formato de código:
   - Debe cumplir regex `^[A-Z0-9]{6}$` (se normaliza a `upper()`).
   - Si no cumple → HTTP `400`:
     ```json
     { "message": "El código de reserva debe ser un string alfanumérico de 6 caracteres." }
     ```

2. Búsqueda:
   - Si no se encuentra → HTTP `404`:
     ```json
     { "message": "Reserva no encontrada" }
     ```

3. Validación con Marshmallow:
   - Si la reserva existe, se valida con `reservation_schema.load`.
   - Si todo ok → HTTP `200` con la reserva.
   - Si hay error de validación → HTTP `500`:
     ```json
     { "message": "Error de validación", "errors": { ... } }
     ```

---

## 3. GET /get_reservation_by_id/<reservation_id>

Obtiene una reserva por su identificador numérico.

- **Método:** `GET`
- **Path:** `/get_reservation_by_id/<reservation_id>`
- **Parámetro de ruta:**
  - `reservation_id` (string en la URL, convertido a `int` dentro).

### Validaciones

1. Conversión a entero:
   - Si no es convertible a `int` → HTTP `400`:
     ```json
     { "message": "El ID de reserva debe ser un número entero positivo." }
     ```

2. Rango:
   - Si `reservation_id <= 0` → HTTP `400`:
     ```json
     { "message": "El ID de reserva debe ser un número positivo mayor que cero." }
     ```

3. Búsqueda:
   - Si no se encuentra → HTTP `404`:
     ```json
     { "message": "Reserva no encontrada" }
     ```

4. Validación con Marshmallow:
   - Si existe → `reservation_schema.load(reservation)`.
   - Si ok → HTTP `200` con la reserva.
   - Si error de validación → HTTP `500` con `"Error de validación"`.

---

## 4. DELETE /delete_reservation_by_id/<reservation_id>

Elimina una reserva existente y **libera el asiento** en GestiónVuelos.

- **Método:** `DELETE`
- **Path:** `/delete_reservation_by_id/<int:reservation_id>`
- **Parámetro de ruta:**
  - `reservation_id` (int, > 0).

### Flujo

1. Validación de ID:
   - Si `reservation_id <= 0` → HTTP `400`:
     ```json
     { "message": "El ID de reserva debe ser un número positivo." }
     ```

2. Estructura de datos:
   - Si `reservations` no es una lista → HTTP `500`:
     ```json
     { "message": "Estructura de datos inválida para reservas." }
     ```

3. Búsqueda:
   - Si no se encuentra la reserva → HTTP `404`:
     ```json
     { "message": "Reserva no encontrada" }
     ```

4. Validación parcial:
   - Se llama a `reservation_schema.load(reservation, partial=True)`.
   - Si falla → HTTP `500` con `"Error de validación"`.

5. Eliminación y liberación de asiento:
   - Elimina la reserva de `reservations`.
   - Llama a GestiónVuelos:
     - `PUT {GESTIONVUELOS_SERVICE}/free_seat/{airplane_id}/seats/{seat_number}`.

   - Errores de red:
     - `ConnectionError` → HTTP `503`:
       ```json
       { "message": "No se pudo conectar con GestiónVuelos para liberar el asiento." }
       ```
     - `Timeout` → HTTP `504`:
       ```json
       { "message": "Timeout al intentar liberar el asiento en GestiónVuelos." }
       ```

   - Si status != 200 → sólo se loguea warning; la respuesta al cliente sigue siendo 200.

6. Respuesta final:
   - HTTP `200`:
     ```json
     {
       "message": "Reserva eliminada exitosamente",
       "deleted_reservation": { ... }
     }
     ```

---

## 5. POST /add_reservation

Crea una nueva reserva de vuelo, valida ruta y asiento en GestiónVuelos y marca el asiento como “Reservado”.

- **Método:** `POST`
- **Path:** `/add_reservation`
- **Body:** JSON respetando `ReservationSchema` (sin `reservation_id`, `reservation_code`, `issued_at`).

### Flujo y validaciones

1. Cuerpo JSON:
   - Si es `None` → HTTP `400`:
     ```json
     { "message": "No se recibió cuerpo JSON" }
     ```

2. Validación con Marshmallow:
   - `reservation_schema.load(data)`:
     - Faltantes, tipos incorrectos o campos extra → HTTP `400`:
       ```json
       { "message": "Error de validación", "errors": { ... } }
       ```

3. Validar ruta en GestiónVuelos:
   - GET `{GESTIONVUELOS_SERVICE}/get_all_airplanes_routes`.
   - Fallos de red:
     - `ConnectionError` → HTTP `503`:
       ```json
       { "message": "No se pudo conectar con GestiónVuelos al obtener rutas." }
       ```
     - `Timeout` → HTTP `504`:
       ```json
       { "message": "Timeout al obtener rutas en GestiónVuelos." }
       ```
   - Status != 200 → HTTP `500`:
     ```json
     { "message": "Error al obtener rutas desde GestiónVuelos." }
     ```
   - Se busca una ruta con `airplane_route_id` igual al enviado:
     - Si no existe → HTTP `400`:
       ```json
       { "message": "Ruta con ID X no encontrada." }
       ```
     - Si existe pero el `airplane_id` no coincide →
       HTTP `400`:
       ```json
       { "message": "La ruta X no está asociada al avión Y." }
       ```

4. Validar asiento:
   - GET `{GESTIONVUELOS_SERVICE}/get_airplane_seats/{airplane_id}/seats`.
   - Fallos de red:
     - `ConnectionError` → HTTP `503`:
       ```json
       { "message": "No se pudo conectar con GestiónVuelos para verificar asiento." }
       ```
     - `Timeout` → HTTP `504`:
       ```json
       { "message": "Timeout al verificar asiento en GestiónVuelos." }
       ```
   - Status != 200 → HTTP `500`:
     ```json
     { "message": "Error al verificar estado de asientos." }
     ```
   - Si el asiento no existe → HTTP `400`:
     ```json
     { "message": "El asiento especificado no existe para ese avión." }
     ```
   - Si no está libre → HTTP `409`:
     ```json
     { "message": "El asiento X no está disponible." }
     ```

5. Generar campos internos:
   - `reservation_code` único (6 caracteres alfanuméricos).
   - `issued_at` con fecha/hora en español.
   - `reservation_id = len(reservations) + 1`.

6. Reservar asiento en GestiónVuelos:
   - PUT `{GESTIONVUELOS_SERVICE}/update_seat_status/{airplane_id}/seats/{seat_number}`
     con body `{ "status": "Reservado" }`.
   - Errores de red → 503/504.
   - Status != 200 → HTTP `500`:
     ```json
     { "message": "No se pudo reservar el asiento X." }
     ```

7. Guardar y responder:
   - Añade la reserva a `reservations`.
   - HTTP `201`:
     ```json
     {
       "message": "Reserva creada exitosamente",
       "reservation": { ... }
     }
     ```

---

## 6. PUT /reservations/<reservation_code>  (editar reserva)

Edita una reserva existente: datos de contacto y/o cambio de asiento.

- **Método:** `PUT`
- **Path:** `/reservations/<string:reservation_code>`
- **Body:** JSON con exactamente 5 campos:
  - `seat_number`
  - `email`
  - `phone_number`
  - `emergency_contact_name`
  - `emergency_contact_phone`

### Validaciones

1. Formato de `reservation_code`:
   - 6 caracteres alfanuméricos (`[A-Z0-9]{6}`).
   - Si no → HTTP `400`:
     ```json
     { "message": "El código de reserva debe ser 6 caracteres alfanuméricos." }
     ```

2. Existencia:
   - Si no existe la reserva → HTTP `404`:
     ```json
     { "message": "Reserva no encontrada" }
     ```

3. Cuerpo JSON:
   - Si no hay body → HTTP `400`:
     ```json
     { "message": "No se recibió cuerpo JSON." }
     ```

4. Campos exactos:
   - Si los campos recibidos (`keys`) no coinciden exactamente con los 5 permitidos
     → HTTP `400` con mensaje descriptivo.

5. Sin cambios:
   - Si todos los valores son iguales a los actuales →
     HTTP `200`:
     ```json
     { "message": "La información es idéntica; no se realizaron cambios." }
     ```

6. Cambio de asiento (cuando `seat_number` cambia):
   - Consultar asientos:
     - GET `{GESTIONVUELOS_SERVICE}/get_airplane_seats/{airplane_id}/seats`.
     - Errores → 503/504.
     - Status != 200 → 500.
   - Validar nuevo asiento:
     - Si no existe → HTTP `400`:
       ```json
       { "message": "Asiento X no existe en el avión." }
       ```
     - Si no está libre → HTTP `409`:
       ```json
       { "message": "El asiento X no está libre." }
       ```
   - Liberar asiento anterior:
     - PUT `/free_seat/{airplane_id}/seats/{old_seat}`.
     - Errores → 503.
     - Status != 200 → 500.
   - Reservar nuevo asiento:
     - PUT `/update_seat_status/{airplane_id}/seats/{new_seat}` con `"Reservado"`.
     - Errores → 503.
     - Status no en (200, 204) → 500.

7. Actualizar campos de contacto:
   - Se sobrescriben en la reserva.

8. Validación final:
   - `reservation_schema.load(reservation)`.
   - Error → HTTP `400`, `"Error de validación"`.

9. Respuesta:
   - HTTP `200` con:
     ```json
     {
       "message": "Reserva y datos actualizados exitosamente",
       "reservation": { ... }
     }
     ```

---

## 7. GET /get_all_fake_payments

Devuelve todos los pagos generados (en memoria).

- **Método:** `GET`
- **Path:** `/get_all_fake_payments`

### Comportamiento

- Si `payments` está vacío → HTTP `200`:
  ```json
  { "message": "No hay pagos generados actualmente." }
