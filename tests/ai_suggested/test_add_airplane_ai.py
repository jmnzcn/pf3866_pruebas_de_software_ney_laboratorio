"""
Tests AI-sugeridos para POST /add_airplane
Archivo generado automáticamente a partir de tests/ai_suggested/cases_add_airplane.json
"""

import os
import random
import json
import pytest
import requests

BASE_URL = os.getenv("GV_BASE_URL", "http://localhost:5001")

@pytest.mark.ai_generated
class TestAiGeneratedPOST__add_airplane:

    def _resolve_dynamic_values(self, payload):
        # ...
        ...

    @pytest.mark.endpoint("POST /add_airplane")
    @pytest.mark.case_id("GV-ADD-PLANE-001")
    def test_gv_add_plane_001(self):
        """
        Crear avión válido (happy path)
        Reglas de negocio: year > 0; capacity > 0; airplane_id debe ser único
        """
        method = "POST"
        path = "/add_airplane"
        input_payload = {
          "airplane_id": "RANDOM_INT_800_899",
          "model": "B737-AI-001",
          "manufacturer": "Boeing",
          "year": 2020,
          "capacity": 15
        }
        expected = {
          "status_code": 201,
          "json_contains": {
            "message": "Avión y asientos agregados con éxito"
          }
        }

        input_payload = self._resolve_dynamic_values(input_payload)
        url = f"{BASE_URL}{path}"
        r = requests.request(method, url, json=input_payload, timeout=10)
        assert r.status_code == expected["status_code"]
        body = r.json()
        assert body.get("message") == "Avión y asientos agregados con éxito"

    @pytest.mark.endpoint("POST /add_airplane")
    @pytest.mark.case_id("GV-ADD-PLANE-002")
    def test_gv_add_plane_002(self):
        """
        Falta campo obligatorio (capacity)
        Reglas de negocio: Debe rechazar payloads con campos faltantes
        """
        # ...
