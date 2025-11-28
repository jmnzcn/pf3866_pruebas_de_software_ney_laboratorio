# EXPERIMENTO_RAG_05_gestionreservas_edit_reservation

## 1. Endpoint bajo prueba

- Servicio: **GestiónReservas**
- Método: **PUT**
- URL:
  `/reservations/<string:reservation_code>`
- Responsabilidad:
  Modificar una reserva existente, permitiendo:
  - Cambiar el número de asiento (si está libre).
  - Actualizar datos de contacto del pasajero y contacto de emergencia.

---

## 2. Contrato funcional (según `app.py`)

### 2.1. Validación de `reservation_code`

1. Se normaliza el código:
   - `code = reservation_code.strip().upper()`
2. Validación de formato:
   - Debe cumplir: `^[A-Z0-9]{6}$`
   - Si NO cumple:
     - `400 Bad Request`
     - Body (JSON):
       ```json
       {
         "message": "El código de reserva debe ser 6 caracteres alfanuméricos."
       }
       ```

### 2.2. Búsqueda de la reserva

- Se busca en la lista en memoria `reservations` por `reservation_code`:
  ```python
  reservation = next((r for r in reservations if r['reservation_code'] == code), None)
Si no se encuentra:

404 Not Found

Body:

json
Copiar código
{ "message": "Reserva no encontrada" }
2.3. Lectura y validación del body JSON
En el código:

python
Copiar código
data = request.get_json()
if not data:
    return jsonify({'message': 'No se recibió cuerpo JSON.'}), 400
Intención de diseño:

Si el body está ausente o vacío:

400 Bad Request

Body:

json
Copiar código
{
  "message": "No se recibió cuerpo JSON."
}
Comportamiento real (Flask):

Si se invoca el endpoint SIN Content-Type: application/json y sin body JSON,
Flask devuelve antes de llegar a la lógica:

415 Unsupported Media Type

Body HTML estándar de Flask.

El test RAG refleja este comportamiento para el caso de “body ausente”.

2.4. Validación estricta de campos del body
Se espera exactamente este conjunto de campos:

python
Copiar código
allowed = {
  "seat_number",
  "email",
  "phone_number",
  "emergency_contact_name",
  "emergency_contact_phone",
}
Se compara el conjunto recibido:

python
Copiar código
received = set(data.keys())
if received != allowed:
    return jsonify({
        'message': 'El body debe incluir exactamente estos campos sin extras ni faltantes: '
                   'seat_number, email, phone_number, emergency_contact_name, emergency_contact_phone.'
    }), 400
Casos cubiertos:

Falta un campo requerido → 400.

Hay uno o más campos extra → 400.

2.5. Detección de “sin cambios”
Si todos los campos del body coinciden con los de la reserva actual:

python
Copiar código
identical = all(data[field] == reservation.get(field) for field in allowed)
if identical:
    return jsonify({'message': 'La información es idéntica; no se realizaron cambios.'}), 200
Respuesta:

200 OK

Body:

json
Copiar código
{ "message": "La información es idéntica; no se realizaron cambios." }
2.6. Cambio de asiento (interacción con GestiónVuelos)
Solo aplica si seat_number cambia:

python
Copiar código
new_seat = data['seat_number']
if new_seat != reservation['seat_number']:
    airplane_id = reservation['airplane_id']
    # 1) Consultar lista de asientos en GestiónVuelos
    # 2) Validar existencia y estado 'Libre'
    # 3) Liberar asiento anterior
    # 4) Reservar el nuevo asiento
Respuestas relevantes:

Error al consultar asientos:

Si GET /get_airplane_seats/<airplane_id>/seats devuelve código != 200:

500 Internal Server Error

{"message": "Error verificando estado de los asientos."}

Asiento no existe en el avión:

400 Bad Request

{"message": "Asiento <X> no existe en el avión."}

Asiento no está libre:

409 Conflict

{"message": "El asiento <X> no está libre."}

Error al liberar asiento anterior en GestiónVuelos:

Si hay ConnectionError o Timeout:

503 Service Unavailable

{"message": "Error liberando el asiento anterior en GestiónVuelos."}

No se puede liberar asiento anterior (respuesta != 200):

500 Internal Server Error

{"message": "No se pudo liberar el asiento anterior."}

Error al reservar el nuevo asiento:

Si hay ConnectionError o Timeout:

503 Service Unavailable

{"message": "Error reservando el nuevo asiento en GestiónVuelos."}

Si código no es 200 ni 204:

500 Internal Server Error

{"message": "No se pudo reservar el nuevo asiento <X>."}

Si todo va bien:

El asiento anterior queda liberado en GestiónVuelos.

El nuevo asiento queda con estado "Reservado" en GestiónVuelos.

El campo seat_number de la reserva se actualiza a new_seat.

2.7. Actualización de datos de contacto y validación final
Después de gestionar el asiento:

python
Copiar código
for field in ['email', 'phone_number', 'emergency_contact_name', 'emergency_contact_phone']:
    reservation[field] = data[field]
Luego se valida con Marshmallow:

python
Copiar código
validated = reservation_schema.load(reservation)
Si hay errores de validación:

400 Bad Request

Body:

json
Copiar código
{
  "message": "Error de validación",
  "errors": { ... }
}
Si todo es correcto:

200 OK

Body:

json
Copiar código
{
  "message": "Reserva y datos actualizados exitosamente",
  "reservation": { ...reserva actualizada y validada... }
}
