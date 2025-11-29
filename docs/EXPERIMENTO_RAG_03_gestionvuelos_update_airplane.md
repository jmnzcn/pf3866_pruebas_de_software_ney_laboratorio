# EXPERIMENTO_RAG_03 – Endpoint `/update_airplane/{airplane_id}`

Experimento RAG centrado en:

- `PUT /update_airplane/{airplane_id}` del microservicio `GestiónVuelos`.

El agente debe usar:

- `docs/ENDPOINTS_GestionVuelos.md`
- `docs/README_testing.md`
- Código de `update_airplane` en `GestionVuelos/app.py` (opcional pero recomendado)

---

## 1. Objetivo del experimento

1. Validar que el agente:
   - Entienda las validaciones de ID, campos extra/faltantes y claves JSON duplicadas.
   - Integre la validación via `AirplaneSchema` (Marshmallow) en los escenarios de prueba.
   - Distinga entre actualización real y “no-op” (datos idénticos).

2. Comprobar que los tests que genera:
   - Cubran tanto el caso exitoso como los diferentes errores 400/404/500.

---

## 2. Formato de petición a la IA

Para cada caso (GV-UPD-XX):

> “Tomando como referencia el endpoint `/update_airplane/{airplane_id}` de `ENDPOINTS_GestionVuelos.md` y las reglas de `README_testing.md`, genera un test de `pytest` para el caso GV-UPD-XX, incluyendo:
> - Descripción breve.
> - JSON de request.
> - Asserts sobre status_code y mensaje.
> - Comentarios explicando qué validación se está cubriendo (ID positivo, campos extra, Marshmallow, no-op, etc.).”

---

## 3. Lista de casos de prueba

**GV-UPD-01 – Actualización válida de avión existente (happy path)**  
- `airplane_id` válido que exista.
- Body con `model`, `manufacturer`, `year`, `capacity` todos válidos.
- Esperar 200 con mensaje de éxito.
- Verificar que, en una lectura posterior, los campos actualizados realmente cambien.

**GV-UPD-02 – ID no positivo**  
- `airplane_id = 0` o negativo.
- Body válido.
- Esperar 400 con mensaje de ID no positivo y `errors['airplane_id']`.

**GV-UPD-03 – Body vacío o mal formado**  
- `airplane_id` válido.
- Body `None` o `{}`.
- Esperar 400 con mensaje de “No se recibió cuerpo JSON.”.

**GV-UPD-04 – Campos extra en el JSON**  
- Body contiene además de los esperados (`model`, `manufacturer`, `year`, `capacity`) un campo inventado (`color`).
- Verificar 400 y que la respuesta incluya la lista de `extras`.

**GV-UPD-05 – Campos faltantes**  
- Body sin uno o varios de los campos requeridos.
- Esperar 400 y que `faltantes` liste correctamente los campos.

**GV-UPD-06 – Avión no encontrado**  
- `airplane_id` válido pero que no exista.
- Body válido.
- Esperar 404.

**GV-UPD-07 – Error de validación con Marshmallow**  
- Por ejemplo, `year` negativo o `capacity` = 0.
- Esperar 400 y usar el `errors` devuelto por el schema.

**GV-UPD-08 – No-op (datos idénticos)**  
- Enviar los mismos valores que ya tiene el avión.
- Esperar 200 con mensaje de “No se realizaron cambios porque los datos son idénticos.”
