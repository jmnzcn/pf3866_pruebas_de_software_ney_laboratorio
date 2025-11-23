import json, re
from .rag_client import RAG

def gen_airplane_payloads():
    rag = RAG()
    ctx = rag.retrieve("AirplaneSchema campos obligatorios Marshmallow y ejemplos válidos")
    # Heurística: deduce tipos y crea 3 casos válidos + 2 límites
    base = {"airplane_id": 99, "model":"B737", "manufacturer":"Boeing", "year":2020, "capacity":15}
    cases = [
        base,
        {**base, "airplane_id": 100, "model":"A320", "manufacturer":"Airbus"},
        {**base, "airplane_id": 101, "year":2019, "capacity":1},
        # bordes
        {**base, "airplane_id": 102, "year":1},      # mínimo válido
        {**base, "airplane_id": 103, "capacity":999} # stress de capacidad
    ]
    return cases
