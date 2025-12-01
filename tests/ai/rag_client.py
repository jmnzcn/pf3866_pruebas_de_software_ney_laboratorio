# tests/ai/rag_client.py

import chromadb
from pathlib import Path


class RAG:
    def __init__(self, db_path: str = "tests/.ragdb"):
        # Asegúrate de que la carpeta exista
        Path(db_path).mkdir(parents=True, exist_ok=True)

        # Nueva forma recomendada en Chromadb reciente
        self.client = chromadb.PersistentClient(path=db_path)

        # El API de colecciones se mantiene muy parecido
        self.col = self.client.get_or_create_collection(name="repo")

    def retrieve(self, question: str, k: int = 6):
        res = self.col.query(query_texts=[question], n_results=k)
        chunks = res.get("documents", [[]])[0]
        paths = [m.get("path") for m in res.get("metadatas", [[]])[0]]
        return list(zip(paths, chunks))
