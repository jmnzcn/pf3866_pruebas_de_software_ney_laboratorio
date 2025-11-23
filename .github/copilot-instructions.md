## Copilot / AI agent quick instructions

Purpose: short, actionable knowledge to make an AI coding agent productive in this repo.

Big picture
- This repo is a small microservice demo built with Flask. Main services live at:
  - `GestionVuelos/` — airplane, seats, routes (service inside container listens on 5000; docker-compose maps to host 5001)
  - `GestionReservas/` — reservations + payments (in-memory lists; container 5000 -> host 5002)
  - `Usuario/` — thin API that proxies/aggregates to `GestionVuelos` (container 5000 -> host 5003)
- Services communicate via HTTP using environment variables `GESTIONVUELOS_SERVICE` and `GESTIONRESERVAS_SERVICE`.

Runtime & how to run
- Preferred dev: start all services with docker-compose from repo root:

  docker-compose up --build

  Note: docker images run `gunicorn` binding to `0.0.0.0:5000` inside each container. docker-compose maps host ports:
  - host:5001 -> GestionVuelos(container:5000)
  - host:5002 -> GestionReservas(container:5000)
  - host:5003 -> Usuario(container:5000)

- Alternative local run: run service's `app.py` directly. Each `app.py` includes a Flask `app.run(...)` with a hard-coded port used for direct execution (GestionVuelos:5001, GestionReservas:5002, Usuario:5003).
  - When running locally outside Docker, make sure `config.env` or environment variables point to the other services (example in `GestionReservas/config.env`).

Key patterns & gotchas (important for code edits)
- In-memory state: core collections are plain Python lists (`airplanes`, `seats`, `airplanes_routes`, `reservations`, `payments`). Any change is ephemeral — tests and flows rely on runtime population.
- Validation: Marshmallow schemas are used heavily. Schemas use different unknown strategies (RAISE, INCLUDE). Respect schema fields and error conventions when adding fields.
- JSON duplicate-key detection: several endpoints detect duplicated keys in raw request body using a custom parser. Avoid changing that behavior silently.
- Date handling: routes expect/return Spanish month names and custom formatters (see `traducir_mes_espanol_a_ingles`, `formatear_fecha`, `formatear_fecha_espanol`). When adding date logic keep existing formats.
- Error shape: endpoints return JSON `{ "message": "...", "errors": {...} }` and use HTTP codes (400,404,500,503,504). Keep this shape for consistency.

Integration & important endpoints (examples)
- From reservations to flights (call chain): `GestionReservas` -> `GESTIONVUELOS_SERVICE` endpoints
  - /get_all_airplanes_routes  (used to validate routes)
  - /get_random_free_seat/{airplane_id}
  - /get_airplane_seats/{airplane_id}/seats
  - /update_seat_status/{airplane_id}/seats/{seat_number}
  - /free_seat/{airplane_id}/seats/{seat_number}
- Reservation-facing endpoints to be aware of: `GestionReservas/app.py` contains `/add_reservation`, `/create_payment`, `/get_reservation_by_code`, `/delete_reservation_by_id`, `/edit_reservation`.

Tests & debugging
- Tests live under `tests/` and expect services to be reachable (they call real HTTP endpoints). Run tests after bringing services up (docker-compose or local processes):

  pytest -q

- Tests use environment variables like `GV_BASE_URL` / `BASE_URL` to point at local services. For faster iteration, run a single service directly and point tests to it.

Where to look first (code pointers)
- Service implementations: `GestionVuelos/app.py`, `GestionReservas/app.py`, `Usuario/app.py` (primary logic and endpoints)
- Docker orchestration: `docker-compose.yml`, each service `Dockerfile` (note: gunicorn binds to container port 5000)
- Per-service env: `GestionReservas/config.env` (example values used when running locally)
- Tests: `tests/api/test_gestionvuelos.py` to understand expected behavior and test helpers.

How an AI agent should behave here
- Preserve API shapes and Marshmallow schemas. When adding fields, update the schema(s) and tests together.
- When changing inter-service calls, update both caller and callee and search for all uses of the endpoint (grep for the path). Use existing tests to validate integration.
- Prefer small, reversible edits with clear tests. Because state is in-memory, tests can rely on setup performed at service startup.

If something is unclear or you want me to expand examples (example payloads for `/add_reservation` or a quick test-run script), tell me which endpoint or workflow to expand and I'll update this file.
