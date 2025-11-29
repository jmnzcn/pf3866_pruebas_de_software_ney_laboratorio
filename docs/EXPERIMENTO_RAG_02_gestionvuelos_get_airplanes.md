# EXPERIMENTO_RAG_02 – Endpoints `/get_airplanes` y `/get_airplane_by_id/{airplane_id}`

Experimento RAG centrado en los endpoints de lectura de aviones del microservicio `GestiónVuelos`:

- `GET /get_airplanes`
- `GET /get_airplane_by_id/{airplane_id}`

El agente MCP/RAG debe usar:

- `docs/ENDPOINTS_GestionVuelos.md`
- `docs/README_testing.md`
- (Opcional) Código de `GestionVuelos/app.py` para estos endpoints

para proponer y/o generar pruebas automatizadas con `pytest` + `requests`.

---

## 1. Objetivo del experimento

1. Validar que el agente:
   - Entienda las reglas de negocio de ambos endpoints.
   - Diferencie entre casos con datos iniciales y estados “vacíos”.
   - Genere casos que cubran tanto IDs válidos como inválidos y no existentes.

2. Evaluar cómo el RAG:
   - Usa la documentación para derivar equivalencias entre mensajes y HTTP codes.
   - Detecta errores de estructura interna (`airplanes` no lista, IDs duplicados, etc.).

---

## 2. Formato de petición a la IA

Para cada caso de prueba (GV-GET-XX) las peticiones a la IA serán del tipo:

> “Tomando como referencia los endpoints `/get_airplanes` y `/get_airplane_by_id/{airplane_id}` documentados en `ENDPOINTS_GestionVuelos.md` y las reglas de `README_testing.md`, genera un test de `pytest` que cubra el caso GV-GET-XX, incluyendo:
> - Descripción breve del caso.
> - Request (URL y parámetros, sin body).
> - Asserts sobre `status_code` y estructura del JSON de respuesta.
> - Comentarios en el código indicando qué regla de negocio se valida (por ejemplo, ID no positivo, avión no encontrado, lista vacía, etc.).”

---

## 3. Lista de casos de prueba

### Grupo A – `/get_airplanes`

**GV-GET-01 – Obtener lista inicial de aviones (happy path)**  
- Verificar que responda 200.
- Confirmar que devuelve una lista no vacía.
- Asegurar que cada elemento tenga las claves `airplane_id`, `model`, `manufacturer`, `year`, `capacity`.
- Verificar que no haya IDs duplicados.

**GV-GET-02 – Escenario sin aviones registrados**  
- Preparar entorno sin aviones (si es posible borrar todos antes del test).
- Verificar respuesta 200 con mensaje `"No hay aviones registrados actualmente."`.
- Confirmar que no devuelve lista de aviones.

**GV-GET-03 – Estructura interna inválida (negativo/controlado)**  
- Simular (si es posible) que `airplanes` no sea una lista.
- Esperar 500 y mensaje de “Estructura interna inválida.”.

---

### Grupo B – `/get_airplane_by_id/{airplane_id}`

**GV-GET-04 – Obtener avión existente (ID válido)**  
- Usar un `airplane_id` inicial conocido (por ejemplo 1).
- Esperar 200.
- Validar que los campos coincidan con lo esperado y que `airplane_id` == 1.

**GV-GET-05 – ID no positivo (error de validación)**  
- Probar con `airplane_id = 0` o `-1`.
- Esperar 400.
- Validar mensaje y estructura de `errors['airplane_id']`.

**GV-GET-06 – Avión no encontrado (ID válido pero inexistente)**  
- Usar un ID grande que no exista (ej: 9999).
- Esperar 404.
- Verificar que el mensaje incluya `"no encontrado"`.

**GV-GET-07 – Robustez ante error inesperado**  
- (Opcional) Simular fallo interno en la búsqueda.
- Verificar que se devuelva 500 con mensaje genérico de error interno.
