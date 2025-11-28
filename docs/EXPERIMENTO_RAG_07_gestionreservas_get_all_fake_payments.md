# EXPERIMENTO_RAG_07_gestionreservas_get_all_fake_payments

## 1. Endpoint bajo prueba

- Servicio: **GestiónReservas**
- Método: **GET**
- URL:  
  `/get_all_fake_payments`
- Responsabilidad:
  Exponer todos los pagos falsos almacenados en memoria (lista global `payments`), generados al arrancar el microservicio con `generate_fake_payments(...)` y aumentados luego con `/create_payment`.

---

## 2. Contrato funcional (según `app.py`)

Implementación relevante:

```python
@app.route('/get_all_fake_payments', methods=['GET'])
def get_all_fake_payments():
    """
    Summary: Lista todos los pagos generados falsamente
    Description:
      Devuelve una lista de pagos simulados almacenados en memoria, útiles para pruebas o demostraciones.
      Si no hay pagos generados, se devuelve un mensaje indicando la ausencia de registros.
    ---
    tags:
      - Payments
    ...
    """
    if not payments:
        return jsonify({'message': 'No hay pagos generados actualmente.'}), 200
    return jsonify(payments), 200
2.1. Caso: hay pagos en memoria
Condición:

La lista global payments no está vacía (if not payments es False).

Respuesta:

200 OK

Content-Type: application/json

Body: lista JSON de pagos, por ejemplo:

json
Copiar código
[
  {
    "payment_id": "PAY123456",
    "reservation_id": 1,
    "amount": 385.25,
    "currency": "USD",
    "payment_method": "Tarjeta",
    "status": "Pagado",
    "payment_date": "Abril 16, 2025 - 15:22:00",
    "transaction_reference": "X8GJ9KL23RT7",
    "...otros campos de la reserva asociada..."
  }
]
No hay validación Marshmallow aquí: el endpoint devuelve directamente el contenido de la lista payments.

2.2. Caso: no hay pagos en memoria
Condición:

not payments es True (lista vacía).

Respuesta:

200 OK (mismo código que cuando sí hay pagos)

Body JSON:

json
Copiar código
{
  "message": "No hay pagos generados actualmente."
}
A diferencia de otros endpoints que usan 204, aquí el contrato codificado es siempre 200, con dos variantes de cuerpo:

lista de pagos (cuando hay registros),

objeto con message (cuando no hay).

2.3. Relación con otras partes del sistema
En el if __name__ == '__main__'::

python
Copiar código
# Generar las reservas una sola vez al arrancar el servidor
reservations.extend(generate_fake_reservations(3))

## Generar los pagos una sola vez al arrancar el servidor
payments = generate_fake_payments(1)
generate_fake_payments(max_pagados):

Recorre una muestra de reservations.

Marca la reserva como "Pagado".

Llama a GestiónVuelos para marcar el asiento como "Pagado".

Genera registros de pago con campos como:

payment_id (PAY + 6 dígitos)

reservation_id

amount, currency

payment_method

status

payment_date

transaction_reference

y mezcla info de la reserva (airplane_id, seat_number, etc.).

Además, /create_payment también añade elementos a payments, por lo que este endpoint lista:

pagos generados automáticamente al arrancar,

pagos creados manualmente vía /create_payment.
