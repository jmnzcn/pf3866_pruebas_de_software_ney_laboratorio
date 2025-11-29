# EXPERIMENTO_RAG_08 – Endpoints `/get_random_free_seat/{airplane_id}` y `/free_seat/{airplane_id}/seats/{seat_number}`

Experimento RAG combinado para:

- `GET /get_random_free_seat/{airplane_id}`
- `PUT /free_seat/{airplane_id}/seats/{seat_number}`

---

## 1. Objetivo

1. Validar que el agente:
   - Entienda cómo se busca un asiento libre para un avión dado.
   - Comprenda el flujo de liberar un asiento (cambiar a `Libre`).

2. Comprobar que los tests:
   - Conecten ambos endpoints en un escenario de extremo a extremo (reservar → liberar → random free seat).

---

## 2. Formato de petición

Para cada caso (GV-RANDOM-XX):

> “Usa los endpoints `/get_random_free_seat/{airplane_id}` y `/free_seat/{airplane_id}/seats/{seat_number}`, según `ENDPOINTS_GestionVuelos.md`, y genera un test de `pytest` para el caso GV-RANDOM-XX.”

---

## 3. Casos

**GV-RANDOM-01 – Obtener asiento libre existente (happy path)**  
- Asegurar que el avión tenga asientos `Libre`.
- Llamar a `/get_random_free_seat/{airplane_id}`.
- Esperar 200 y validar que `status == "Libre"` y `airplane_id` coincida.

**GV-RANDOM-02 – Sin asientos libres**  
- Preparar todos los asientos de un avión como `Reservado` o `Pagado`.
- Llamar a `/get_random_free_seat/{airplane_id}`.
- Esperar 404 con mensaje `"No hay asientos libres"`.

**GV-RANDOM-03 – Liberar asiento ocupado**  
- Tomar un asiento no libre.
- Llamar a `/free_seat/{airplane_id}/seats/{seat_number}`.
- Esperar 200 y que el asiento quede en estado `Libre`.

**GV-RANDOM-04 – Liberar asiento ya libre**  
- Asiento en `Libre`.
- Llamar al endpoint de liberación.
- Esperar 200 con mensaje de que ya estaba libre.

**GV-RANDOM-05 – Avión no encontrado al liberar**  
- `airplane_id` inexistente.
- Esperar 404.

**GV-RANDOM-06 – Asiento no encontrado al liberar**  
- `airplane_id` válido pero `seat_number` inexistente.
- Esperar 404.

**GV-RANDOM-07 – Estructuras inválidas en `free_seat`**  
- Forzar `seats` o `airplanes` no lista.
- Esperar 500.
