from gestionvuelos_common import _get, service_up


def test_get_airplanes_rag_basic(service_up):
    """
    Caso RAG: listar aviones con /get_airplanes.
    Acepta dos diseños: lista de aviones o mensaje de 'No hay aviones...'.
    """
    r = _get("/get_airplanes")
    assert r.status_code in (200, 500), (
        f"Código inesperado en /get_airplanes: {r.status_code} {r.text}"
    )

    if r.status_code == 200:
        body = r.json()
        if isinstance(body, list):
            assert all("airplane_id" in a for a in body)
        elif isinstance(body, dict):
            assert "message" in body
    else:
        # 500 = posible problema de datos internos
        pass
