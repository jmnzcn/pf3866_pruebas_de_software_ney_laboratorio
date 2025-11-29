# EXPERIMENTO_RAG_09 – Endpoint `/add_airplane_route`

Experimento RAG enfocado en:

- `POST /add_airplane_route` del microservicio `GestiónVuelos`.

---

## 1. Objetivo

1. Validar que el agente:
   - Comprenda todas las validaciones de `AirplaneRouteSchema`.
   - Aplique reglas de negocio sobre fechas y duplicados (IDs, flight_number, ruta idéntica).
   - Use la traducción de meses en español → inglés para parseo de fechas.

2. Garantizar que los tests:
   - Cubran casos de fechas ordenadas y desordenadas.
   - Verifiquen campos generados: `flight_time`.

---

## 2. Formato de petición

Para cada caso (GV-ROUTEADD-XX):

> “Basándote en el endpoint `/add_airplane_route` en `ENDPOINTS_GestionVuelos.md` y `README_testing.md`, genera un test de `pytest` para GV-ROUTEADD-XX, con:
> - JSON de entrada.
> - Expectativas de status y campos (`flight_time`, fechas formateadas).
> - Comentarios sobre la regla de negocio que se valida.”

---

## 3. Casos

**GV-ROUTEADD-01 – Crear ruta válida (happy path)**  
- Body con:
  - `airplane_route_id` positivo no usado.
  - `airplane_id` existente.
  - `flight_number` con formato `AA-1234`.
  - `departure` y `arrival` no vacíos.
  - Fechas con mes en español válidas y arrival > departure.
  - `Moneda` dentro de `{Colones, Dolares, Euros}`.
- Esperar 201.
- Verificar que el response incluya `flight_time` calculado y fechas formateadas.

**GV-ROUTEADD-02 – Claves JSON duplicadas**  
- Enviar JSON con claves repetidas.
- Esperar 400 con mensaje de duplicados.

**GV-ROUTEADD-03 – Body vacío o mal formado**  
- Body `None` o `{}`.
- Esperar 400.

**GV-ROUTEADD-04 – Avión no existe**  
- `airplane_id` que no esté registrado.
- Esperar 400 con error en `airplane_id`.

**GV-ROUTEADD-05 – ID de ruta duplicado**  
- Reutilizar `airplane_route_id` de una ruta ya creada.
- Esperar 400.

**GV-ROUTEADD-06 – (flight_number, airplane_id) duplicados**  
- Usar mismo `flight_number` y `airplane_id` que otra ruta existente.
- Esperar 400.

**GV-ROUTEADD-07 – Ruta totalmente idéntica a otra**  
- Repetir todos los campos de una ruta existente.
- Esperar 400 con referencia al ID ya registrado.

**GV-ROUTEADD-08 – Moneda inválida**  
- `Moneda` fuera de lista permitida.
- Esperar 400 (error de validación Marshmallow).

**GV-ROUTEADD-09 – Formato de número de vuelo inválido**  
- `flight_number` que no cumpla `^[A-Z]{2}-\d{4}$`.
- Esperar 400.

**GV-ROUTEADD-10 – arrival_time <= departure_time**  
- Fechas en orden incorrecto.
- Esperar 400 con error en `arrival_time`.
