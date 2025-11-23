# README_testing.md
Reglas de negocio y criterios de prueba para FlightBooking (microservicios)

Este documento resume las reglas de negocio importantes que deben usarse como **fuente de verdad** al diseñar casos de prueba (manuales o generados con MCP/RAG) para el sistema FlightBooking, especialmente para el microservicio **GestiónVuelos**.

La idea es que cualquier herramienta de IA que sugiera casos de prueba use **estas reglas**, y no invente requisitos que las contradigan.

---

## 1. Contexto general del sistema

- El sistema está basado en microservicios:
  - `gestiovuelos` (GestiónVuelos): aviones, asientos y rutas.
  - `gestionreservas`: reservas, pagos y estados de asientos asociados.
  - `usuarios`: orquestación / consumo de otros servicios.

- Todo el estado está en memoria:
  - Listas globales (por ejemplo `airplanes`, `seats`, `airplanes_routes`).
  - No hay base de datos ni archivos persistentes.
  - Al iniciar, se generan:
    - 3 aviones iniciales (`airplane_id` 1, 2, 3).
    - Sus asientos correspondientes.
    - 3 rutas iniciales.

- Estándar de HTTP en general:
  - `200 OK`: operación exitosa (lecturas, actualizaciones, borrados).
  - `201 Created`: creación exitosa (aviones, rutas).
  - `400 Bad Request`: validación de datos / parámetros inválidos.
  - `404 Not Found`: entidad no encontrada (avión, ruta, asiento).
  - `500 Internal Server Error`: problemas internos o estructuras corruptas.

---

## 2. Endpoints clave de GestiónVuelos

### 2.1 Diagnóstico

1. `GET /health`
   - Siempre debe responder `200` si el servicio está vivo.
   - Cuerpo esperado:
     ```json
     { "status": "ok", "instance_id": "<string no vacío>" }
     ```
   - Cabecera HTTP:
     - `X-Instance-Id`: identificador de proceso/instancia (no vacío).

2. `GET /__state`
   - Devuelve un resumen del estado interno:
     ```json
     {
       "instance_id": "<string>",
       "airplanes_count": <int>,
       "airplane_ids": [<int>, ...],
       "routes_count": <int>
     }
     ```
   - Debe responder `200` si el servicio funciona y las estructuras están sanas.

---

## 3. Reglas de negocio: Aviones (`Airplanes`)

### 3.1 Estructura de avión

Un avión tiene la siguiente forma lógica:

```json
{
  "airplane_id": <int positivo>,
  "model": "<string>",
  "manufacturer": "<string>",
  "year": <int positivo>,
  "capacity": <int positivo>
}
