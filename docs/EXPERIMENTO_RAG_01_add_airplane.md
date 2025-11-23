# EXPERIMENTO_RAG_01 – Endpoint `/add_airplane`

Primer experimento RAG centrado exclusivamente en el endpoint:

- `POST /add_airplane` del microservicio `GestiónVuelos`.

La idea es que el agente MCP/RAG lea:
- `docs/ENDPOINTS_GestionVuelos.md`
- `docs/README_testing.md`
- (Opcional) Código de `add_airplane` en `GestionVuelos`

y, a partir de eso, genere o revise pruebas automatizadas para los casos siguientes.

---

## 1. Objetivo del experimento

1. Ver si el agente MCP/RAG:
   - Entiende las reglas de negocio de `/add_airplane`.
   - Propone casos de prueba coherentes con la documentación y el código.
   - Genera tests `pytest` que llamen al servicio real con `requests`.

2. Evaluar cómo el RAG:
   - Usa la documentación para justificar cada caso.
   - Detecta posibles faltantes de cobertura.

---

## 2. Formato de petición a la IA

Para cada caso de prueba (ADD-XX) haremos peticiones del tipo:

> “Tomando como referencia el endpoint `/add_airplane` descrito en `ENDPOINTS_GestionVuelos.md` y las reglas de `README_testing.md`, genera un test de `pytest` que cubra el caso ADD-XX, incluyendo:
> - Descripción breve del caso.
> - Request JSON usado.
> - Asserts sobre `status_code` y campos clave del JSON de respuesta.
> - Comentarios en el código que indiquen qué regla de negocio se está validando.”

---

## 3. Lista de casos de prueba para `/add_airplane`

### Grupo A – Casos felices (creación válida)

#### ADD-01 – Crear avión válido (happy path básico)
- Tipo: `happy path`
- Descripción: Crear un avión nuevo con todos los campos válidos y un `airplane_id` que no exista aún.
- Request ejemplo:
  ```json
  {
    "airplane_id": 850,
    "model": "B737-TEST01",
    "manufacturer": "Boeing",
    "year": 2020,
    "capacity": 15
  }
