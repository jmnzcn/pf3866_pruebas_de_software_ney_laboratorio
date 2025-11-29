# EXPERIMENTO_RAG_06 – Endpoint `/seats/grouped-by-airplane`

Experimento RAG sobre:

- `GET /seats/grouped-by-airplane` en `GestiónVuelos`.

---

## 1. Objetivo

1. Verificar que el agente:
   - Entienda el esquema de agrupación por `airplane_id`.
   - Use el contrato de `AirplaneSeatSchema(many=True)` por grupo.

2. Asegurar que los tests:
   - Diferencien entre “no hay asientos” (200 con mensaje) y errores de estructura (500).

---

## 2. Formato de petición

Para cada caso (GV-GROUP-XX):

> “Usando el endpoint `/seats/grouped-by-airplane` y `ENDPOINTS_GestionVuelos.md`, genera un test `pytest` para el caso GV-GROUP-XX:
> - Explicando qué se valida.
> - Qué asserts se hacen sobre el JSON agrupado (claves de avión, lista de asientos).
> - Comentando qué regla de negocio/documentación está detrás.”

---

## 3. Casos

**GV-GROUP-01 – Agrupación normal con varios aviones**  
- Dejar la seed inicial de aviones/asientos.
- Esperar 200.
- Verificar que la respuesta sea un objeto cuyas claves sean IDs de avión (como string o int, según serialización).
- Verificar que cada grupo tenga asientos válidos (`airplane_id`, `seat_number`, `status`).

**GV-GROUP-02 – Sin asientos registrados**  
- Simular sistema sin asientos.
- Esperar 200.
- Respuesta con mensaje `"No hay asientos registrados en el sistema."`.

**GV-GROUP-03 – Estructura interna de asientos inválida**  
- Forzar que `seats` no sea lista.
- Esperar 500 con mensaje de estructura inválida.

**GV-GROUP-04 – Error de validación en un grupo**  
- Manipular un grupo para que un asiento tenga `status` inválido.
- Esperar 500 con mensaje de error de datos para el avión afectado.
