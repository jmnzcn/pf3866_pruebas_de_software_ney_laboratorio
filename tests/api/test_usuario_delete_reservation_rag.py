"""
EXPERIMENTO_RAG_03_usuario_delete_reservation

Pruebas de contrato para el endpoint:
    DELETE /usuario/delete_reservation_by_id/<int:reservation_id>

Casos cubiertos:
- ID inválido (<= 0) -> 400.
- Reserva inexistente -> 404.
- Caso feliz: eliminación exitosa -> 200 y luego 404 al intentar eliminarla de nuevo.
"""

import os
import requests
import pytest

# Reutilizamos la función para encontrar una reserva existente desde el experimento de update
from tests.api.test_usuario_update_reservation_rag import _find_any_reservation

# Base URL del microservicio Usuario
BASE_URL = os.getenv("USUARIO_BASE_URL", "http://localhost:5003")


def _delete(path: str, **kwargs) -> requests.Response:
    """
    Helper para enviar DELETE al microservicio Usuario.
    """
    url = f"{BASE_URL}{path}"
    return requests.delete(url, **kwargs)


@pytest.mark.parametrize(
    "case_id, reservation_id, expected_status, expected_msg_sub",
    [
        (
            "USR_DEL_ID_INVALIDO",
            0,   # ID no positivo -> debe devolver 400
            400,
            "número positivo",
        ),
        (
            "USR_DEL_NO_EXISTE",
            999999,  # ID que muy probablemente no exista
            404,
            "no encontrada",  # parte del mensaje esperado
        ),
    ],
)
def test_usuario_delete_reservation_validaciones_y_404(
    case_id,
    reservation_id,
    expected_status,
    expected_msg_sub,
):
    """
    Casos de error para /usuario/delete_reservation_by_id/<reservation_id>:

    - ID no positivo -> 400.
    - Reserva inexistente -> 404.
    """
    r = _delete(f"/usuario/delete_reservation_by_id/{reservation_id}")

    # Intentar parsear el body como JSON, pero no romper si no lo es.
    try:
        body = r.json()
        msg_text = body.get("message", "") or body.get("error", "")
    except Exception:
        body = {}
        msg_text = r.text

    assert (
        r.status_code == expected_status
    ), f"[{case_id}] Código inesperado: {r.status_code} {r.text}"

    # Mensaje esperado (solo substring, no exacto)
    assert expected_msg_sub.lower() in msg_text.lower(), (
        f"[{case_id}] No se encontró el texto esperado en el mensaje. "
        f"Buscaba: '{expected_msg_sub}' en: '{msg_text}'"
    )


def test_usuario_delete_reservation_happy_path():
    """
    Caso feliz: eliminar una reserva existente por ID.

    Pasos:
    1) Obtener una reserva existente desde Usuario/GestiónReservas.
    2) Llamar a DELETE /usuario/delete_reservation_by_id/<reservation_id>:
       - Esperado 200, mensaje de éxito y 'deleted_reservation' en la respuesta.
    3) Volver a llamar con el mismo ID:
       - Esperado 404, reserva ya no existe.
    """
    # 1) Tomar cualquier reserva existente (reutilizamos helper del experimento de update)
    reserva = _find_any_reservation()
    reservation_id = reserva["reservation_id"]

    # 2) Primera eliminación: debería ser exitosa (200)
    r1 = _delete(f"/usuario/delete_reservation_by_id/{reservation_id}")

    assert (
        r1.status_code == 200
    ), f"[USR_DEL_OK_01] Código inesperado en primer DELETE: {r1.status_code} {r1.text}"

    # Parsear respuesta
    try:
        body1 = r1.json()
    except Exception:
        body1 = {}
    msg1 = body1.get("message", "") or body1.get("error", "")
    deleted_reservation = body1.get("deleted_reservation")

    # Validaciones mínimas del caso feliz
    msg1_lower = msg1.lower()
    # Aceptamos cualquier mensaje que indique eliminación
    assert (
        "eliminad" in msg1_lower  # "eliminada"/"eliminado"
        or "borrad" in msg1_lower  # "borrada"/"borrado"
    ), (
        "[USR_DEL_OK_01] Mensaje de éxito inesperado en primer DELETE: "
        f"{msg1}"
    )

    assert isinstance(deleted_reservation, dict), (
        "[USR_DEL_OK_01] La respuesta no contiene 'deleted_reservation' como objeto: "
        f"{body1}"
    )
    # Coherencia básica: el ID eliminado debe coincidir
    assert deleted_reservation.get("reservation_id") == reservation_id, (
        "[USR_DEL_OK_01] El reservation_id de 'deleted_reservation' no coincide "
        f"con el esperado. Obtenido: {deleted_reservation.get('reservation_id')}, "
        f"esperado: {reservation_id}"
    )

    # 3) Segunda eliminación: ahora la reserva ya no debería existir (404)
    r2 = _delete(f"/usuario/delete_reservation_by_id/{reservation_id}")

    assert (
        r2.status_code == 404
    ), f"[USR_DEL_OK_01] Código inesperado en segundo DELETE: {r2.status_code} {r2.text}"

    try:
        body2 = r2.json()
        msg2 = body2.get("message", "") or body2.get("error", "")
    except Exception:
        body2 = {}
        msg2 = r2.text

    msg2_lower = msg2.lower()
    assert (
        "no se encontró" in msg2_lower
        or "no se encontro" in msg2_lower
        or "no encontrada" in msg2_lower
    ), (
        "[USR_DEL_OK_01] Mensaje de 'no encontrada' inesperado en segundo DELETE: "
        f"{msg2}"
    )
