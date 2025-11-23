# EXPERIMENTO_RAG_05_usuario_cancel_payment_and_reservation

Pruebas de contrato (black-box) asistidas por RAG para el endpoint:

`DELETE /cancel_payment_and_reservation/<payment_id>`

del microservicio **Usuario**.

---

## 1. Objetivo del experimento

Validar, mediante pruebas de contrato guiadas por RAG, que el endpoint:

`DELETE /cancel_payment_and_reservation/<payment_id>`

del microservicio **Usuario**:

1. Valida correctamente el formato del `payment_id`.
2. Propaga adecuadamente los códigos de respuesta de GestiónReservas.
3. Devuelve mensajes JSON coherentes en los escenarios de error y en el caso feliz.
4. Expone un contrato estable para consumidores externos (por ejemplo, un frontend o un orquestador).

El foco es el contrato HTTP del microservicio **Usuario** (status codes + estructura/mensajes de la respuesta), no la lógica interna de GestiónReservas ni de GestiónVuelos.

---

## 2. Alcance y Supuestos

- Servicio bajo prueba: **Usuario** (Flask).
- Endpoint bajo prueba: `DELETE /cancel_payment_and_reservation/<payment_id>`.
- Otros microservicios (GestiónReservas, GestiónVuelos) se consideran cajas negras.
- Se asume que:
  - Existe al menos un **pago** válido en memoria asociado a una reserva.
  - La configuración por defecto de entorno es:
    - `USUARIO_BASE_URL=http://localhost:5003`
- Las pruebas deben ser **idempotentes a nivel de datos de prueba** o, al menos, dejar el sistema en un estado coherente.

---

## 3. Contrato esperado del endpoint

### 3.1. Definición (según código de Usuario)

```http
DELETE /cancel_payment_and_reservation/<payment_id>
