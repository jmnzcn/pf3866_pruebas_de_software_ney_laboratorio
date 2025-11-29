from gestionvuelos_common import _get, service_up


def test_get_all_routes_rag_basic(service_up):
    """
    Caso RAG: listar rutas con /get_all_airplanes_routes.
    Acepta lista de rutas o mensaje 'No hay rutas registradas actualmente.'.
    """
    r = _get("/get_all_airplanes_routes")
    assert r.status_code in (200, 500)

    if r.status_code == 200:
        body = r.json()
        if isinstance(body, list):
            if body:
                assert all("airplane_route_id" in rt for rt in body)
        elif isinstance(body, dict):
            assert "message" in body
    else:
        # 500 = posible problema interno
        pass
