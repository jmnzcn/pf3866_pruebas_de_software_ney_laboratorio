# Reglas de negocio para pruebas – GestiónReservas

Este documento resume las reglas de negocio que deben respetar los endpoints
del microservicio **GestiónReservas**. Sirve como guía para diseñar casos de
prueba manuales y para los casos sugeridos por el “RAG tester”.

## 1. Contexto general

- El servicio mantiene **todo en memoria**:
  - Lista `reservations`: reservas de vuelo.
  - Lista `payments`: pagos asociados a reservas.
- Se integra con el microservicio **GestiónVuelos** (env: `GESTIONVUELOS_SERVICE`)
  para:
  - Validar rutas (`/get_all_airplanes_routes`).
  - Consultar asientos de un avión (`/get_airplane_seats/<airplane_id>/seats`).
  - Reservar / pagar / liberar asientos:
    - `PUT /update_seat_status/{airplane_id}/seats/{seat_number}`
    - `PUT /free_seat/{airplane_id}/seats/{seat_number}`

Para las pruebas, es importante que **GestiónVuelos** esté levantado y en un
estado razonable (con aviones, rutas y asientos).

---

## 2. Estructura de una reserva

Las reservas se validan con `ReservationSchema` (Marshmallow).

Campos relevantes:

- `reservation_id` (int, generado en backend, no requerido en el POST).
- `reservation_code` (str, 6 caracteres alfanuméricos, generado en backend).
- `passport_number` (str, requerido).
- `full_name` (str, requerido).
- `email` (email válido, requerido).
- `phone_number` (str, requerido).
- `emergency_contact_name` (str, requerido).
- `emergency_contact_phone` (str, requerido).
- `airplane_id` (int, requerido).
- `airplane_route_id` (int, requerido).
- `flight_number` (str, opcional, normalmente viene de GestiónVuelos).
- `seat_number` (str, requerido, ej. “1A”).
- `status` (str, requerido, uno de: `"Reservado"`, `"Pagado"`).
- `reservation_date` (str, opcional).
- `issued_at` (str, generado en backend).
- `price` (float, opcional).

Reglas generales:

- Campos desconocidos en el JSON de entrada → error de validación (Marshmallow).
- `status` sólo puede ser `"Reservado"` o `"Pagado"`.

---

## 3. Reglas de negocio – Reservas

### 3.1. `GET /get_fake_reservations`

- Devuelve la lista actual de `reservations`.
- Si no hay reservas:
  - HTTP 204 con `{"message": "No hay reservas generadas actualmente."}`.
- Si hay reservas:
  - HTTP 200 con el arreglo de reservas.

### 3.2. `GET /get_reservation_by_code/<reservation_code>`

Reglas:

- `reservation_code` debe ser **string alfanumérico de 6 caracteres**:
  - Regex: `^[A-Z0-9]{6}$` (se convierte internamente a `upper()`).
  - Si no cumple → HTTP 400, mensaje:
    - `"El código de reserva debe ser un string alfanumérico de 6 caracteres."`
- Si el código es válido pero no existe en `reservations`:
  - HTTP 404, `"Reserva no encontrada"`.
- Si existe:
  - Se valida la estructura con `ReservationSchema`.
  - Si la validación es correcta → HTTP 200 con la reserva.
  - Si hay error de validación → HTTP 500,
    `"Error de validación"` + detalles en `errors`.

### 3.3. `GET /get_reservation_by_id/<reservation_id>`

Reglas:

1. Validación de tipo/valor:
   - Se intenta convertir `reservation_id` a `int`.
   - Si falla (no numérico) → HTTP 400:
     - `"El ID de reserva debe ser un número entero positivo."`
   - Si `reservation_id <= 0` → HTTP 400:
     - `"El ID de reserva debe ser un número positivo mayor que cero."`

2. Búsqueda:
   - Se busca en `reservations` por `reservation_id`.
   - Si no se encuentra → HTTP 404, `"Reserva no encontrada"`.

3. Validación de estructura:
   - Se carga con `reservation_schema.load(reservation)`.
   - Si ok → HTTP 200 con la reserva.
   - Si error de validación → HTTP 500,
     `"Error de validación"` + detalles.

### 3.4. `DELETE /delete_reservation_by_id/<int:reservation_id>`

Reglas:

1. Validación de ID:
   - Flask ya entrega un `int`, pero se valida:
     - Si `reservation_id <= 0` → HTTP 400:
       `"El ID de reserva debe ser un número positivo."`

2. Estructura:
   - Si `reservations` no es lista → HTTP 500,
     `"Estructura de datos inválida para reservas."`

3. Búsqueda:
   - Si no se encuentra la reserva → HTTP 404, `"Reserva no encontrada"`.

4. Validación parcial con Marshmallow:
   - `reservation_schema.load(reservation, partial=True)`
   - Si falla → HTTP 500 con `"Error de validación"`.

5. Eliminación y liberación de asiento:
   - Se elimina la reserva de memoria.
   - Se llama a GestiónVuelos:
     - `PUT /free_seat/{airplane_id}/seats/{seat_number}`.
   - Errores de red:
     - `ConnectionError` → HTTP 503,
       `"No se pudo conectar con GestiónVuelos para liberar el asiento."`
     - `Timeout` → HTTP 504,
       `"Timeout al intentar liberar el asiento en GestiónVuelos."`
   - Si GestiónVuelos responde con status != 200:
     - Se registra en logs, pero la API igual responde 200 al cliente.

6. Respuesta final:
   - HTTP 200 con:
     - `"message": "Reserva eliminada exitosamente"`
     - `"deleted_reservation": { ... }`

### 3.5. `POST /add_reservation`

Flujo crítico:

1. Cuerpo obligatorio:
   - Si `request.get_json()` es `None` → HTTP 400:
     - `"No se recibió cuerpo JSON"`.

2. Validación de payload:
   - `reservation_schema.load(data)`:
     - Campos faltantes o tipos incorrectos → HTTP 400,
       `"Error de validación"` + `errors`.
     - Campos extra (no definidos en el schema) → HTTP 400 (RAISE).

3. Validación de ruta en GestiónVuelos:
   - GET `GESTIONVUELOS_SERVICE/get_all_airplanes_routes`.
   - Errores de red:
     - `ConnectionError` → HTTP 503,
       `"No se pudo conectar con GestiónVuelos al obtener rutas."`
     - `Timeout` → HTTP 504,
       `"Timeout al obtener rutas en GestiónVuelos."`
   - Status != 200 → HTTP 500,
     `"Error al obtener rutas desde GestiónVuelos."`
   - Se busca una ruta con `airplane_route_id == route_id`.
     - Si no existe → HTTP 400,
       `"Ruta con ID {route_id} no encontrada."`
     - Si existe pero `airplane_id` no coincide →
       HTTP 400,
       `"La ruta {route_id} no está asociada al avión {airplane_id}."`

4. Validación del asiento:
   - GET `.../get_airplane_seats/{airplane_id}/seats`.
   - Errores de red:
     - `ConnectionError` → HTTP 503,
       `"No se pudo conectar con GestiónVuelos para verificar asiento."`
     - `Timeout` → HTTP 504,
       `"Timeout al verificar asiento en GestiónVuelos."`
   - Status != 200 → HTTP 500,
     `"Error al verificar estado de asientos."`
   - Se busca el asiento por `seat_number`.
     - Si no existe → HTTP 400,
       `"El asiento especificado no existe para ese avión."`
     - Si existe pero `status != 'Libre'` → HTTP 409,
       `"El asiento {seat_number} no está disponible."`

5. Generación de campos de backend:
   - `reservation_code`:
     - 6 caracteres alfanuméricos (`A-Z0-9`),
       garantizado único en `reservations`.
   - `issued_at`: fecha actual en formato español:
     - `"Enero 13, 2025 - 19:00:00"`.
   - `reservation_id`: `len(reservations) + 1`.

6. Marcar asiento como reservado:
   - PUT `.../update_seat_status/{airplane_id}/seats/{seat_number}` con:
     - `{ "status": "Reservado" }`
   - Errores de red:
     - `ConnectionError` → HTTP 503,
       `"No se pudo conectar con GestiónVuelos al reservar asiento."`
     - `Timeout` → HTTP 504,
       `"Timeout al reservar asiento en GestiónVuelos."`
   - Status != 200 → HTTP 500,
     `"No se pudo reservar el asiento {seat_number}."`

7. Almacenamiento y respuesta:
   - La reserva validada se agrega a `reservations`.
   - HTTP 201 con:
     - `"message": "Reserva creada exitosamente"`
     - `"reservation": { ... }`

### 3.6. `PUT /reservations/<reservation_code>` (editar reserva)

Reglas:

1. Validación de `reservation_code`:
   - `6` caracteres alfanuméricos (`[A-Z0-9]{6}`).
   - Si no cumple → HTTP 400,
     `"El código de reserva debe ser 6 caracteres alfanuméricos."`

2. Búsqueda:
   - Se busca por `reservation_code` (normalizado a `upper()`).
   - Si no existe → HTTP 404, `"Reserva no encontrada"`.

3. Body requerido:
   - Si no hay JSON → HTTP 400,
     `"No se recibió cuerpo JSON."`

4. Campos permitidos:
   - Debe contener **exactamente** estos campos:
     - `seat_number`
     - `email`
     - `phone_number`
     - `emergency_contact_name`
     - `emergency_contact_phone`
   - Si hay faltantes o extras → HTTP 400,
     con mensaje indicando los 5 campos exactos.

5. Sin cambios:
   - Si todos los valores son idénticos a los actuales →
     HTTP 200 con:
     `"message": "La información es idéntica; no se realizaron cambios."`

6. Cambio de asiento:
   - Si `seat_number` cambia:
     - Consultar `GET /get_airplane_seats/{airplane_id}/seats`.
     - Errores de red → 503/504 (mensaje de error genérico).
     - Status != 200 → 500, `"Error verificando estado de los asientos."`
     - Verificar que el nuevo asiento exista y tenga `status == 'Libre'`:
       - No existe → HTTP 400,
         `"Asiento {new_seat} no existe en el avión."`
       - No libre → HTTP 409,
         `"El asiento {new_seat} no está libre."`
     - Liberar asiento anterior:
       - PUT `/free_seat/{airplane_id}/seats/{old_seat}`.
       - Errores de red → 503.
       - Status != 200 → 500, `"No se pudo liberar el asiento anterior."`
     - Reservar nuevo asiento:
       - PUT `/update_seat_status/{airplane_id}/seats/{new_seat}` con `"Reservado"`.
       - Errores de red → 503.
       - Status no en (200, 204) → 500,
         `"No se pudo reservar el nuevo asiento {new_seat}."`

7. Actualizar datos de contacto:
   - Se actualizan `email`, `phone_number`,
     `emergency_contact_name`, `emergency_contact_phone`.

8. Validación final:
   - `reservation_schema.load(reservation)`:
     - Si ok → HTTP 200 con `"reservation"` actualizada.
     - Si error → 400 `"Error de validación"`.

---

## 4. Reglas de negocio – Pagos

### 4.1. Modelo de pago (en memoria)

Cada elemento de `payments` suele incluir:

- `payment_id`: `"PAY"` + 6 dígitos (ej. `PAY123456`), único.
- `reservation_id`: ID de reserva asociado.
- `amount`: monto (float, normalmente `reservation.price`).
- `currency`: `"Dolares"` o `"Colones"` (en `create_payment`).
- `payment_method`: `"Tarjeta"`, `"PayPal"`, `"Transferencia"`, etc.
- `status`: `"Pagado"`.
- `payment_date`: fecha en formato español.
- `transaction_reference`: string aleatorio de 12 caracteres.
- Además, muchos campos de la propia reserva (airplane_id, seat_number, etc.).

### 4.2. `GET /get_all_fake_payments`

- Si `payments` está vacío → HTTP 200,
  `"message": "No hay pagos generados actualmente."`
- Si hay pagos → HTTP 200 con la lista completa.

### 4.3. `GET /get_payment_by_id/<payment_id>`

Reglas:

1. Validación de formato:
   - Debe coincidir con `^PAY\d{6}$`.
   - Si no → HTTP 400,
     `"El formato del payment_id es inválido. Debe ser como PAY123456"`.

2. Validar estructura:
   - Si `payments` no es lista → HTTP 500,
     `"Estructura de pagos inválida."`

3. Sin pagos:
   - Si lista vacía → HTTP 404,
     `"No hay pagos generados aún."`

4. Búsqueda:
   - Si se encuentra el pago → HTTP 200 con el pago.
   - Si no → HTTP 404,
     `"No se encontró ningún pago con ID: {payment_id}"`

### 4.4. `DELETE /get_payment_by_id/<payment_id>` (delete_payment_by_id)

Reglas:

- Validación de formato `PAY\d{6}`:
  - Si no cumple → HTTP 400.
- Validación de estructura de `payments` lista:
  - Si no lo es → HTTP 500.
- Si no se encuentra el pago → HTTP 404.
- Si se encuentra:
  - Se elimina el pago de la lista.
  - HTTP 200 con mensaje de éxito.

### 4.5. `POST /create_payment`

Flujo:

1. Body JSON:
   - Debe contener al menos:
     - `reservation_id` (int, > 0).
     - `payment_method` ∈ {"Tarjeta", "PayPal", "Transferencia"}.
     - `currency` opcional, default `"USD"`, pero se valida contra:
       - `"Dolares"`, `"Colones"`.

2. Validaciones:
   - `reservation_id` no entero o <= 0 → HTTP 400.
   - `payment_method` no permitido → HTTP 400.
   - `currency` no soportada → HTTP 400.

3. Verificar reserva:
   - Debe existir en `reservations`.
   - Si no → HTTP 404,
     `"Reserva con ID {reservation_id} no encontrada."`

4. Pago duplicado:
   - Si ya hay un pago con ese `reservation_id` en `payments` → HTTP 409,
     `"Esta reserva ya tiene un pago registrado."`

5. Generar `payment_id` único:
   - `"PAY"` + 6 dígitos, que no exista ya en `payments`.

6. Actualizar reserva:
   - `status` de la reserva se cambia a `"Pagado"`.

7. Notificar a GestiónVuelos:
   - PUT `/update_seat_status/{airplane_id}/seats/{seat_number}` con `"Pagado"`.
   - Errores de red → 503/504.
   - Si status != 200, se registra warning pero no se corta totalmente.

8. Crear el pago:
   - Se arma el dict con datos de reserva + campos de pago.
   - Se agrega a `payments`.

9. Respuesta:
   - HTTP 201 con `"message": "✅ Pago registrado correctamente."` y `"payment"`.

### 4.6. `DELETE /cancel_payment_and_reservation/<payment_id>`

Flujo:

1. Validar formato `PAY\d{6}`:
   - Si no → HTTP 400.

2. Buscar pago:
   - Si no existe → HTTP 404.

3. Tomar datos:
   - `reservation_id`, `airplane_id`, `seat_number` deben estar presentes.
   - Si faltan → HTTP 404,
     `"El pago no tiene los datos completos para liberar la reserva"`.

4. Liberar asiento:
   - PUT `/free_seat/{airplane_id}/seats/{seat_number}`.
   - Si status != 200 → HTTP 500,
     `"No se pudo liberar el asiento en GestiónVuelos."`
   - Cualquier excepción → HTTP 500.

5. Eliminar pago:
   - Se remueve de `payments`.

6. Eliminar reserva:
   - Se busca en `reservations` por `reservation_id` y se elimina si existe.

7. Respuesta:
   - HTTP 200 con:
     - `"message": "Cancelación exitosa: pago y reserva eliminados, asiento liberado."`
     - `"deleted_payment"` y `"deleted_reservation"`.

### 4.7. `PUT /edit_payment/<payment_id>`

Reglas:

1. Validar `payment_id` (formato `PAY\d{6}`):
   - Si no → HTTP 400.

2. Buscar pago:
   - Si no existe → HTTP 404.

3. Body JSON requerido:
   - Si no hay → HTTP 400,
     `"No se recibió cuerpo JSON"`

4. Campos que se pueden actualizar:
   - `payment_method`:
     - Debe ser uno de:
       `"Tarjeta"`, `"PayPal"`, `"Transferencia"`, `"Efectivo"`, `"SINPE"`.
     - Valores fuera de esa lista → HTTP 400, `"Método de pago inválido"`.
   - `payment_date`: se acepta cualquier string.
   - `transaction_reference`: se acepta cualquier string.

5. Respuesta:
   - HTTP 200 con `"Pago actualizado correctamente."` y el `payment` resultante.

---

## 5. Puntos clave para pruebas (manuales y RAG)

- Validar siempre:
  - Códigos de estado HTTP.
  - Mensajes de error/coherencia en español.
  - Efectos colaterales:
    - Cambios en `reservations` / `payments`.
    - Llamadas a GestiónVuelos para asientos.
- Casos interesantes:
  - Crear reserva con ruta/avión desincronizados.
  - Intentar reservar asiento ya “Reservado” o “Pagado”.
  - Editar reserva cambiando a un asiento inexistente o no libre.
  - Crear pagos duplicados.
  - Cancelar pago y verificar que la reserva y asiento se eliminen/liberen.
