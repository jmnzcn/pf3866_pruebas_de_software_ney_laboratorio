from pathlib import Path
import json, glob
from chromadb import Client
from chromadb.config import Settings

DOC_GLOBS = [
    "*/**/openapi.json",
    "*/**/swagger.json",
    "*/**/*.md",
    "*/**/*.log",
    "*/**/app.py",  # incluye Marshmallow schemas
]

def build_index(db_path="tests/.ragdb"):
    client = Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=db_path))
    col = client.get_or_create_collection("repo")
    docs, ids, metas = [], [], []
    for pat in DOC_GLOBS:
        for p in glob.glob(pat, recursive=True):
            try:
                text = Path(p).read_text(encoding="utf-8", errors="ignore")
                docs.append(text[:200_000])  # recorte defensivo
                ids.append(p)
                metas.append({"path": p})
            except Exception:
                pass
    if docs:
        col.add(documents=docs, ids=ids, metadatas=metas)
        client.persist()
    return col

if __name__ == "__main__":
    build_index()
