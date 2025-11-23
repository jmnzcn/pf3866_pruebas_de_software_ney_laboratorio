# EXPERIMENTO_RAG_04_usuario_create_payment

## 1. Información general

- **Módulo:** Usuario  
- **Endpoint bajo prueba:** `POST /usuario/create_payment`  
- **Microservicios involucrados:**
  - `Usuario` (orquestador de la operación)
  - `GestiónReservas` (crea el pago y valida existencia de la reserva)
  - `GestiónVuelos` (marca el asiento como `Pagado`)

---

## 2. Objetivo del experimento

Verificar, mediante pruebas de contrato externas (black box, vía HTTP), que el endpoint:

- Valida correctamente el body de entrada:
  - `reservation_id` es un entero positivo.
  - `payment_method` ∈ {`Tarjeta`, `PayPal`, `Transferencia`}.
  - `currency` ∈ {`Dolares`, `Colones`}.
- Verifica la existencia de la reserva en el microservicio `GestiónReservas`.
- Delegaa la creación del pago al microservicio `GestiónReservas`.
- Notifica a `GestiónVuelos` para marcar el asiento asociado como `Pagado` después de crear el pago.
- Maneja apropiadamente errores de validación y errores de comunicación entre microservicios.

---

## 3. Precondiciones

Antes de ejecutar el experimento se asume:

1. **Servicios levantados:**
   - Microservicio `GestiónVuelos`.
   - Microservicio `GestiónReservas`.
   - Microservicio `Usuario`, accesible en:
     - `http://localhost:5003` (por defecto).

2. **Variables de entorno configuradas:**
   - `GESTIONRESERVAS_SERVICE` (URL base de GestiónReservas).
   - `GESTIONVUELOS_SERVICE` (URL base de GestiónVuelos).

3. **Datos existentes:**
   - Existe **al menos una reserva válida** en `GestiónReservas`, con:
     - `reservation_id` > 0.
     - Campos `airplane_id` y `seat_number` consistentes.
   - El asiento asociado a esa reserva está en un estado que permita marcarlo como `Pagado` (normalmente `Reservado`).

> Nota: para el caso feliz se obtendrá un `reservation_id` real durante la prueba usando, por ejemplo, `GET /get_all_reservations` (Usuario) o directamente desde el microservicio `GestiónReservas`.

---

## 4. Casos de prueba diseñados

### 4.1 Resumen en tabla

| ID caso              | Descripción                                                       | Entrada (body) principal                                                   | Resultado esperado                                        |
|----------------------|-------------------------------------------------------------------|----------------------------------------------------------------------------|-----------------------------------------------------------|
| USR_PAY_BODY_VACIO   | Body ausente o vacío                                             | `None` o `{}`                                                              | `400` + msg incluye: `"No se recibió cuerpo JSON"`       |
| USR_PAY_ID_INVALIDO  | `reservation_id` no entero positivo                              | `reservation_id = 0`, `-1` o no entero                                    | `400` + msg incluye: `"El reservation_id debe ser un entero positivo."` |
| USR_PAY_METHOD_INV   | `payment_method` fuera de `["Tarjeta","PayPal","Transferencia"]` | `payment_method = "Bitcoin"` u otro valor inválido                        | `400` + msg incluye: `"Método de pago inválido."`        |
| USR_PAY_CURRENCY_INV | `currency` fuera de `["Dolares","Colones"]`                      | `currency = "EUR"` u otro valor inválido                                  | `400` + msg incluye: `"Moneda no soportada."`            |
| USR_PAY_RES_NO_EXIST | `reservation_id` válido pero inexistente                         | `reservation_id = 999999` (u otro ID que no exista)                       | `404` + msg incluye: `"Reserva con ID 999999 no encontrada."` (o ID usado) |
| USR_PAY_ERR_RESERVAS | GestiónReservas devuelve error al crear el pago                  | Simular respuesta ≠ `201` desde `GestiónReservas` (caso más avanzado)     | Se propaga el código de respuesta y mensaje de GestiónReservas |
| USR_PAY_OK_01        | Flujo feliz completo                                             | `reservation_id` existente, `payment_method` y `currency` válidos         | `201` + msg contiene `"Pago registrado"` y objeto `payment` |

> Nota: algunos casos de error en `GestiónReservas` pueden requerir manipulación del back o de datos para forzar ciertas respuestas; se pueden marcar como **opcionales** si no se automatizan.

---

## 5. Detalle de casos de prueba

### 5.1 Caso USR_PAY_BODY_VACIO

**Descripción:**  
Llamada al endpoint sin body JSON o con un body vacío `{}`.

**Pasos:**

1. Enviar `POST` a:

   `POST /usuario/create_payment`

   con:
   - Sin header `Content-Type: application/json` y sin body, **o**
   - `Content-Type: application/json` y body `{}`.

2. Observar respuesta HTTP.

**Resultado esperado:**

- Código de estado: `400`.
- Respuesta JSON con al menos:

  ```json
  {
    "message": "No se recibió cuerpo JSON"
  }
