# tools/generate_test_cases.py
import json
import argparse
from pathlib import Path

# Aquí iría tu cliente RAG/LLM real
def query_rag(endpoint: str):
    # TODO: usar tu índice real
    openapi_snippet = f"[OPENAPI para {endpoint}]"
    testing_notes = f"[Notas de prueba para {endpoint}]"
    return openapi_snippet, testing_notes

def call_llm(prompt: str) -> str:
    # TODO: reemplazar por llamada real a OpenAI u otro LLM
    # Por ahora podrías simular cargando un archivo mock para dev.
    raise NotImplementedError("Implementar integración con LLM aquí")


BASE_PROMPT = """... (el prompt de la sección anterior) ..."""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--endpoint", required=True,
                        help="Endpoint en formato 'POST /add_airplane'")
    parser.add_argument("--output", required=True,
                        help="Ruta de salida del JSON de casos")
    args = parser.parse_args()

    openapi_snippet, testing_notes = query_rag(args.endpoint)

    prompt = BASE_PROMPT.format(
        openapi_snippet=openapi_snippet,
        testing_notes=testing_notes,
        endpoint=args.endpoint,
    )

    llm_response = call_llm(prompt)  # string JSON
    data = json.loads(llm_response)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Casos generados en {out_path}")

if __name__ == "__main__":
    main()
