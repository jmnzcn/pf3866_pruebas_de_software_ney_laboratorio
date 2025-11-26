# EXPERIMENTO_RAG_00_usuario_health

## Objetivo

Validar el estado de salud del microservicio **Usuario** usando el endpoint `GET /health`,
apoyándose en el servidor MCP (`get_health`) para decidir si se deben ejecutar o no
el resto de pruebas funcionales (RAG_01 a RAG_10).

---

## Microservicio y endpoint bajo prueba

- Microservicio: **Usuario**
- Puerto por defecto: `5003`
- Endpoint: `GET /health`

### Contrato del endpoint

**Request**

- Método: `GET`
- URL: `http://localhost:5003/health`
- Headers: ninguno obligatorio
- Body: vacío

**Response – caso exitoso**

- Código: `200 OK`
- Body (JSON):

  ```json
  {
    "status": "ok",
    "service": "usuario"
  }
