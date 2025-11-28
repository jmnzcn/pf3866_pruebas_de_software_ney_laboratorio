# EXPERIMENTO_RAG_08_gestionreservas_get_payment_by_id

## 1. Endpoint bajo prueba

- Servicio: **GestiónReservas**
- Método: **GET**
- URL:  
  `/get_payment_by_id/<string:payment_id>`
- Responsabilidad:
  Consultar y devolver los detalles de un pago específico, identificado por un `payment_id` con formato tipo `PAY123456`, utilizando únicamente la lista en memoria `payments`.

---

## 2. Contrato funcional (según `app.py`)

Implementación relevante:

```python
@app.route('/get_payment_by_id/<string:payment_id>', methods=['GET'])
def get_payment_by_id(payment_id):
    logging.info(f"🔍 Buscando pago con ID: {payment_id}")

    # Validación 1: Formato correcto del payment_id
    if not re.match(r"^PAY\d{6}$", payment_id.strip().upper()):
        return jsonify({'message': 'El formato del payment_id es inválido. Debe ser como PAY123456'}), 400

    # Validación 2: Asegurar que payments sea una lista
    if not isinstance(payments, list):
        logging.error("❌ Estructura de pagos inválida: no es una lista.")
        return jsonify({'message': 'Estructura de pagos inválida.'}), 500

    # Validación 4: Si no hay pagos aún
    if not payments:
        logging.warning("⚠️ No hay pagos generados en memoria.")
        return jsonify({'message': 'No hay pagos generados aún.'}), 404

    # Buscar el pago
    payment = next((p for p in payments if p['payment_id'] == payment_id), None)

    if payment:
        return jsonify(payment), 200

    return jsonify({'message': f'No se encontró ningún pago con ID: {payment_id}'}), 404
2.1. Formato de payment_id
El endpoint recibe el identificador como parte del path:
/get_payment_by_id/<payment_id>

Regla de formato:

Internamente se valida con:

python
Copiar código
re.match(r"^PAY\d{6}$", payment_id.strip().upper())
Es decir:

Se hace strip() y upper() al valor recibido.

Debe iniciar con "PAY" seguido de exactamente 6 dígitos (0–9).

Si el formato es inválido:

Respuesta:

400 Bad Request

JSON:

json
Copiar código
{
  "message": "El formato del payment_id es inválido. Debe ser como PAY123456"
}
Comentario importante:

La validación de formato es case-insensitive (porque se usa .upper()), pero la búsqueda posterior en la lista payments compara el payment_id tal como llega en el path.

Recomendación práctica: siempre invocar el endpoint con payment_id en mayúsculas (PAY123456) para evitar desajustes.

2.2. Validación de estructura de payments
Antes de buscar el pago, el código asegura que la estructura global payments sea una lista:

python
Copiar código
if not isinstance(payments, list):
    return jsonify({'message': 'Estructura de pagos inválida.'}), 500
Si payments no es una lista:

500 Internal Server Error

JSON:

json
Copiar código
{ "message": "Estructura de pagos inválida." }
2.3. Caso: no hay pagos en memoria
Si payments es una lista pero está vacía:

python
Copiar código
if not payments:
    return jsonify({'message': 'No hay pagos generados aún.'}), 404
Respuesta:

404 Not Found

JSON:

json
Copiar código
{ "message": "No hay pagos generados aún." }
Este comportamiento ocupa el mismo código de estado (404) tanto para “no hay pagos en absoluto” como para “pago no encontrado por ID” (ver siguiente sección).

2.4. Búsqueda del pago por ID
Si pasa las validaciones anteriores, se busca en la lista:

python
Copiar código
payment = next((p for p in payments if p['payment_id'] == payment_id), None)
Si se encuentra:

200 OK

Body: el objeto completo del pago, por ejemplo:

json
Copiar código
{
  "payment_id": "PAY123456",
  "reservation_id": 1,
  "amount": 150.0,
  "currency": "Dolares",
  "payment_method": "Tarjeta",
  "status": "Pagado",
  "payment_date": "Abril 29, 2025 - 13:00:00",
  "transaction_reference": "X1Y2Z3A4B5C6",
  "...otros campos de la reserva asociada..."
}
Si no se encuentra un pago con ese payment_id:

404 Not Found

JSON:

json
Copiar código
{ "message": "No se encontró ningún pago con ID: PAY999999" }
Resumen de códigos:

Situación	Código	message (resumen)
Formato de payment_id inválido	400	"El formato del payment_id es inválido..."
payments no es lista	500	"Estructura de pagos inválida."
No hay ningún pago en memoria	404	"No hay pagos generados aún."
No existe pago con ese payment_id	404	"No se encontró ningún pago con ID: <id>"
Pago encontrado	200	Se devuelve el objeto de pago completo
