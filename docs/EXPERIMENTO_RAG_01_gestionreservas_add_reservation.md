# EXPERIMENTO_RAG_01_gestionreservas_add_reservation

## 1. Propósito del experimento

Verificar, mediante pruebas de contrato y apoyo RAG/MCP, el comportamiento del endpoint:

- **Microservicio**: GestiónReservas  
- **Endpoint**: `POST /add_reservation`  

Objetivos:

1. Validar que el endpoint aplica correctamente las reglas de negocio:
   - Validación del cuerpo JSON (campos requeridos y tipos).
   - Validación de la relación ruta ↔ avión contra GestiónVuelos.
   - Validación de existencia y disponibilidad del asiento.
   - Generación adecuada de `reservation_id`, `reservation_code` e `issued_at`.
2. Verificar el manejo de errores:
   - Errores de validación de datos.
   - Asiento inexistente / no disponible.
   - Rutas inexistentes o no asociadas al avión.
   - Problemas de conexión / timeout con GestiónVuelos.
3. Documentar claramente el contrato para que QA-Copilot (vía MCP) pueda proponer y ejecutar casos de prueba de manera guiada.

---

## 2. Endpoint bajo prueba

- **Método**: `POST`  
- **Ruta**: `/add_reservation`  
- **Servicio**: GestiónReservas (`http://localhost:5002` en entorno local)

### 2.1. Request: cuerpo JSON esperado

El endpoint invoca `reservation_schema.load(data)` con `unknown = RAISE`, por lo que:

- Se **requieren** los siguientes campos:

```json
{
  "passport_number": "string",
  "full_name": "string",
  "email": "string con formato de email válido",
  "phone_number": "string",
  "emergency_contact_name": "string",
  "emergency_contact_phone": "string",
  "airplane_id": "int",
  "airplane_route_id": "int",
  "seat_number": "string (ej. '1A')",
  "status": "string ('Reservado' o 'Pagado')"
}
