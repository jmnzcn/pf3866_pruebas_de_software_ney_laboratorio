# EXPERIMENTO_RAG_07 – Endpoint `/update_seat_status/{airplane_id}/seats/{seat_number}`

Experimento RAG para:

- `PUT /update_seat_status/{airplane_id}/seats/{seat_number}`.

---

## 1. Objetivo

1. Probar que el agente:
   - Comprenda todas las validaciones sobre `seat_number` (longitud, regex, palabras prohibidas).
   - Diferencie entre cambio real de estado y “ya tenía ese estado”.

2. Asegurar que los tests:
   - Cubran combinaciones de estados: `Libre`, `Reservado`, `Pagado`.

---

## 2. Formato de petición

Para cada caso (GV-UPDSEAT-XX):

> “Basándote en `ENDPOINTS_GestionVuelos.md`, genera un test de `pytest` para el caso GV-UPDSEAT-XX sobre `/update_seat_status/{airplane_id}/seats/{seat_number}`, incluyendo:
> - setup (estado inicial del asiento).
> - request JSON.
> - asserts sobre status y mensaje.
> - comentarios sobre la regla que se valida (regex, keywords, estado inválido, etc.).”

---

## 3. Casos

**GV-UPDSEAT-01 – Cambiar de Libre a Reservado (happy path)**  
- Asiento inicialmente `Libre`.
- Body `{ "status": "Reservado" }`.
- Esperar 200 y mensaje de actualización.
- Verificar que el asiento en una lectura posterior tenga `status = "Reservado"`.

**GV-UPDSEAT-02 – Cambiar de Reservado a Pagado**  
- Similar al caso anterior, preparando un asiento en `Reservado`.
- Cambiar a `Pagado`.

**GV-UPDSEAT-03 – Asiento ya en el mismo estado**  
- Asiento en `Reservado`.
- Body con `status = "Reservado"`.
- Esperar 200 con mensaje de que ya tenía ese estado.

**GV-UPDSEAT-04 – Avión no existe**  
- `airplane_id` inexistente.
- Esperar 404.

**GV-UPDSEAT-05 – seats no es lista (estructura inválida)**  
- Forzar `seats` inválido.
- Esperar 500.

**GV-UPDSEAT-06 – seat_number demasiado largo**  
- `seat_number` con longitud > 5.
- Esperar 400.

**GV-UPDSEAT-07 – seat_number palabra reservada (ALL / *)**  
- Probar `"ALL"` y `"*"` (insensible a mayúsculas).
- Esperar 400.

**GV-UPDSEAT-08 – seat_number con formato inválido**  
- Ejemplos: `"A12"`, `"12Z"`, `"12AA"`.
- Esperar 400 (regex no cumple `^\d+[A-F]$`).

**GV-UPDSEAT-09 – Body vacío / sin status**  
- Body `{}` o `None`.
- Esperar 400.

**GV-UPDSEAT-10 – status inválido**  
- `status` distinto de `"Libre"`, `"Reservado"`, `"Pagado"`.
- Esperar 400.

**GV-UPDSEAT-11 – Asiento no encontrado**  
- `airplane_id` válido pero `seat_number` que no exista.
- Esperar 404.
