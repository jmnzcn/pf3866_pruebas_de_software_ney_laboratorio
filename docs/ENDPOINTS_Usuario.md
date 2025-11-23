# ENDPOINTS – Microservicio Usuario

Base por defecto (si no se configura otra): `http://localhost:5003`

El microservicio **Usuario** actúa como fachada/orquestador frente a:
- `GESTIONVUELOS_SERVICE` (GestiónVuelos)
- `GESTIONRESERVAS_SERVICE` (GestiónReservas)

Por eso muchos endpoints delegan la lógica a otros microservicios y añaden validaciones extra.

---

## 1. Rutas y asientos (`Flights routes and seats`)

### 1.1. GET `/get_seats_by_airplane_id/{airplane_id}/seats`

Obtiene y valida los asientos de un avión (consultando GestiónVuelos).

- `airplane_id` (path, int > 0)

Validaciones:
- Si `airplane_id <= 0` → `400` + `"Por favor proporciona un ID de avión válido (mayor que cero)."`
- Llama a `GESTIONVUELOS_SERVICE/get_airplane_seats/{airplane_id}/seats`.
- Si la respuesta no es lista JSON → `500`.
- Si la lista viene vacía → `404` + `"No se encontraron asientos para el avión con ID X."`
- Valida con `AirplaneSeatSchema`:
  - Campos requeridos: `airplane_id`, `seat_number`, `status`.
  - `status` ∈ {"Libre", "Reservado", "Pagado"}.

Respuestas:
- `200` → lista validada de asientos.
- `400`, `404`, `500` según los casos anteriores.

---

### 1.2. GET `/get_all_airplanes_with_seats`

Obtiene **todos los aviones** y les agrega sus asientos (ambos desde GestiónVuelos).

Flujo:
1. `GET {GESTIONVUELOS_SERVICE}/get_airplanes`
   - Si status != 200 → `500`.
   - Si no es lista o está vacía → `404` + `"No hay aviones registrados actualmente."`
2. `GET {GESTIONVUELOS_SERVICE}/seats/grouped-by-airplane`
   - Si status != 200 → `500`.

Validaciones:
- Cada avión se valida con `AirplaneSchema`:
  - `airplane_id`, `model`, `manufacturer`, `year`, `capacity`.
- Asientos por avión se validan con `AirplaneSeatSchema(many=True)`.

Respuestas:
- `200` → lista de objetos `{airplane_id, model, ..., seats: [...]}`.
- `404` → si no hay aviones o resultado final vacío.
- `500` → error de red o validación.

---

### 1.3. GET `/get_all_airplanes_routes`

Devuelve todas las rutas de vuelo, pasando por una función helper (`get_all_flights`) que llama a GestiónVuelos.

Flujo y validaciones en `get_all_flights()`:
- Construye `GET {GESTIONVUELOS_SERVICE}/get_all_airplanes_routes`.
- Si variable de entorno no está → devuelve `None`.
- Si status != 200 → `None`.
- Si `Content-Type` no contiene `application/json` → `None`.
- Si el JSON no es lista → `None`.

En el endpoint:
- Si `vuelos is None` → `500` + `"No se pudo establecer conexión con el microservicio de vuelos."`
- Si no es lista → `500` + `"La respuesta del microservicio no tiene el formato correcto (lista esperada)."`
- Si lista vacía → `404` + `"No hay vuelos registrados actualmente en el sistema."`
- Si algún item no tiene `airplane_route_id` → `500`.

Respuesta:
- `200` → lista de rutas (diccionarios).
- `404`, `500` según casos.

---

### 1.4. GET `/get_airplane_route_by_id/{airplane_route_id}`

Consulta una ruta específica a GestiónVuelos y la valida con `AirplaneRouteSchema`.

Parámetros:
- `airplane_route_id` (path, int > 0)

Validaciones:
- Si `airplane_route_id <= 0` → `400` + `"El ID debe ser un número positivo."`
- Llama a `GET {GESTIONVUELOS_SERVICE}/get_airplanes_route_by_id/{id}`:
  - `404` → `"Ruta de vuelo no encontrada"`
  - status != 200 y != 404 → `500` + `"Error al consultar el microservicio GestiónVuelos"`
- Si respuesta no es JSON → `500`.
- Valida con `AirplaneRouteSchema`:
  - `airplane_route_id`, `airplane_id`, `flight_number`, `departure`, `arrival`, `departure_time`, `arrival_time`, `flight_time`, `price`, `Moneda`.
  - `unknown = INCLUDE` (campos extra permitidos).

Respuestas:
- `200` → ruta validada.
- `400`, `404`, `500` según el caso.

---

## 2. Reservas (`Reservations`)

### 2.1. GET `/get_reservation_by_code/{reservation_code}`

Consulta una reserva en GestiónReservas por código alfanumérico.

Parámetros:
- `reservation_code` (path, string no vacío)

Validaciones:
- Si no es `str` o vacío → `400` + `"El código de reserva es obligatorio y debe ser texto válido."`
- Llama a `GET {GESTIONRESERVAS_SERVICE}/get_reservation_by_code/{code}`:
  - `404` → `"Reserva no encontrada en GestiónReservas"`
  - status != 200 y != 404 → `500` + `"Error consultando reserva. Código: X"`
- Valida estructura con `ReservationSchema` (email, status ∈ {"Reservado","Pagado"}, etc.).

Respuestas:
- `200` → reserva validada.
- `400`, `404`, `500`.

---

### 2.2. GET `/get_reservation_by_id/{reservation_id}`

Consulta reserva por ID numérico.

Parámetros:
- `reservation_id` (path, int > 0)

Validaciones:
- `reservation_id <= 0` → `400` + `"El ID debe ser un número entero positivo."`
- `GET {GESTIONRESERVAS_SERVICE}/get_reservation_by_id/{id}`:
  - `404` → `"Reserva no encontrada en GestiónReservas"`
  - != 200 y != 404 → `500` + `"Error consultando reserva. Código: X"`
- Valida con `ReservationSchema`.

Respuestas:
- `200` → reserva validada.
- `400`, `404`, `500`.

---

### 2.3. PUT `/update_reservation/{reservation_code}`

Modifica una reserva existente (via GestiónReservas) y sincroniza asientos con GestiónVuelos.

Parámetros:
- `reservation_code` (path, 6 caracteres alfanuméricos).
- Body JSON obligatorio con **exactamente** estos campos:
  - `seat_number`, `email`, `phone_number`,
    `emergency_contact_name`, `emergency_contact_phone`.

Validaciones:
1. Formato de código: regex `[A-Z0-9]{6}` → si falla → `400`.
2. Body:
   - Si no hay JSON → `400` + `"No se recibió cuerpo JSON."`
   - Si claves != conjunto permitido → `400` + mensaje indicando campos exactos.
3. Llama a `GET {GESTIONRESERVAS_SERVICE}/get_reservation_by_code/{code}`:
   - `503/504` si hay problemas de conexión/timeout.
   - `404` si no existe.
   - Status no 200/404 → error propagado.

Reglas:
- Si todos los campos son idénticos a la reserva actual → `200` + `"La información es idéntica; no se realizaron cambios."`
- Si cambia `seat_number`:
  - Consulta asientos en GestiónVuelos:
    - si error → `500`.
    - si asiento no existe → `400`.
    - si asiento no está `Libre` → `409`.
- Luego hace `PUT {GESTIONRESERVAS_SERVICE}/reservations/{code}` con el body:
  - Si status != 200 → se reenvía tal cual.
- Si cambió asiento:
  - `PUT /free_seat/{airplane_id}/seats/{old_seat}` (liberar).
  - `PUT /update_seat_status/{airplane_id}/seats/{new_seat}` (reservar).
  - Errores en estas llamadas se loguean pero no cambian el status 200 final (solo warnings).

Respuesta:
- `200` → `"Reserva y datos actualizados exitosamente" + reservation`.

---

### 2.4. DELETE `/usuario/delete_reservation_by_id/{reservation_id}`

Desde Usuario: elimina la reserva en GestiónReservas y libera asiento en GestiónVuelos.

Parámetros:
- `reservation_id` (path, int > 0)

Flujo:
1. Validación: `reservation_id <= 0` → `400`.
2. `DELETE {GESTIONRESERVAS_SERVICE}/delete_reservation_by_id/{id}`:
   - `404` → `"Reserva no encontrada"`
   - != 200 y != 404 → `500` + `"Error al eliminar reserva. Código: X"`
3. Extrae `deleted_reservation` del JSON:
   - Si falta o no tiene `airplane_id`/`seat_number` → `500`.
4. Llama a `PUT {GESTIONVUELOS_SERVICE}/free_seat/{airplane_id}/seats/{seat_number}`:
   - Si status != 200 → `503` + `"Reserva eliminada, pero no se pudo liberar el asiento"`.

Respuestas:
- `200` → mensaje de éxito + `deleted_reservation`.
- `400`, `404`, `503`, `504`, `500`.

---

### 2.5. GET `/get_all_reservations`

Lista todas las reservas.

Flujo:
- `GET {GESTIONRESERVAS_SERVICE}/get_fake_reservations`:
  - `204` → se transforma en `200` + `"No hay reservas registradas."`
  - `200`:
    - si lista vacía o no lista → `200` + `"No hay reservas registradas."`
    - si lista con elementos → valida con `reservation_schema(many=True)`:
      - si OK → `200` + lista.
      - si falla → `500` + `"Error de validación en las reservas"`.
  - Otros códigos → se propagan.

---

### 2.6. POST `/usuario/add_reservation`

Crea una reserva **a través de Usuario**, validando ruta↔avión y asiento Libre antes de delegar en GestiónReservas.

Body:
- Valida con `ReservationCreationSchema`:
  - Requeridos:
    - `passport_number`, `full_name`, `email`, `phone_number`,
      `emergency_contact_name`, `emergency_contact_phone`,
      `airplane_id`, `airplane_route_id`, `seat_number`, `status`.
  - `status` debe ser `"Reservado"`.
  - `unknown = INCLUDE` (campos extra permitidos).

Flujo:
1. Si no hay JSON → `400` + `"No se recibió cuerpo JSON"`.
2. Si falla validación → `400` + `"Error de validación"` + `errors`.
3. Validación ruta ↔ avión:
   - `GET {GESTIONVUELOS_SERVICE}/get_all_airplanes_routes`:
     - errores de red → `503/504`.
     - status != 200 → `500`.
   - Busca ruta con `airplane_route_id`:
     - si no está → `400` + `"Ruta con ID {route_id} no encontrada."`
     - si `airplane_id` de ruta != `airplane_id` del body → `400` + `"La ruta {route_id} no está asociada al avión {airplane_id}."`
4. Validar asiento:
   - `GET {GESTIONVUELOS_SERVICE}/get_airplane_seats/{airplane_id}/seats`:
     - errores de red → `503/504`.
     - status != 200 → `500`.
   - Busca asiento:
     - no existe → `400` + `"Asiento {seat_number} no existe en el avión {airplane_id}."`
     - status != "Libre" → `409` + `"El asiento {seat_number} no está libre."`
5. Crear reserva en GestiónReservas:
   - `POST {GESTIONRESERVAS_SERVICE}/add_reservation` con el payload validado:
     - errores de conexión/timeout → `503/504`.
     - status != 201 → se propaga JSON/mensaje y código.
6. Marcar asiento como `Reservado`:
   - `PUT {GESTIONVUELOS_SERVICE}/update_seat_status/{airplane_id}/seats/{seat_number}`:
     - excepción de red → `500` + mensaje `"Reserva en GestiónReservas OK, pero fallo al reservar asiento..."` + `reservation`.
     - status != 200 → `500` + mensaje similar.

Respuesta final:
- `201` → body JSON devuelto por GestiónReservas (normalmente `"message": "Reserva creada exitosamente", "reservation": {...}`).
- `400`, `409`, `503`, `504`, `500` según la regla violada.

---

## 3. Pagos (`Payments`)

### 3.1. DELETE `/cancel_payment_and_reservation/{payment_id}`

Cancela un pago y la reserva asociada, delegando en GestiónReservas.

Parámetros:
- `payment_id` (formato `PAYdddddd`)

Validaciones:
- Si formato no coincide con `PAY\d{6}` → `400`.

Flujo:
- `DELETE {GESTIONRESERVAS_SERVICE}/cancel_payment_and_reservation/{payment_id}`:
  - `503/504` en errores de conexión/timeout.
  - Si `200` → se devuelve el JSON tal cual.
  - En otros códigos → se propaga el body (JSON o texto) con ese mismo status.

---

### 3.2. GET `/get_all_payments`

Lista todos los pagos (desde GestiónReservas).

Flujo:
- `GET {GESTIONRESERVAS_SERVICE}/get_all_fake_payments`
  - status != 200 → se propaga código con mensaje de error.
  - Si respuesta es dict con `"message"`:
    - si texto dice “no hay pagos” → `200` + `"No hay pagos generados actualmente."`
    - si no, se devuelve tal cual.
  - Si no es lista → `500` + `"Error de validación: se esperaba una lista de pagos"`.
  - Si lista vacía → `200` + `"No hay pagos generados actualmente."`
  - Si lista con elementos → valida con `PaymentSchema(many=True)`:
    - si OK → `200` + lista.
    - si falla → `500` + `"Error de validación en los pagos"`.

---

### 3.3. GET `/get_payment_by_id/{payment_id}`

Obtiene detalle de un pago por ID.

Parámetros:
- `payment_id` con formato `PAYdddddd`.

Validaciones:
- Si formato inválido → `400`.
- Llama a `GET {GESTIONRESERVAS_SERVICE}/get_payment_by_id/{payment_id}`:
  - `404` → `"No se encontró ningún pago con ID: X"`
  - `200` → se devuelve JSON tal cual.
  - Otros códigos → `500` + `"Error consultando pago. Código: X"`

---

### 3.4. POST `/usuario/create_payment`

Desde Usuario: crea un pago en GestiónReservas y marca asiento como `Pagado` en GestiónVuelos.

Body:
- `reservation_id` (int > 0)
- `payment_method` ∈ {"Tarjeta","PayPal","Transferencia"}
- `currency` ∈ {"Dolares","Colones"} (default `"Dolares"`)

Flujo:
1. Validaciones básicas del body → `400` si fallan.
2. `GET {GESTIONRESERVAS_SERVICE}/get_reservation_by_id/{reservation_id}`:
   - `404` → `"Reserva con ID X no encontrada."`
   - != 200/404 → se propaga.
3. Llama a `POST {GESTIONRESERVAS_SERVICE}/create_payment`:
   - errores de red/timeout → `503/504`.
   - status != 201 → se devuelve body y status tal cual.
4. Extrae `airplane_id` y `seat_number` de la reserva.
5. `PUT {GESTIONVUELOS_SERVICE}/update_seat_status/{airplane_id}/seats/{seat_number}` → `status = "Pagado"`:
   - errores de red/timeout → `503/504`.
   - status != 200 → warning log, pero se responde `201` igualmente.

Respuesta:
- `201` → `"✅ Pago registrado y asiento marcado como pagado." + payment`.
- `400`, `404`, `409`, `503`, `504`, `500` según el caso.

---

### 3.5. PUT `/usuario/edit_payment/{payment_id}`

Edita un pago existente delegando en GestiónReservas.

Parámetros:
- `payment_id` (formato `PAYdddddd`).

Body:
- Puede incluir cualquier subconjunto de:
  - `payment_method` (debe estar en {"Tarjeta","PayPal","Transferencia","Efectivo","SINPE"} si se envía).
  - `payment_date`
  - `transaction_reference`

Validaciones:
- Formato de `payment_id` → si inválido → `400`.
- Si no hay JSON → `400`.
- Si body tiene campos fuera del conjunto permitido → `400`.

Flujo:
- `PUT {GESTIONRESERVAS_SERVICE}/edit_payment/{payment_id}` y se propaga el body y status.

Respuestas:
- `200`, `400`, `404`, `503`, `504`, `500` según respuesta de GestiónReservas.
