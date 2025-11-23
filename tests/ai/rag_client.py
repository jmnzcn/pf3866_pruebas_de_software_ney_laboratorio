from chromadb import Client
from chromadb.config import Settings

class RAG:
    def __init__(self, db_path="tests/.ragdb"):
        self.client = Client(Settings(chroma_db_impl="duckdb+parquet", persist_directory=db_path))
        self.col = self.client.get_or_create_collection("repo")

    def retrieve(self, question, k=6):
        res = self.col.query(query_texts=[question], n_results=k)
        chunks = res.get("documents", [[]])[0]
        paths  = [m.get("path") for m in res.get("metadatas", [[]])[0]]
        return list(zip(paths, chunks))
