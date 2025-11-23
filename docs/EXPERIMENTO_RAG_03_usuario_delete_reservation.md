# EXPERIMENTO_RAG_03_usuario_delete_reservation

## 1. Objetivo del contrato

Validar, mediante pruebas de contrato tipo “caja negra” (black-box API testing), el comportamiento del endpoint de eliminación de reservas expuesto por el microservicio **Usuario**:

> `DELETE /usuario/delete_reservation_by_id/<reservation_id>`

Este endpoint coordina la eliminación de una reserva en el microservicio **GestiónReservas** y la liberación del asiento correspondiente en **GestiónVuelos**.

El objetivo es asegurar que:

1. Se apliquen correctamente las validaciones de entrada (ID numérico positivo).
2. Se gestione adecuadamente el caso de reservas inexistentes.
3. El caso feliz elimine la reserva y libere el asiento.
4. Los mensajes y códigos de estado HTTP sean consistentes con el contrato funcional esperado.

---

## 2. Endpoint bajo prueba

- **Método:** `DELETE`
- **Ruta en Usuario:**  
  `DELETE /usuario/delete_reservation_by_id/<reservation_id>`
- **Parámetros de ruta:**
  - `reservation_id` (int, requerido):  
    ID numérico de la reserva a eliminar.  
    Debe ser un entero positivo (`> 0`).

- **Respuestas esperadas (según implementación actual):**
  - `200 OK`  
    - Reserva eliminada correctamente en GestiónReservas.  
    - Se intenta liberar el asiento en GestiónVuelos.  
    - Cuerpo JSON (forma típica):
      ```json
      {
        "message": "Reserva eliminada exitosamente",
        "deleted_reservation": {
          "reservation_id": 5,
          "reservation_code": "ABC123",
          "airplane_id": 1,
          "seat_number": "1A",
          "status": "Reservado",
          "...": "otros campos de la reserva"
        }
      }
      ```
  - `400 Bad Request`  
    - ID inválido (<= 0).  
    - Ejemplo de mensaje:
      ```json
      { "message": "El ID debe ser un número positivo." }
      ```
  - `404 Not Found`  
    - La reserva no existe en GestiónReservas.  
    - Ejemplo de mensaje:
      ```json
      { "message": "Reserva no encontrada" }
      ```
  - `503 Service Unavailable`  
    - Error de conexión con GestiónVuelos al liberar el asiento.
  - `504 Gateway Timeout`  
    - Timeout al intentar liberar el asiento en GestiónVuelos.
  - `500 Internal Server Error`  
    - Error interno inesperado o estructura inválida en la respuesta de GestiónReservas.

---

## 3. Entorno de prueba

- **Lenguaje:** Python 3.13.2  
- **Framework de pruebas:** `pytest 8.4.0`
- **Sistema operativo:** Windows (PowerShell)
- **Microservicios involucrados:**
  - `Usuario` corriendo en `http://localhost:5003`
  - `GestiónReservas` corriendo en el puerto configurado en `GESTIONRESERVAS_SERVICE`
  - `GestiónVuelos` corriendo en el puerto configurado en `GESTIONVUELOS_SERVICE`
- **Archivo de pruebas:**  
  `tests/api/test_usuario_delete_reservation_rag.py`
- **Ejecución de pruebas:**
  ```bash
  pytest tests/api/test_usuario_delete_reservation_rag.py -vv
