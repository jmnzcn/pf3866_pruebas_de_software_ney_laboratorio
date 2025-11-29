# EXPERIMENTO_RAG_04 – Endpoint `/delete_airplane_by_id/{airplane_id}`

Experimento RAG para:

- `DELETE /delete_airplane_by_id/{airplane_id}` en `GestiónVuelos`.

---

## 1. Objetivo

1. Validar que el agente:
   - Reconozca el flujo de borrado de avión + asientos asociados.
   - Proponga casos de prueba que cubran la actualización de estructuras internas (`airplanes`, `airplanes_by_id`, `seats`).

2. Verificar que los tests:
   - Comprueben el conteo de asientos eliminados.
   - Consideren estados límite (sin aviones, ID inexistente).

---

## 2. Formato de petición a la IA

Para cada caso (GV-DEL-XX):

> “Usando el endpoint `/delete_airplane_by_id/{airplane_id}` descrito en `ENDPOINTS_GestionVuelos.md` y las reglas de `README_testing.md`, genera un test de `pytest` para el caso GV-DEL-XX, con:
> - Descripción del escenario.
> - Preparación previa (si es necesario crear el avión primero).
> - Asserts sobre status_code, mensaje y `asientos_eliminados`.
> - Comentarios que referencien las reglas de negocio de la documentación.”

---

## 3. Casos de prueba

**GV-DEL-01 – Borrado exitoso de avión con asientos**  
- Crear primero un avión con capacidad conocida.
- Borrarlo.
- Esperar 200.
- Verificar mensaje y que `asientos_eliminados` coincida con la capacidad.
- Confirmar que el avión ya no está en `/get_airplanes` ni en `airplanes_by_id`.

**GV-DEL-02 – ID no positivo**  
- `airplane_id = 0` o negativo.
- Esperar 400 y mensaje de ID inválido.

**GV-DEL-03 – No hay aviones en el sistema**  
- Forzar estado sin aviones (opcional/facultativo).
- Llamar al endpoint con cualquier ID.
- Esperar 404 con mensaje de que no hay aviones registrados.

**GV-DEL-04 – Avión no encontrado**  
- `airplane_id` válido pero que no exista en la lista.
- Esperar 404.

**GV-DEL-05 – Estructuras internas inválidas**  
- Simular que `airplanes` o `seats` no son lista.
- Esperar 500 con mensaje de estructura interna inválida.
