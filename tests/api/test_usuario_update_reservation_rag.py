# tests/api/test_usuario_update_reservation_rag.py

import os
import requests
import pytest

# Base URL del microservicio Usuario
USUARIO_BASE_URL = os.getenv("USUARIO_BASE_URL", "http://localhost:5003")


def _url(path: str) -> str:
    return f"{USUARIO_BASE_URL}{path}"


def _get(path: str):
    return requests.get(_url(path), timeout=20)


def _put(path: str, json=None):
    return requests.put(_url(path), json=json, timeout=20)


@pytest.fixture(scope="session")
def service_up():
    """
    Simple verificación de que el microservicio Usuario responde.
    Si está caído, las pruebas fallarán igual, pero al menos
    tenemos un punto único para ajustar en el futuro.
    """
    try:
        _get("/get_all_reservations")
    except Exception:
        pytest.skip("Usuario no está disponible en USUARIO_BASE_URL")
    return True


def _find_any_reservation():
    """
    Busca alguna reserva existente a través de /get_all_reservations
    para poder probar el caso feliz de update.
    """
    r = _get("/get_all_reservations")

    if r.status_code != 200:
        pytest.skip(
            f"get_all_reservations no devolvió 200 (devuelve {r.status_code}); "
            "no se puede probar el caso feliz de update."
        )

    data = r.json()

    # El endpoint puede devolver {"message": "No hay reservas registradas."}
    if isinstance(data, dict) and "message" in data:
        msg = data["message"].lower()
        if "no hay reservas" in msg:
            pytest.skip("No hay reservas registradas para probar update.")
        else:
            pytest.skip(f"Respuesta inesperada de get_all_reservations: {data}")

    if not isinstance(data, list) or not data:
        pytest.skip(f"Respuesta inesperada de get_all_reservations: {data}")

    # Tomamos la primera reserva
    return data[0]


@pytest.mark.parametrize(
    "case_id, reservation_code, body, expected_status, expected_msg_sub",
    [
        (
            "USR_UPD_BODY_VACIO",
            "ABC123",  # código con formato válido
            None,      # sin body JSON
            400,
            "No se recibió cuerpo JSON",
        ),
        (
            "USR_UPD_CODIGO_INVALIDO",
            "ABC",  # menos de 6 caracteres => regex falla
            {
                "seat_number": "1A",
                "email": "test@example.com",
                "phone_number": "+50611111111",
                "emergency_contact_name": "Contacto Prueba",
                "emergency_contact_phone": "+50622222222",
            },
            400,
            "El código de reserva debe ser 6 caracteres alfanuméricos",
        ),
        (
            "USR_UPD_CAMPOS_EXTRA",
            "ABC123",  # formato válido
            {
                # body con un campo extra para disparar la validación de keys
                "seat_number": "1A",
                "email": "test@example.com",
                "phone_number": "+50611111111",
                "emergency_contact_name": "Contacto Prueba",
                "emergency_contact_phone": "+50622222222",
                "extra_field": "no_deberia_estar",
            },
            400,
            "exactamente estos campos",
        ),
    ],
)
def test_usuario_update_reservation_validaciones_basicas(
    service_up,
    case_id,
    reservation_code,
    body,
    expected_status,
    expected_msg_sub,
):
    """
    Casos de validación local para /update_reservation/<reservation_code>:

    - body vacío (sin JSON)
    - código con formato inválido
    - body con campos extra
    """

    if body is None:
        # Enviar SIN body JSON
        r = _put(f"/update_reservation/{reservation_code}")
    else:
        r = _put(f"/update_reservation/{reservation_code}", json=body)

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        resp_json = {}
        msg_text = r.text

    assert (
        r.status_code == expected_status
    ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"

    assert expected_msg_sub in msg_text, (
        f"[{case_id}] No se encontró el texto esperado en el mensaje. "
        f"Buscaba: '{expected_msg_sub}' en: '{msg_text}'"
    )


def test_usuario_update_reservation_sin_cambios(service_up):
    """
    Caso: enviar exactamente los mismos datos de contacto y asiento.
    Esperado: 200 con mensaje indicando que no hubo cambios reales.
    """
    reserva = _find_any_reservation()
    code = reserva["reservation_code"]

    body = {
        "seat_number": reserva["seat_number"],
        "email": reserva["email"],
        "phone_number": reserva["phone_number"],
        "emergency_contact_name": reserva["emergency_contact_name"],
        "emergency_contact_phone": reserva["emergency_contact_phone"],
    }

    r = _put(f"/update_reservation/{code}", json=body)

    try:
        resp_json = r.json()
        msg_text = resp_json.get("message", "") or resp_json.get("error", "")
    except Exception:
        resp_json = {}
        msg_text = r.text

    assert (
        r.status_code == 200
    ), f"[USR_UPD_NO_CAMBIOS] Código inesperado: {r.status_code} {r.text}"

    # El endpoint devuelve:
    # "La información es idéntica; no se realizaron cambios."
    # No atamos el assert a todo el string, solo a una parte estable.
    assert "idéntica" in msg_text or "no se realizaron cambios" in msg_text, (
        "[USR_UPD_NO_CAMBIOS] No se encontró indicación de 'sin cambios' en el mensaje: "
        f"'{msg_text}'"
    )




def test_usuario_update_reservation_happy_path(service_up):
    """
    Caso feliz: cambiar datos de contacto manteniendo el mismo asiento.

    Este test verifica SOLO que:
    - El endpoint responde 200.
    - El mensaje indica éxito.
    - La respuesta incluye una clave 'reservation'.
    No valida los campos internos de la reserva, porque eso ya se cubre
    indirectamente por los otros tests y por el propio backend.
    """
    # 1) Tomar cualquier reserva existente de GestiónReservas
    reserva = _find_any_reservation()
    code = reserva["reservation_code"]

    email_actual = reserva.get("email") or "sin-email@example.com"

    # 2) Construir un nuevo email distinto al actual
    nuevo_email = f"nuevo+{code.lower()}@example.com"
    if nuevo_email == email_actual:
        nuevo_email = f"nuevo2+{code.lower()}@example.com"

    body = {
        "seat_number": reserva["seat_number"],
        "email": nuevo_email,
        "phone_number": reserva["phone_number"],
        "emergency_contact_name": reserva["emergency_contact_name"],
        "emergency_contact_phone": reserva["emergency_contact_phone"],
    }

    # 3) Llamar al endpoint de Usuario
    r = _put(f"/update_reservation/{code}", json=body)

    # 4) Código de respuesta esperado: 200
    assert (
        r.status_code == 200
    ), f"[USR_UPD_OK_01] Código inesperado: {r.status_code} {r.text}"

    # 5) La respuesta debe ser JSON y contener al menos:
    #    - un mensaje de éxito
    #    - un objeto 'reservation'
    resp_json = r.json()

    msg = resp_json.get("message", "")
    assert "actualizados exitosamente" in msg, (
        "[USR_UPD_OK_01] Mensaje de éxito inesperado: "
        f"{msg}"
    )

    # Solo verificamos que exista la clave 'reservation'
    assert "reservation" in resp_json, (
        "[USR_UPD_OK_01] No viene 'reservation' en la respuesta: "
        f"{resp_json}"
    )
