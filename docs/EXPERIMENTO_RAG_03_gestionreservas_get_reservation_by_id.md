# EXPERIMENTO_RAG_03_gestionreservas_get_reservation_by_id

## 1. Contexto y objetivo

Este experimento valida el contrato del endpoint de GestiónReservas:

`GET /get_reservation_by_id/<reservation_id>`

Objetivos:

- Verificar que el endpoint valida correctamente el `reservation_id` (numérico, positivo, > 0).
- Confirmar que se devuelven los códigos y mensajes adecuados para:
  - ID no numérico.
  - ID <= 0.
  - Reserva inexistente.
- Validar el caso feliz a partir de una reserva generada en memoria por el propio microservicio.
- Documentar estos comportamientos para usarlos como “ground truth” en pruebas asistidas por RAG/MCP.

---

## 2. Endpoint y contrato

### 2.1. Definición

- Método: `GET`
- Ruta: `/get_reservation_by_id/<reservation_id>`

En el código Flask la firma es:

```python
@app.route('/get_reservation_by_id/<reservation_id>', methods=['GET'])
def get_reservation_by_id(reservation_id):
    ...
