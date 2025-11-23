from .rag_client import RAG

def summarize_logs(log_text: str, hint: str=""):
    rag = RAG()
    ctx = rag.retrieve("Errores comunes Flask Marshmallow validación y concurrencia RLock")
    # síntesis simple: top líneas repetidas
    lines = [l.strip() for l in log_text.splitlines() if l.strip()]
    from collections import Counter
    top = Counter(lines).most_common(10)
    summary = "\n".join(f"{c}× {t}" for t,c in top)
    return f"HINT:{hint}\nTOP:\n{summary}\nCTX:\n" + "\n---\n".join(c for _,c in ctx[:3])
