# EXPERIMENTO_RAG_02_gestionreservas_get_reservation_by_code

Pruebas de contrato para el endpoint de GestiónReservas:

`GET /get_reservation_by_code/<reservation_code>`

---

## 1. Objetivo

Verificar, mediante pruebas de caja negra, el comportamiento del endpoint:

- Validación de formato de `reservation_code`.
- Manejo de reservas inexistentes.
- Caso feliz recuperando una reserva real generada por el sistema.
- Mensajes y códigos de estado HTTP coherentes con lo definido en `app.py`.

---

## 2. Endpoint bajo prueba

- **Servicio**: GestiónReservas  
- **Base URL (local)**: `http://localhost:5002`
- **Método**: `GET`
- **Ruta**: `/get_reservation_by_code/<reservation_code>`

### 2.1 Comportamiento según `app.py`

Resumen de la función:

```python
@app.route('/get_reservation_by_code/<reservation_code>', methods=['GET'])
def get_reservation_by_code(reservation_code):
    # 1) Log y validación de formato:
    #    - Debe ser string alfanumérico de 6 caracteres: ^[A-Z0-9]{6}$
    #    - Se normaliza con reservation_code.upper()
    #    - Si no cumple: 400 + message "El código de reserva debe ser un string alfanumérico de 6 caracteres."
    #
    # 2) Búsqueda en la lista global "reservations" por reservation_code exacto.
    #    - Si no se encuentra: 404 + message "Reserva no encontrada".
    #
    # 3) Validación de la reserva encontrada con ReservationSchema (Marshmallow).
    #    - Si todo OK: 200 + objeto JSON de la reserva.
    #
    # 4) Errores:
    #    - ValidationError: 500 + message "Error de validación" + detalle en "errors".
    #    - Cualquier excepción: 500 + message "Error interno del servidor".
