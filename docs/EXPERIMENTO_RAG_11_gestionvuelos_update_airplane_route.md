# EXPERIMENTO_RAG_11 – Endpoint `/update_airplane_route_by_id/{airplane_route_id}`

Experimento RAG para:

- `PUT /update_airplane_route_by_id/{airplane_route_id}`.

---

## 1. Objetivo

1. Validar que el agente:
   - Tome en cuenta la validación del ID de la ruta y la estructura de `airplanes_routes`.
   - Comprenda que no se permite cambiar `airplane_route_id` en el body.
   - Valide fechas y recálculo de `flight_time`.

2. Los tests deben:
   - Cubrir “no-op” vs actualización real.
   - Verificar re-computación consistente de `flight_time`.

---

## 2. Formato de petición

Para cada caso (GV-ROUTEUPD-XX):

> “Siguiendo `ENDPOINTS_GestionVuelos.md` para `/update_airplane_route_by_id/{airplane_route_id}`, genera un test de `pytest` para GV-ROUTEUPD-XX.”

---

## 3. Casos

**GV-ROUTEUPD-01 – Actualizar ruta con datos válidos (happy path)**  
- Ruta existente.
- Body con valores distintos (fechas, precio, moneda, etc.) válidos.
- Esperar 200, con mensaje de éxito y `route` actualizada.
- Validar que `flight_time` sea consistente con las nuevas fechas.

**GV-ROUTEUPD-02 – ID no positivo**  
- `airplane_route_id <= 0`.
- Esperar 400.

**GV-ROUTEUPD-03 – `airplane_route_id` no existe**  
- ID válido pero sin ruta asociada.
- Esperar 404.

**GV-ROUTEUPD-04 – Claves JSON duplicadas**  
- Body con claves repetidas.
- Esperar 400 y mensaje de duplicados.

**GV-ROUTEUPD-05 – Body vacío o mal formado**  
- Body `{}` o `None`.
- Esperar 400.

**GV-ROUTEUPD-06 – Intento de cambiar airplane_route_id en body**  
- Incluir `airplane_route_id` distinto al de la URL.
- Esperar 400 con mensaje de que no se permite cambiar el ID.

**GV-ROUTEUPD-07 – Errores de validación (schema)**  
- Por ejemplo, moneda inválida, flight_number mal formado, campos faltantes.
- Esperar 400 con `errors` del schema.

**GV-ROUTEUPD-08 – arrival_time <= departure_time**  
- Fechas en orden incorrecto.
- Esperar 400.

**GV-ROUTEUPD-09 – No-op (datos idénticos)**  
- Enviar body que, tras normalización de fechas y cálculo, sea idéntico a la ruta existente.
- Esperar 200 con mensaje de “No se realizaron cambios porque los datos son idénticos.”
