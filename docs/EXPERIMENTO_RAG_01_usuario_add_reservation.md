# EXPERIMENTO_RAG_01_usuario_add_reservation

Pruebas de contrato para el endpoint de **creación de reservas** expuesto por el microservicio **Usuario**, integradas con el enfoque de **RAG/MCP**.

Archivo de pruebas asociado (propuesto):  
`tests/api/test_usuario_add_reservation_rag.py`


## 1. Descripción general

Este experimento valida el comportamiento del endpoint:

> `POST /usuario/add_reservation`

que actúa como fachada de orquestación entre:

- **GestiónVuelos**:
  - Validar relación ruta ↔ avión.
  - Validar existencia y disponibilidad del asiento.
  - Marcar el asiento como `"Reservado"` tras crear la reserva.
- **GestiónReservas**:
  - Crear la reserva en memoria.

Los `case_id` definidos aquí sirven para:

- Probar el contrato HTTP de la API Usuario.
- Servir como unidades de conocimiento en un sistema **RAG/MCP** (cada caso explica qué se espera que ocurra y por qué).


## 2. Endpoint bajo prueba

| Endpoint                       | Método | Descripción breve                                                                      |
|--------------------------------|--------|-----------------------------------------------------------------------------------------|
| `/usuario/add_reservation`    | POST   | Crea una nueva reserva validando datos, ruta↔avión, asiento Libre y luego reservándolo |

### 2.1. Validaciones locales (Usuario)

Según `ReservationCreationSchema` y el código de `usuario_add_reservation`:

1. Cuerpo JSON:
   - Si no hay JSON, no es dict o está vacío → `400`  
     `{"message": "No se recibió cuerpo JSON"}`

2. Esquema de entrada (campos requeridos):

   ```json
   {
     "passport_number": "...",
     "full_name": "...",
     "email": "correo@valido",
     "phone_number": "...",
     "emergency_contact_name": "...",
     "emergency_contact_phone": "...",
     "airplane_id": 1,
     "airplane_route_id": 10,
     "seat_number": "1A",
     "status": "Reservado"
   }
