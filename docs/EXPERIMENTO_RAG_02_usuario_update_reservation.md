# EXPERIMENTO_RAG_02_usuario_update_reservation

Microservicio: `usuario`  
Endpoint bajo prueba: `PUT /update_reservation/{reservation_code}`

## Objetivo

Definir casos de prueba que un agente RAG (QA-Copilot) debería sugerir para validar el comportamiento de:

- Validaciones locales sobre:
  - Formato del `reservation_code`.
  - Presencia del body JSON.
  - Estructura exacta del body (campos requeridos, sin extras).
- Escenarios de actualización donde:
  - No hay cambios reales en la información.
  - Se actualiza el asiento y los datos de contacto correctamente.

Estos casos se enfocan en el contrato descrito en `ENDPOINTS_Usuario.md` y en la implementación del endpoint
`/update_reservation/{reservation_code}` en `app.py` del microservicio `usuario`.

---

## Información del endpoint

- **Método:** `PUT`
- **Ruta:** `/update_reservation/{reservation_code}`
- **Path param:**
  - `reservation_code` (string, exactamente 6 caracteres alfanuméricos, p.ej. `ABC123`)
- **Body esperado (JSON):**  
  Debe incluir **exactamente** estos cinco campos (ni más ni menos):

```json
{
  "seat_number": "2C",
  "email": "nuevo@example.com",
  "phone_number": "+50612345678",
  "emergency_contact_name": "Nuevo Contacto",
  "emergency_contact_phone": "+50687654321"
}
