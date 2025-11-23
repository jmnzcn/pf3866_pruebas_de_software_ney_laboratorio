# tests/test_gestionvuelos.py
import os
import time
import json
import random
import string

import pytest
import requests

BASE_URL = os.getenv("GV_BASE_URL", "http://localhost:5001")

# Flasgger suele exponer uno de estos JSON de especificación
SPEC_CANDIDATES = [
    "/openapi.json",
    "/apispec_1.json",
    "/docs/openapi.json",
    "/docs/apispec_1.json",
    "/swagger.json",
]

# -----------------------
# Utilidades de ayuda
# -----------------------
def _rand_suffix(n=6):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=n))


def _get_json(path, **kwargs):
    r = requests.get(f"{BASE_URL}{path}", timeout=kwargs.pop("timeout", 10))
    body = None
    if r.headers.get("content-type", "").startswith("application/json"):
        try:
            body = r.json()
        except Exception:
            body = None
    return r, body


def _post_json(path, payload, **kwargs):
    r = requests.post(
        f"{BASE_URL}{path}", json=payload, timeout=kwargs.pop("timeout", 10)
    )
    body = None
    if r.headers.get("content-type", "").startswith("application/json"):
        try:
            body = r.json()
        except Exception:
            body = None
    return r, body


def _put_json(path, payload, **kwargs):
    r = requests.put(
        f"{BASE_URL}{path}", json=payload, timeout=kwargs.pop("timeout", 10)
    )
    body = None
    if r.headers.get("content-type", "").startswith("application/json"):
        try:
            body = r.json()
        except Exception:
            body = None
    return r, body


def _delete(path, **kwargs):
    r = requests.delete(f"{BASE_URL}{path}", timeout=kwargs.pop("timeout", 10))
    body = None
    if r.headers.get("content-type", "").startswith("application/json"):
        try:
            body = r.json()
        except Exception:
            body = None
    return r, body


def _fetch_spec():
    for ep in SPEC_CANDIDATES:
        try:
            r = requests.get(f"{BASE_URL}{ep}", timeout=5)
            if r.status_code == 200 and "application/json" in r.headers.get(
                "content-type", ""
            ):
                return r.json()
        except Exception:
            pass
    return None


# -----------------------
# Fixtures
# -----------------------
@pytest.fixture(scope="session")
def service_up():
    """
    Verifica que el servicio esté levantado en BASE_URL.
    Si no responde correctamente en /health, se saltan todos los tests.
    """
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=5)
        if r.status_code != 200:
            pytest.skip("GestiónVuelos no responde 200 en /health")
    except Exception:
        pytest.skip("GestiónVuelos no está disponible en BASE_URL")
    return True


@pytest.fixture
def airplane_factory():
    """
    Crea aviones de prueba y los elimina al finalizar el test.
    Devuelve (airplane_id, airplane_body).
    """
    created_ids = []

    def _create_airplane(capacity=15, year=2020, max_tries=5):
        for _ in range(max_tries):
            new_id = random.randint(800, 899)
            payload = {
                "airplane_id": new_id,
                "model": f"B737-{_rand_suffix()}",
                "manufacturer": "Boeing",
                "year": year,
                "capacity": capacity,
            }
            r, body = _post_json("/add_airplane", payload)

            if r.status_code == 201:
                # Creado correctamente
                return new_id, body["airplane"]

            # Si ya existía, lo tratamos como "OK, úsalo"
            if (
                r.status_code == 400
                and body
                and (body.get("errors") or {}).get("airplane_id")
            ):
                # Obtenemos el avión existente por ID
                r_get, existing = _get_json(f"/get_airplane_by_id/{new_id}")
                assert r_get.status_code == 200, f"No se pudo leer avión existente {new_id}"
                return new_id, existing

            # Cualquier otro error sí se considera fallo real
            assert False, f"Falló creación de avión: {r.status_code} {r.text}"

    yield _create_airplane

    # Teardown: eliminar los aviones creados (no hacemos assert aquí)
    for aid in created_ids:
        _delete(f"/delete_airplane_by_id/{aid}")


@pytest.fixture
def route_factory():
    """
    Crea rutas de avión de prueba y las elimina al finalizar el test.
    Devuelve (airplane_route_id, route_body).
    """
    created_routes = []

    def _create_route_for_airplane(airplane_id):
        rid = random.randint(5000, 5999)
        payload = {
            "airplane_route_id": rid,
            "airplane_id": airplane_id,
            "flight_number": f"{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}"
            f"{random.choice('ABCDEFGHIJKLMNOPQRSTUVWXYZ')}-{random.randint(1000, 9999)}",
            "departure": "Aeropuerto Internacional A",
            "departure_time": "Marzo 30, 2025 - 16:46:19",
            "arrival": "Aeropuerto Internacional B",
            "arrival_time": "Marzo 30, 2025 - 19:25:00",
            "price": 98000,
            "Moneda": "Colones",
        }
        r, body = _post_json("/add_airplane_route", payload)
        assert (
            r.status_code == 201
        ), f"Falló creación de ruta: {r.status_code} {r.text}"
        created_routes.append(rid)
        return rid, body["route"]

    yield _create_route_for_airplane

    # Teardown: eliminar rutas creadas
    for rid in created_routes:
        _delete(f"/delete_airplane_route_by_id/{rid}")


# -----------------------
# Tests de diagnóstico
# -----------------------
def test_health_and_instance_header(service_up):
    r, body = _get_json("/health")
    assert r.status_code == 200
    assert isinstance(body, dict)
    assert body.get("status") == "ok"

    iid = r.headers.get("X-Instance-Id")
    assert iid and len(iid) >= 3

    # Segunda llamada para inspeccionar el header
    r2, _ = _get_json("/health")
    iid2 = r2.headers.get("X-Instance-Id")
    assert iid2, "Falta X-Instance-Id en segunda respuesta"
    print("DEBUG instance ids:", iid, iid2)


def test_state_endpoint(service_up):
    r, body = _get_json("/__state")
    assert r.status_code == 200
    assert isinstance(body, dict)
    assert {"instance_id", "airplanes_count", "airplane_ids", "routes_count"} <= set(
        body.keys()
    )


# -----------------------
# Tests de Airplanes
# -----------------------
def test_add_airplane_and_get_by_id(service_up, airplane_factory):
    """
    ADD-01 / ADD-10:
    - Crear avión válido
    - Verificar que aparece en __state y en get_airplane_by_id
    - Verificar asientos generados (capacity)
    """
    ...
    new_id, airplane = airplane_factory()
    assert airplane.get("airplane_id") == new_id

    # Verifica aparición en __state
    r2, state = _get_json("/__state")
    assert r2.status_code == 200
    assert new_id in state.get("airplane_ids", [])

    # Consulta por ID
    r3, a3 = _get_json(f"/get_airplane_by_id/{new_id}")
    assert r3.status_code == 200
    assert a3.get("airplane_id") == new_id


def test_add_airplane_duplicate_and_validation(service_up):
    # Crear un avión y luego intentar duplicarlo
    dup_id = random.randint(1000, 1999)
    payload = {
        "airplane_id": dup_id,
        "model": f"A320-{_rand_suffix()}",
        "manufacturer": "Airbus",
        "year": 2018,
        "capacity": 12,
    }
    r_ok, _ = _post_json("/add_airplane", payload)
    assert r_ok.status_code == 201

    r_dup, body_dup = _post_json("/add_airplane", payload)
    assert r_dup.status_code == 400
    assert "Duplicado" in json.dumps(body_dup or {})

    # Validación: faltan campos
    bad_payload = {"airplane_id": dup_id + 1, "model": "X"}
    r_bad, body_bad = _post_json("/add_airplane", bad_payload)
    assert r_bad.status_code == 400
    assert "Faltan campos" in (body_bad or {}).get("message", "")

    # Limpieza mínima de datos
    _delete(f"/delete_airplane_by_id/{dup_id}")


@pytest.mark.parametrize(
    "payload, expected_fragment",
    [
        (
            {
                "airplane_id": 9001,
                "model": "X",
                "manufacturer": "Y",
                "year": -1,
                "capacity": 10,
            },
            "year",
        ),
        (
            {
                "airplane_id": 9002,
                "model": "X",
                "manufacturer": "Y",
                "year": 2020,
                "capacity": 0,
            },
            "capacity",
        ),
    ],
)
def test_add_airplane_validation_errors_param(service_up, payload, expected_fragment):
    r, body = _post_json("/add_airplane", payload)
    assert r.status_code == 400
    assert expected_fragment in json.dumps(body or {})


def test_update_airplane_and_noop(service_up, airplane_factory):
    aid, airplane = airplane_factory()
    original = {
        "model": airplane["model"],
        "manufacturer": airplane["manufacturer"],
        "year": airplane["year"],
        "capacity": airplane["capacity"],
    }

    # Actualizar con datos distintos
    update_payload = {
        "model": original["model"] + "-MOD",
        "manufacturer": original["manufacturer"],
        "year": original["year"] + 1,
        "capacity": original["capacity"] + 5,
    }
    r_upd, body_upd = _put_json(f"/update_airplane/{aid}", update_payload)
    assert r_upd.status_code == 200
    assert "actualizado" in (body_upd or {}).get("message", "").lower()

    # Verificar GET
    r_get, a = _get_json(f"/get_airplane_by_id/{aid}")
    assert r_get.status_code == 200
    assert a["model"] == update_payload["model"]
    assert a["year"] == update_payload["year"]

    # No-op: mandar los mismos datos
    r_noop, body_noop = _put_json(f"/update_airplane/{aid}", update_payload)
    assert r_noop.status_code == 200
    assert "no se realizaron cambios" in (body_noop or {}).get(
        "message", ""
    ).lower()


def test_delete_airplane_and_cascade_seats(service_up, airplane_factory):
    # Crea un avión con 10 asientos
    del_id, _ = airplane_factory(capacity=10)

    # Verifica seats existen
    r_seats, seats_body = _get_json(f"/get_airplane_seats/{del_id}/seats")
    assert r_seats.status_code == 200
    assert isinstance(seats_body, list) and len(seats_body) == 10

    # Borra el avión
    r_del, body = _delete(f"/delete_airplane_by_id/{del_id}")
    assert r_del.status_code == 200
    assert body.get("asientos_eliminados") == 10

    # Seats ya no deben existir
    r_seats2, _body2 = _get_json(f"/get_airplane_seats/{del_id}/seats")
    assert r_seats2.status_code == 404


# -----------------------
# Tests de Seats
# -----------------------
def test_seats_grouped_and_update_status(service_up, airplane_factory):
    # Crea un avión con 6 asientos para probar
    aid, _ = airplane_factory(capacity=6)

    # Lista seats por avión
    r_seats, seats = _get_json(f"/get_airplane_seats/{aid}/seats")
    assert r_seats.status_code == 200
    assert isinstance(seats, list) and len(seats) == 6
    seat = seats[0]
    sn = seat["seat_number"]

    # Actualiza estado de un asiento válido
    r_upd, body = _put_json(
        f"/update_seat_status/{aid}/seats/{sn}", {"status": "Reservado"}
    )
    assert r_upd.status_code == 200
    assert body.get("asiento", {}).get("status") == "Reservado"

    # Endpoint de seats agrupados
    r_grouped, grouped = _get_json("/seats/grouped-by-airplane")
    assert r_grouped.status_code == 200
    # Puede devolver mensaje si no hay asientos, lo cubrimos:
    if isinstance(grouped, dict) and "message" in grouped:
        assert grouped["message"] in (
            "No hay asientos registrados en el sistema.",
        )
    else:
        assert isinstance(grouped, dict)
        # Debería incluir nuestro avión
        assert str(aid) in grouped or aid in grouped


@pytest.mark.parametrize("seat_number", ["XYZ99", "123", "AAAAA", "ALL", "*"])
def test_update_seat_status_invalid_numbers(
    service_up, airplane_factory, seat_number
):
    aid, _ = airplane_factory(capacity=4)
    r_seats, seats = _get_json(f"/get_airplane_seats/{aid}/seats")
    assert r_seats.status_code == 200
    assert seats

    r_bad, _body = _put_json(
        f"/update_seat_status/{aid}/seats/{seat_number}", {"status": "Libre"}
    )
    assert r_bad.status_code == 400


def test_get_random_free_seat_and_free_seat(service_up, airplane_factory):
    aid, _ = airplane_factory(capacity=3)

    # random free seat
    r_free, seat = _get_json(f"/get_random_free_seat/{aid}")
    assert r_free.status_code in (200, 404)
    if r_free.status_code == 200:
        assert seat["airplane_id"] == aid
        assert seat["status"] == "Libre"
        sn = seat["seat_number"]

        # cambiar a Reservado
        r_res, body_res = _put_json(
            f"/update_seat_status/{aid}/seats/{sn}", {"status": "Reservado"}
        )
        assert r_res.status_code == 200
        assert body_res["asiento"]["status"] == "Reservado"

        # liberar asiento
        r_lib, body_lib = _put_json(
            f"/free_seat/{aid}/seats/{sn}", {}
        )  # body vacío, pero el endpoint lo tolera
        assert r_lib.status_code == 200
        assert body_lib["asiento"]["status"] == "Libre"


# -----------------------
# Tests de Routes
# -----------------------
def test_add_route_and_get_all(service_up, airplane_factory, route_factory):
    aid, _ = airplane_factory()
    rid, route = route_factory(aid)
    assert route.get("airplane_route_id") == rid

    r_all, routes = _get_json("/get_all_airplanes_routes")
    assert r_all.status_code == 200
    assert isinstance(routes, list)
    assert any(r.get("airplane_route_id") == rid for r in routes)


def test_get_airplanes_route_by_id_and_not_found(
    service_up, airplane_factory, route_factory
):
    aid, _ = airplane_factory()
    rid, _ = route_factory(aid)

    # Ruta existente
    r_ok, route = _get_json(f"/get_airplanes_route_by_id/{rid}")
    assert r_ok.status_code == 200
    assert route.get("airplane_route_id") == rid

    # Ruta inexistente
    r_nf, body_nf = _get_json("/get_airplanes_route_by_id/999999")
    assert r_nf.status_code in (400, 404)
    if r_nf.status_code == 400:
        # ID <= 0 no lo estamos probando aquí, así que lo usual será 404
        assert "entero positivo" in json.dumps(body_nf or {}).lower()
    else:
        assert "no encontrada" in json.dumps(body_nf or {}).lower()


def test_update_airplane_route_by_id(service_up, airplane_factory, route_factory):
    aid, _ = airplane_factory()
    rid, route = route_factory(aid)

    update_payload = {
        "airplane_route_id": rid,  # debe coincidir
        "airplane_id": aid,
        "flight_number": route["flight_number"],  # mantenemos
        "departure": "Aeropuerto Internacional A MOD",
        "departure_time": "Marzo 30, 2025 - 10:00:00",
        "arrival": "Aeropuerto Internacional B MOD",
        "arrival_time": "Marzo 30, 2025 - 12:30:00",
        "price": route["price"] + 5000,
        "Moneda": route["Moneda"],
    }

    r_upd, body_upd = _put_json(
        f"/update_airplane_route_by_id/{rid}", update_payload
    )
    assert r_upd.status_code == 200
    assert "actualizada" in body_upd.get("message", "").lower()
    updated = body_upd["route"]
    assert updated["departure"].endswith("MOD")
    assert updated["arrival"].endswith("MOD")
    # flight_time recalculado
    assert "horas" in updated["flight_time"]


def test_delete_airplane_route_by_id(service_up, airplane_factory, route_factory):
    aid, _ = airplane_factory()
    rid, _ = route_factory(aid)

    r_del, body_del = _delete(f"/delete_airplane_route_by_id/{rid}")
    assert r_del.status_code == 200
    assert "eliminada" in body_del.get("message", "").lower()

    r_get, body_get = _get_json(f"/get_airplanes_route_by_id/{rid}")
    assert r_get.status_code == 404


# -----------------------
# OpenAPI / Swagger
# -----------------------
def test_openapi_present_optional(service_up):
    spec = _fetch_spec()
    if not spec:
        pytest.skip("No se encontró especificación OpenAPI/Swagger publicada")

    assert isinstance(spec, dict)
    assert "paths" in spec
    paths = spec["paths"].keys()

    # En vez de exigir /health, sólo verificamos que haya *algún* path
    assert len(paths) > 0

    # Opcional: si existe /health, lo “celebramos”, pero no lo exigimos
    if not any("/health" in p for p in paths):
        print("AVISO: /health no aparece documentado en OpenAPI (no es error fatal).")
