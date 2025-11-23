"""
mcp/rag_tester_simulator.py

Simulador simple de un "agente RAG tester" que:
- Lee documentación en docs/*.md
- Extrae casos de prueba para /add_airplane
- Sugiere cómo transformarlos en tests automatizados (pytest + requests)
"""

from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict


# Ruta base del proyecto (raíz: laboratorio/)
BASE_DIR = Path(__file__).resolve().parents[1]
DOCS_DIR = BASE_DIR / "docs"


@dataclass
class TestSuggestion:
    id: str
    categoria: str
    descripcion: str
    endpoint: str
    metodo_http: str
    payload_ejemplo: Dict
    esperados: Dict


def cargar_documentos() -> Dict[str, str]:
    """
    Carga el contenido de todos los .md en docs/ y los devuelve
    como un diccionario {nombre_archivo: contenido_str}.
    """
    docs = {}
    if not DOCS_DIR.exists():
        print(f"[WARN] La carpeta docs/ no existe en: {DOCS_DIR}")
        return docs

    for md in DOCS_DIR.glob("*.md"):
        try:
            docs[md.name] = md.read_text(encoding="utf-8")
        except Exception as e:
            print(f"[WARN] No se pudo leer {md}: {e}")
    return docs


def sugerencias_add_airplane(docs: Dict[str, str]) -> List[TestSuggestion]:
    """
    Simula un razonamiento RAG: asume que en
    EXPERIMENTO_RAG_01_add_airplane.md ya definiste los casos
    de negocio, y aquí los transforma en estructuras explícitas.
    """
    endpoint = "/add_airplane"
    metodo = "POST"

    sugerencias: List[TestSuggestion] = []

    # 1) Caso feliz básico
    sugerencias.append(
        TestSuggestion(
            id="ADD_OK_01",
            categoria="feliz",
            descripcion="Crear avión válido con ID nuevo y capacidad > 0",
            endpoint=endpoint,
            metodo_http=metodo,
            payload_ejemplo={
                "airplane_id": 1234,
                "model": "B737-RAG01",
                "manufacturer": "Boeing",
                "year": 2020,
                "capacity": 15,
            },
            esperados={
                "status_code": 201,
                "contiene_claves": ["message", "airplane"],
                "message_substring": "Avión y asientos agregados",
            },
        )
    )

    # 2) Duplicado por airplane_id
    sugerencias.append(
        TestSuggestion(
            id="ADD_ERR_ID_DUP",
            categoria="validacion_negocio",
            descripcion="Intentar crear avión con airplane_id ya existente",
            endpoint=endpoint,
            metodo_http=metodo,
            payload_ejemplo={
                "airplane_id": 1234,  # mismo que el caso feliz
                "model": "B737-RAG02",
                "manufacturer": "Boeing",
                "year": 2021,
                "capacity": 20,
            },
            esperados={
                "status_code": 400,
                "message_substring": "Ya existe un avión con ese ID",
            },
        )
    )

    # 3) Faltan campos obligatorios
    sugerencias.append(
        TestSuggestion(
            id="ADD_ERR_FALTANTES",
            categoria="validacion_estructura",
            descripcion="Body con campos obligatorios faltantes (solo airplane_id y model)",
            endpoint=endpoint,
            metodo_http=metodo,
            payload_ejemplo={
                "airplane_id": 2000,
                "model": "X-SIN-CAMPOS",
            },
            esperados={
                "status_code": 400,
                "message_substring": "Faltan campos obligatorios",
            },
        )
    )

    # 4) Campos extra no permitidos
    sugerencias.append(
        TestSuggestion(
            id="ADD_ERR_EXTRAS",
            categoria="validacion_estructura",
            descripcion="Body con campos extra que no están en el esquema (ej: color)",
            endpoint=endpoint,
            metodo_http=metodo,
            payload_ejemplo={
                "airplane_id": 2001,
                "model": "A320-EXTRA",
                "manufacturer": "Airbus",
                "year": 2018,
                "capacity": 12,
                "color": "rojo",
            },
            esperados={
                "status_code": 400,
                "message_substring": "Campos no válidos",
            },
        )
    )

    # 5) Año inválido (<= 0)
    sugerencias.append(
        TestSuggestion(
            id="ADD_ERR_YEAR",
            categoria="validacion_dominio",
            descripcion="Campo year <= 0 debería ser rechazado",
            endpoint=endpoint,
            metodo_http=metodo,
            payload_ejemplo={
                "airplane_id": 2002,
                "model": "MD80-NEG",
                "manufacturer": "McDonnell",
                "year": 0,
                "capacity": 10,
            },
            esperados={
                "status_code": 400,
                "message_substring": "El campo 'year' debe ser un entero positivo",
            },
        )
    )

    # 6) Capacidad inválida (0 o negativa)
    sugerencias.append(
        TestSuggestion(
            id="ADD_ERR_CAPACITY",
            categoria="validacion_dominio",
            descripcion="Capacidad <= 0 debería ser rechazada",
            endpoint=endpoint,
            metodo_http=metodo,
            payload_ejemplo={
                "airplane_id": 2003,
                "model": "E190-CAP0",
                "manufacturer": "Embraer",
                "year": 2017,
                "capacity": 0,
            },
            esperados={
                "status_code": 400,
                "message_substring": "capacity",
            },
        )
    )

    # 7) JSON ausente o mal formado
    sugerencias.append(
        TestSuggestion(
            id="ADD_ERR_BODY_VACIO",
            categoria="robustez",
            descripcion="No enviar body JSON debería devolver error claro",
            endpoint=endpoint,
            metodo_http=metodo,
            payload_ejemplo={},
            esperados={
                "status_code": 400,
                "message_substring": "No se recibió ningún cuerpo JSON",
            },
        )
    )

    return sugerencias


def imprimir_resumen_sugerencias(sugerencias: List[TestSuggestion]) -> None:
    """
    Imprime un resumen legible en consola.
    """
    print("=" * 80)
    print("SUGERENCIAS DE TEST PARA /add_airplane (simulador RAG)".center(80))
    print("=" * 80)
    for s in sugerencias:
        print(f"- ID: {s.id}")
        print(f"  Categoría : {s.categoria}")
        print(f"  Endpoint  : {s.metodo_http} {s.endpoint}")
        print("  Descripción:")
        print(f"    {s.descripcion}")
        print("  Payload ejemplo:")
        for k, v in s.payload_ejemplo.items():
            print(f"    {k}: {v!r}")
        print("  Esperados:")
        for k, v in s.esperados.items():
            print(f"    {k}: {v!r}")
        print("-" * 80)


def generar_borrador_pytest(sugerencias: List[TestSuggestion]) -> str:
    """
    Genera un borrador de código pytest parametrizado que podrías pegar
    en tests/api/test_gestionvuelos_rag.py, por ejemplo.
    """
    lines: List[str] = []
    lines.append("import pytest")
    lines.append("import requests")
    lines.append("import os")
    lines.append("")
    lines.append('BASE_URL = os.getenv("GV_BASE_URL", "http://localhost:5001")')
    lines.append("")
    lines.append("")
    lines.append("@pytest.mark.parametrize(")
    lines.append("    'case_id, payload, expected_status, expected_msg', [")
    for s in sugerencias:
        msg = s.esperados.get("message_substring", "")
        lines.append(
            f"        ({s.id!r}, {s.payload_ejemplo!r}, {s.esperados.get('status_code', 200)}, {msg!r}),"
        )
    lines.append("    ]")
    lines.append(")")
    lines.append("def test_add_airplane_rag_cases(case_id, payload, expected_status, expected_msg):")
    lines.append('    """Casos generados/sugeridos por el agente RAG tester."""')
    lines.append('    r = requests.post(f"{BASE_URL}/add_airplane", json=payload)')
    lines.append("    body = {}")
    lines.append("    try:")
    lines.append("        body = r.json()")
    lines.append("    except Exception:")
    lines.append("        body = {}")
    lines.append("")
    lines.append(
        '    assert r.status_code == expected_status, '
        'f"[{case_id}] Código inesperado: {r.status_code} {r.text}"'
    )
    lines.append("    if expected_msg:")
    lines.append(
        "        assert expected_msg in (body.get('message', '') or r.text), "
        'f"[{case_id}] Mensaje esperado no encontrado"'
    )
    return "\n".join(lines)


def main():
    print(f"[INFO] BASE_DIR : {BASE_DIR}")
    print(f"[INFO] DOCS_DIR : {DOCS_DIR}")
    docs = cargar_documentos()
    if not docs:
        print(
            "[WARN] No se cargaron documentos .md; el simulador seguirá usando plantillas internas."
        )
    else:
        print(f"[INFO] Documentos cargados: {', '.join(docs.keys())}")

    sugerencias = sugerencias_add_airplane(docs)
    imprimir_resumen_sugerencias(sugerencias)

    print("\n\n=== BORRADOR DE TEST PYTEST (copiar/pegar en un archivo de tests) ===\n")
    borrador = generar_borrador_pytest(sugerencias)
    print(borrador)


if __name__ == "__main__":
    main()
