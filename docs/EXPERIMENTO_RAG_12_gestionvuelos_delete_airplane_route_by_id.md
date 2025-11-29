# EXPERIMENTO_RAG_12 – Endpoint `/delete_airplane_route_by_id/{airplane_route_id}`

Experimento RAG para:

- `DELETE /delete_airplane_route_by_id/{airplane_route_id}`.

---

## 1. Objetivo

1. Validar que el agente:
   - Entienda la lógica de borrado de rutas.
   - Considere validaciones de ID, estructura interna y ruta inexistente.

2. Que los tests:
   - Verifiquen que la ruta desaparece de `airplanes_routes` tras el borrado.

---

## 2. Formato de petición

Para cada caso (GV-ROUTEDEL-XX):

> “Usando el endpoint `/delete_airplane_route_by_id/{airplane_route_id}` de `ENDPOINTS_GestionVuelos.md`, genera un test `pytest` para GV-ROUTEDEL-XX.”

---

## 3. Casos

**GV-ROUTEDEL-01 – Borrado exitoso de ruta existente (happy path)**  
- Crear una ruta o usar una existente.
- Borrarla.
- Esperar 200 con mensaje de éxito.
- Verificar que ya no aparezca en `/get_all_airplanes_routes`.

**GV-ROUTEDEL-02 – ID no positivo**  
- ID ≤ 0.
- Esperar 400.

**GV-ROUTEDEL-03 – Estructura interna inválida**  
- Forzar `airplanes_routes` no lista.
- Esperar 500.

**GV-ROUTEDEL-04 – Ruta no encontrada**  
- ID válido sin ruta asociada.
- Esperar 404.

**GV-ROUTEDEL-05 – Error inesperado (negativo/controlado)**  
- (Opcional) Simular excepción en la eliminación.
- Esperar 500.
