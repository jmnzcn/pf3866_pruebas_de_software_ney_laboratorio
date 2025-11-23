import requests

BASE_URL_RESERVAS = "http://localhost:5002"

SPEC_CANDIDATES = [
    "/openapi.json",
    "/apispec_1.json",
    "/docs/openapi.json",
    "/docs/apispec_1.json",
    "/swagger.json",
]

def _fetch_status_enum_from_spec():
    for ep in SPEC_CANDIDATES:
        try:
            r = requests.get(f"{BASE_URL_RESERVAS}{ep}", timeout=5)
            if r.status_code == 200 and "application/json" in r.headers.get("content-type",""):
                spec = r.json()
                paths = spec.get("paths", {})
                post = paths.get("/add_reservation", {}).get("post", {})
                rb = post.get("requestBody", {})
                content = rb.get("content", {}).get("application/json", {})
                schema = content.get("schema", {})

                def find_enum(node):
                    if not isinstance(node, dict):
                        return None
                    props = node.get("properties", {})
                    st = props.get("status")
                    if isinstance(st, dict) and isinstance(st.get("enum"), list):
                        return st["enum"]
                    for k in ("oneOf", "allOf", "anyOf"):
                        if k in node and isinstance(node[k], list):
                            for sub in node[k]:
                                found = find_enum(sub)
                                if found:
                                    return found
                    return None

                enum_vals = find_enum(schema)
                if enum_vals:
                    return enum_vals
        except Exception:
            pass
    return None

def _try_create(payload_base, statuses):
    last = None
    for st in statuses:
        payload = dict(payload_base)
        payload["status"] = st
        r = requests.post(f"{BASE_URL_RESERVAS}/add_reservation", json=payload, timeout=10)
        print(f"DEBUG POST status={st!r} ->", r.status_code, r.text)
        last = r
        if r.status_code in (200, 201):
            return r
    return last

def test_crear_reserva_contrato_y_estado():
    # Ajusta host/puerto si aplica
    payload_base = {
        "passport_number": "A1234567",
        "full_name": "Juan Perez",
        "email": "jp@example.com",
        "phone_number": "+50670000000",
        "emergency_contact_name": "Ana",
        "emergency_contact_phone": "+50671111111",
        "airplane_id": 1,           # entero requerido por tu schema
        "airplane_route_id": 1001,  # entero requerido por tu schema
        "seat_number": "12A",
    }

    # 1) Intentar leer enum real desde OpenAPI
    enum_vals = _fetch_status_enum_from_spec()
    print("DEBUG enum desde spec:", enum_vals)

    # 2) Candidatos de respaldo si el spec no expone enum
    fallbacks = [
        # mayúsculas inglés
        "CREATED","CONFIRMED","PENDING","BOOKED","ACTIVE","ISSUED","PAID","RESERVED",
        # minúsculas inglés
        "created","confirmed","pending","booked","active","issued","paid","reserved",
        # español
        "CREADA","CONFIRMADA","PENDIENTE","RESERVADA","ACTIVA","EMITIDA","PAGADA",
        "creada","confirmada","pendiente","reservada","activa","emitida","pagada",
    ]
    # 3) También probar numéricos típicos de Enum (0..9)
    numeric = list(range(0,10))

    candidates = enum_vals or fallbacks + numeric

    r = _try_create(payload_base, candidates)
    assert r.status_code in (200, 201), "El backend rechazó todos los valores probados para 'status'. Revisa tu esquema real."
    data = r.json()
    assert data.get("reservation_code"), "Falta reservation_code en la respuesta"

    # Verificación de listado simple
    r2 = requests.get(f"{BASE_URL_RESERVAS}/reservations", timeout=10)
    print("DEBUG GET /reservations:", r2.status_code, r2.text[:400])
    assert r2.status_code == 200
    items = r2.json()
    assert any(
        x.get("seat_number") == "12A"
        and x.get("airplane_id") == 1
        and x.get("airplane_route_id") == 1001
        for x in items
    ), "La reserva creada no aparece en el listado"
