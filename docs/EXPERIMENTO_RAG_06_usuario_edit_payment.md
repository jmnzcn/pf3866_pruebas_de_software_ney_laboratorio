# EXPERIMENTO_RAG_06_usuario_edit_payment

## 1. Objetivo del experimento

Diseñar y ejecutar pruebas de contrato (API-level) para el endpoint:

`PUT /usuario/edit_payment/<payment_id>`

expuesto por el microservicio **Usuario**, que delega la actualización de un pago al microservicio **GestiónReservas**.

Se busca validar:

- Validaciones locales en Usuario:
  - Formato del `payment_id`.
  - Presencia de body JSON.
  - Campos permitidos en el body.
- Manejo de errores desde GestiónReservas (pago inexistente).
- Caso feliz donde un pago existente se actualiza correctamente.

---

## 2. Endpoint bajo prueba

- **Método:** `PUT`
- **Ruta:** `/usuario/edit_payment/<payment_id>`
- **Path param:**
  - `payment_id` (string), formato esperado: `PAY123456`
- **Body JSON permitido (cualquier subconjunto no vacío):**
  - `payment_method` (string) – opcional
  - `payment_date` (string) – opcional
  - `transaction_reference` (string) – opcional

Validaciones locales:

1. `payment_id` debe cumplir regex: `^PAY\d{6}$`  
   - Si no cumple → `400`  
     Mensaje: `"El formato del payment_id es inválido. Debe ser PAY123456"`

2. Body:
   - Si no se recibe JSON o viene vacío → `400`  
     Mensaje: `"No se recibió cuerpo JSON"`

3. Campos permitidos:
   - Si el body incluye claves fuera del conjunto  
     `{payment_method, payment_date, transaction_reference}` → `400`  
     Mensaje:  
     `"Solo se pueden actualizar: payment_method, payment_date, transaction_reference"`

4. Delegación a GestiónReservas:
   - Usuario hace `PUT` a:  
     `/edit_payment/<payment_id>` en GestiónReservas, reenviando el mismo JSON.
   - Usuario devuelve al cliente:
     - el body JSON que responda GestiónReservas
     - y el mismo status HTTP.

---

## 3. Casos de prueba

### 3.1. Casos de error (400 – validaciones locales)

#### Caso 1 – Body vacío o ausente

- **ID caso:** `USR_EDIT_PAY_BODY_VACIO`
- **Precondición:** `payment_id` con formato válido, por ejemplo `PAY123456`
- **Request:**
  - `PUT /usuario/edit_payment/PAY123456`
  - Sin body JSON (no enviar `json=...`).
- **Esperado:**
  - `HTTP 400`
  - Body JSON:
    - `message` contiene `"No se recibió cuerpo JSON"`.

---

#### Caso 2 – payment_id con formato inválido

- **ID caso:** `USR_EDIT_PAY_ID_INVALIDO`
- **Precondición:** N/A.
- **Request:**
  - `PUT /usuario/edit_payment/ABC123`
  - Body JSON válido, por ejemplo:
    ```json
    {
      "payment_method": "Tarjeta"
    }
    ```
- **Esperado:**
  - `HTTP 400`
  - Body JSON:
    - `message` contiene  
      `"El formato del payment_id es inválido. Debe ser PAY123456"`.

---

#### Caso 3 – Body con campos extra no permitidos

- **ID caso:** `USR_EDIT_PAY_BODY_CAMPOS_EXTRA`
- **Precondición:** `payment_id` con formato válido, por ejemplo `PAY123456`
- **Request:**
  - `PUT /usuario/edit_payment/PAY123456`
  - Body JSON:
    ```json
    {
      "payment_method": "Tarjeta",
      "amount": 100.0
    }
    ```
    donde `amount` no es un campo permitido.
- **Esperado:**
  - `HTTP 400`
  - Body JSON:
    - `message` contiene  
      `"Solo se pueden actualizar: payment_method, payment_date, transaction_reference"`.

---

### 3.2. Caso de error (404 – pago inexistente)

> Nota: este caso depende de la implementación de GestiónReservas, pero se incluye como contrato deseado.

#### Caso 4 – payment_id no existente en GestiónReservas

- **ID caso:** `USR_EDIT_PAY_NO_EXISTE`
- **Precondición:**
  - Utilizar un ID con formato válido pero que probablemente no exista, por ejemplo `PAY999999`.
- **Request:**
  - `PUT /usuario/edit_payment/PAY999999`
  - Body JSON:
    ```json
    {
      "payment_method": "Tarjeta"
    }
    ```
- **Esperado (deseable como contrato):**
  - `HTTP 404`
  - Body JSON:
    - `message` indica que el pago no fue encontrado (`"Pago no encontrado"` o similar).

En las pruebas se validará principalmente el **status 404** y, si es posible, la presencia de un mensaje que contenga algo como `"no se encontró"` / `"no encontrado"`.

---

### 3.3. Caso feliz (200 – edición exitosa)

#### Caso 5 – Actualización exitosa de un pago existente

- **ID caso:** `USR_EDIT_PAY_OK_01`
- **Precondiciones:**
  - Debe existir al menos un pago en el sistema, recuperable desde:
    - `GET /get_all_payments`
  - De ahí se obtendrá un `payment_id` válido, con formato `PAYxxxxxx`.
- **Request (flujo):**
  1. `GET /get_all_payments`
     - Debe devolver `200` y una lista de pagos.
     - Se selecciona el primer pago que tenga `payment_id` no vacío.
  2. Construir un body de actualización, por ejemplo:
     ```json
     {
       "transaction_reference": "REF-ACTUALIZADA-<payment_id>"
     }
     ```
     asegurando que la referencia sea distinta a la actual (si se conoce).
  3. Hacer:
     - `PUT /usuario/edit_payment/<payment_id>`
     - con el body anterior.
- **Esperado:**
  - `HTTP 200`
  - Body JSON:
    - Debe ser un objeto (`dict`).
    - Debe contener al menos algún campo de confirmación, típicamente:
      - `message` con texto indicando éxito (por ejemplo `"Pago actualizado correctamente"`).
      - Opcionalmente, algún objeto `payment` o similar con los datos actualizados.
- **Verificaciones mínimas en el test:**
  - `status_code == 200`
  - `resp_json` es dict.
  - `resp_json.get("message", "")` no es cadena vacía.

---

## 4. Helpers reutilizables en los tests

Para mantener consistencia con los experimentos anteriores:

- Se reutilizará el `BASE_URL` y helpers `_get`/_`post` definidos en otros tests (por ejemplo `test_usuario_create_payment_rag.py`), que apuntan al microservicio Usuario:

  ```python
  BASE_URL = os.getenv("USUARIO_BASE_URL", "http://localhost:5003")
