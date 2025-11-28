# EXPERIMENTO_RAG_06_gestionreservas_get_fake_reservations

## 1. Endpoint bajo prueba

- Servicio: **GestiónReservas**
- Método: **GET**
- URL:  
  `/get_fake_reservations`
- Responsabilidad:
  Exponer las reservas de vuelo que están almacenadas en memoria (lista global `reservations`), generadas al arrancar el microservicio mediante `generate_fake_reservations(...)`.

---

## 2. Contrato funcional (según `app.py`)

Implementación relevante:

```python
@app.route('/get_fake_reservations', methods=['GET'])
def get_fake_reservations():
    """
    Summary: Obtiene todas las reservas generadas
    Description:
      Recupera todas las reservas de vuelo generadas en memoria.
      Si no hay reservas disponibles, retorna un estado 204 sin contenido.
    ---
    ...
    """
    if not reservations:
        return jsonify({'message': 'No hay reservas generadas actualmente.'}), 204

    return jsonify(reservations), 200
2.1. Casos principales
Hay reservas en memoria

Condición:

La lista global reservations no está vacía (if not reservations es False).

Respuesta:

200 OK

Cabecera: Content-Type: application/json

Body: lista JSON de reservas, por ejemplo:

json
Copiar código
[
  {
    "reservation_id": 1,
    "reservation_code": "ABC123",
    "passport_number": "A12345678",
    "full_name": "Luis Gómez",
    "email": "luis@example.com",
    "phone_number": "+50688889999",
    "emergency_contact_name": "Carlos Jiménez",
    "emergency_contact_phone": "+50677778888",
    "airplane_id": 1,
    "flight_number": "LAV101",
    "airplane_route_id": 10,
    "seat_number": "1A",
    "reservation_date": "2025-04-09 16:55:12",
    "status": "Reservado",
    "price": 200.0
  }
]
No se aplica validación Marshmallow aquí; se devuelve lo que esté en reservations.

No hay reservas en memoria

Condición:

not reservations es True (lista vacía o no inicializada).

Respuesta:

204 No Content (aunque se devuelve JSON, el contrato de código usa 204)

Body JSON:

json
Copiar código
{ "message": "No hay reservas generadas actualmente." }
Este caso puede darse, por ejemplo, si:

El servidor se levantó sin ejecutar generate_fake_reservations, o

Algún código de test limpió la lista reservations (no ocurre desde caja negra, pero es una posibilidad técnica).

2.2. Relaciones con otros componentes
La lista reservations se alimenta en if __name__ == '__main__': con:

python
Copiar código
reservations.extend(generate_fake_reservations(3))
generate_fake_reservations(...):

Llama a GestiónVuelos:

/get_all_airplanes_routes para obtener rutas.

/get_random_free_seat/<airplane_id> para encontrar asientos libres.

/update_seat_status/<airplane_id>/seats/<seat_number> para marcarlos como "Reservado".

Construye reservas con campos como:

reservation_id

reservation_code

passport_number

full_name, email, phone_number

emergency_contact_name, emergency_contact_phone

airplane_id, flight_number, airplane_route_id

seat_number, reservation_date, status, price

El endpoint no hace:

Validación Marshmallow de cada reserva.

Paginación.

Filtros de búsqueda.

3. Casos de prueba cubiertos por este experimento
Archivo asociado:
tests/api/test_gestionreservas_get_fake_reservations_rag.py

3.1. Caso “lista con reservas”
Objetivo:

Verificar que, cuando reservations no está vacía, el endpoint devuelve:

Código 200.

Un array JSON de elementos tipo “reserva”.

Estrategia desde caja negra:

Hacer GET /get_fake_reservations.

Si el código es 200:

Parsear r.json().

Verificar que:

Es una lista.

Tiene al menos 1 elemento.

Cada elemento es un dict con campos clave como:

reservation_id

reservation_code

airplane_id

seat_number

status

reservation_id es entero positivo.

El test debe ser tolerante a valores específicos (generados con Faker), verificando solo forma/estructura.

3.2. Caso “sin reservas”
Objetivo:

Cubrir el contrato cuando reservations está vacía.

Estrategia desde caja negra:

Hacer GET /get_fake_reservations.

Si el servidor está recién iniciado y generó reservas, puede devolver 200.

El test contempla ambas posibilidades:

Si status_code == 204:

De acuerdo al código, puede venir un body JSON con:

json
Copiar código
{ "message": "No hay reservas generadas actualmente." }
El test:

Acepta 204 como señal de “sin reservas”.

Si status_code == 200 pero json no es lista o está vacía:

También se interpreta como escenario “sin reservas útiles”.

Se valida que el mensaje (si viene como dict) contenga "No hay reservas" o que la lista tenga len == 0.

Así, el test es robusto frente a:

Implementaciones que cambiasen a 200 + mensaje.

Cambios en los datos iniciales generados por generate_fake_reservations.

4. Precondiciones y entorno
Microservicio GestiónReservas corriendo en:

GESTIONRESERVAS_BASE_URL (por defecto http://localhost:5002 en los tests).

Idealmente, GestiónVuelos también levantado, para que generate_fake_reservations funcione correctamente al inicio.

No se requiere cuerpo JSON ni cabecera Content-Type especial:

Es un GET sin parámetros ni query string.
