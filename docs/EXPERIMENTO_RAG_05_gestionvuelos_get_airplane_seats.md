# EXPERIMENTO_RAG_05 – Endpoint `/get_airplane_seats/{airplane_id}/seats`

Experimento RAG para:

- `GET /get_airplane_seats/{airplane_id}/seats` en `GestiónVuelos`.

---

## 1. Objetivo

1. Validar comprensión de:
   - Verificación de existencia de avión.
   - Validación con `AirplaneSeatSchema(many=True)`.
   - Manejo de “avión sin asientos” vs “avión inexistente”.

2. Lograr que los tests:
   - Cubran escenarios tanto felices como de error (400, 404, 500).

---

## 2. Formato de petición

Para cada caso (GV-SEATS-XX):

> “Con base en el endpoint `/get_airplane_seats/{airplane_id}/seats` documentado en `ENDPOINTS_GestionVuelos.md`, genera un test de `pytest` para el caso GV-SEATS-XX:
> - Detallando el `airplane_id` usado.
> - Expectativas de status_code.
> - Validaciones sobre la lista de asientos y sus campos.
> - Comentarios referenciando las reglas de negocio.”

---

## 3. Casos de prueba

**GV-SEATS-01 – Listar asientos de avión existente (happy path)**  
- Elegir un `airplane_id` existente con asientos.
- Esperar 200.
- Validar que la lista no esté vacía y que cada asiento tenga `airplane_id`, `seat_number`, `status`.
- Comprobar que todos pertenecen al avión solicitado.

**GV-SEATS-02 – ID no positivo**  
- `airplane_id = 0` o negativo.
- Esperar 400.

**GV-SEATS-03 – Avión no encontrado**  
- `airplane_id` grande que no exista.
- Esperar 404.

**GV-SEATS-04 – Avión sin asientos registrados**  
- (Opcional) Crear avión sin generar asientos o manipular estructura para probar este caso.
- Esperar 404 y mensaje indicando que no hay asientos registrados para el avión.

**GV-SEATS-05 – Estructura interna inválida**  
- Simular que `airplanes` o `seats` no sean listas.
- Esperar 500.

**GV-SEATS-06 – Error de validación de Marshmallow en asientos**  
- Forzar que un asiento tenga `status` inválido.
- Esperar 500 con mensaje de error en datos de asientos.
