# EXPERIMENTO_RAG_09_usuario_get_payments

Pruebas de contrato para los endpoints de **consulta de pagos** expuestos por el microservicio **Usuario**, integrados con el enfoque de **RAG/MCP**.

Archivo de pruebas asociado (propuesto):  
`tests/api/test_usuario_get_payments_rag.py`


## 1. Descripción general

Este experimento valida el comportamiento del microservicio **Usuario** cuando actúa como fachada de lectura hacia **GestiónReservas** para:

- Consultar un pago específico por su **ID** (`payment_id`).
- Listar todos los pagos existentes (o indicar claramente que no hay pagos).

Los `case_id` definidos sirven tanto para:

- Automatizar pruebas de contrato con `pytest`.
- Ser indexados en un sistema **RAG/MCP** como unidades de conocimiento reutilizables, enlazando:
  - Código (`app.py`).
  - Swagger.
  - Este mismo `.md` con descripciones de escenarios.


## 2. Endpoints bajo prueba

| Endpoint                                      | Método | Descripción breve                                                                 |
|----------------------------------------------|--------|------------------------------------------------------------------------------------|
| `/get_payment_by_id/<string:payment_id>`     | GET    | Devuelve los detalles de un pago específico validando el formato de `payment_id`. |
| `/get_all_payments`                          | GET    | Lista todos los pagos o indica que no hay pagos registrados actualmente.          |


## 3. Casos de prueba propuestos

### 3.1. `GET /get_payment_by_id/<string:payment_id>`

Según `app.py`, este endpoint:

1. Valida el formato del `payment_id` con la expresión regular:  
   `^PAY\d{6}$` (ejemplo válido: `PAY123456`).
2. Si el formato es inválido → 400.
3. Llama a GestiónReservas:
   - 404 → `No se encontró ningún pago con ID: ...`
   - 200 → retorna el JSON tal cual.
   - Otros códigos → 500 con mensaje `Error consultando pago. Código: ...`.
4. Errores de red (`RequestException`) → 500 `Error de conexión con el microservicio de pagos`.
5. Errores inesperados → 500 `Error interno del servidor`.

#### 3.1.1 Casos de error

| case_id                               | Entrada (path)                               | Esperado | Tipo                    | Mensaje esperado (substring)                                     |
|---------------------------------------|----------------------------------------------|----------|-------------------------|-------------------------------------------------------------------|
| `USR_PAY_GET_ID_FORMATO_INVALIDO_400` | `/get_payment_by_id/ABC123`                  | 400      | Validación local        | `El formato del payment_id es inválido. Debe ser como PAY123456` |
| `USR_PAY_GET_ID_NO_EXISTE_404`        | `/get_payment_by_id/PAY999999`               | 404      | No encontrado           | `No se encontró ningún pago con ID: PAY999999`                   |
| `USR_PAY_GET_ID_BACKEND_ERROR_500`    | (ID que fuerce código != 200/404 en backend) | 500      | Error backend           | `Error consultando pago. Código:`                                |
| `USR_PAY_GET_ID_CONN_ERROR_500`       | (caída de GestiónReservas)                   | 500      | Error de conexión       | `Error de conexión con el microservicio de pagos`                |

Notas:

- En la práctica, `USR_PAY_GET_ID_BACKEND_ERROR_500` y `USR_PAY_GET_ID_CONN_ERROR_500` pueden ser más útiles como **escenarios conceptuales** para RAG (explicar comportamiento en caso de fallos de infraestructura) que como pruebas automatizadas directas, salvo que se simule el backend.

#### 3.1.2 Caso feliz

| case_id                        | Estrategia                                                                                                                          | Esperado |
|--------------------------------|-------------------------------------------------------------------------------------------------------------------------------------|----------|
| `USR_PAY_GET_ID_OK_200`       | 1) Obtener un pago existente (por ejemplo, desde `/get_all_payments`).<br>2) Tomar su `payment_id`.<br>3) Llamar a `/get_payment_by_id/<payment_id>`. | 200      |

Validaciones mínimas:

- `status_code == 200`.
- Respuesta es un `dict`.
- El `payment_id` devuelto coincide con el solicitado.
- Existen campos clave: `reservation_id`, `amount`, `currency`, `payment_method`, `status`, `payment_date`, `transaction_reference` (según `PaymentSchema`).


### 3.2. `GET /get_all_payments`

Este endpoint llama internamente a:

```python
gestion_reservas_url = os.getenv("GESTIONRESERVAS_SERVICE")
url = f"{gestion_reservas_url}/get_all_fake_payments"
response = requests.get(url, timeout=20)
