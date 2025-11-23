# EXPERIMENTO_RAG_01_add_reservation.md  
_Casos que el agente “RAG tester” debe ser capaz de sugerir para `/add_reservation`_

## 1. Contexto del experimento

Endpoint bajo prueba (microservicio **GestiónReservas**):

- `POST /add_reservation`  
- Crea una nueva reserva de vuelo, validando:
  - Estructura y tipos con `ReservationSchema` (Marshmallow, `unknown=RAISE`).
  - Que la **ruta** (`airplane_route_id`) exista en GestiónVuelos.
  - Que la ruta esté asociada al **airplane_id** indicado.
  - Que el **asiento** exista para ese avión y esté en estado `"Libre"`.
  - Que se pueda **marcar el asiento como “Reservado”** en GestiónVuelos.

Campos relevantes del body (según `ReservationSchema`):

Obligatorios:
- `passport_number` (str)
- `full_name` (str)
- `email` (email válido)
- `phone_number` (str)
- `emergency_contact_name` (str)
- `emergency_contact_phone` (str)
- `airplane_id` (int)
- `airplane_route_id` (int)
- `seat_number` (str)
- `status` (str) ∈ {`"Reservado"`, `"Pagado"`} → para creación normalmente `"Reservado"`.

Generados en backend:
- `reservation_id` (int)
- `reservation_code` (str, 6 caracteres alfanuméricos)
- `issued_at` (str, fecha/hora en español)

---

## 2. Objetivo del experimento

Que el agente RAG tester, a partir de:

- `ENDPOINTS_GestionReservas.md`
- Reglas de negocio en `README_testing.md`
- (Opcionalmente) ejemplos previos de reservas válidas

sea capaz de sugerir **casos de prueba API** para `/add_reservation` que cubran:

1. Caso feliz completo (reserva nueva, asiento libre, ruta válida).
2. Errores de **estructura/esquema** (faltan campos, sobran campos, tipos inválidos).
3. Errores de **dominio** (status inválido, email inválido).
4. Errores de **negocio / integraciones**:
   - ruta no existe,
   - ruta no asociada al avión,
   - asiento no existe,
   - asiento no está libre.

---

## 3. Suposiciones técnicas para los tests

Para que los casos sean ejecutables:

- Ya existe al menos un avión y una ruta válidos en GestiónVuelos (creados por un fixture previo).
- Hay al menos un asiento `"Libre"` para ese avión.
- El test puede obtener:
  - un `airplane_id` válido,
  - un `airplane_route_id` válido asociado a ese avión,
  - un `seat_number` libre,
  usando ya sea:
  - llamadas directas al microservicio GestiónVuelos, o  
  - un endpoint auxiliar como `GET /__state` en GestiónVuelos (si existe).

El agente debe reflejar estos supuestos en la **descripción** de los casos (por ejemplo: “usar un airplane_id y airplane_route_id válidos obtenidos del estado actual del sistema”).

---

## 4. Casos mínimos que el RAG debe sugerir

### 4.1. Caso feliz

**ID:** `ADD_RES_OK_01`  
**Tipo:** `happy_path`  
**Descripción:**  
Crear una reserva válida para un asiento `"Libre"` de una ruta existente y asociada al avión correcto.

- **Precondición:**
  - Obtener `airplane_id`, `airplane_route_id` y `seat_number` `"Libre"` desde GestiónVuelos.
- **Payload ejemplo (esqueleto):**
  ```json
  {
    "passport_number": "A12345678",
    "full_name": "Juan Pérez",
    "email": "juan.perez@example.com",
    "phone_number": "+50688889999",
    "emergency_contact_name": "Carlos Jiménez",
    "emergency_contact_phone": "+50677778888",
    "airplane_id": 1,
    "airplane_route_id": 10,
    "seat_number": "1A",
    "status": "Reservado"
  }
