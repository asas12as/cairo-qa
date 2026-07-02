import chromadb
from chromadb.api.types import EmbeddingFunction, Embeddings
from chromadb.config import Settings
from chromadb.errors import NotFoundError


class _EmbeddingFn(EmbeddingFunction):
    def __init__(self, embedder):
        self.embedder = embedder

    def __call__(self, input: list[str]) -> Embeddings:
        return self.embedder.embed(input)


class VectorStore:
    def __init__(self, path: str, collection_name: str, embedder=None):
        self.client = chromadb.PersistentClient(
            path=path,
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection_name = collection_name
        self.collection = None
        self._embedder = embedder

    def get_or_create_collection(self):
        ef = _EmbeddingFn(self._embedder) if self._embedder else None
        try:
            self.collection = self.client.get_collection(
                self.collection_name, embedding_function=ef
            )
        except (ValueError, NotFoundError):
            self.collection = self.client.create_collection(
                self.collection_name, embedding_function=ef
            )
        return self.collection

    def delete_collection(self):
        try:
            self.client.delete_collection(self.collection_name)
        except (ValueError, NotFoundError):
            pass
        self.collection = None

    def add_places(self, places: list[dict]):
        ids = []
        documents = []
        metadatas = []

        for p in places:
            doc = " | ".join(filter(None, [
                p.get("name", ""),
                p.get("category", ""),
                p.get("genre_type", ""),
                p.get("neighborhood", ""),
                p.get("address", ""),
                p.get("budget_level", ""),
                p.get("notes", ""),
            ]))
            ids.append(str(p["id"]))
            metadatas.append({
                "id": p["id"],
                "name": p.get("name", ""),
                "category": p.get("category", ""),
                "genre_type": p.get("genre_type", ""),
                "neighborhood": p.get("neighborhood", ""),
                "budget_level": p.get("budget_level", ""),
            })
            documents.append(doc)

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

    def search(self, query: str, n_results: int = 10, where: dict | None = None) -> list[dict]:
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
            where=where,
        )
        if not results["ids"] or not results["ids"][0]:
            return []
        rows = []
        for i in range(len(results["ids"][0])):
            meta = results["metadatas"][0][i]
            rows.append({
                "id": int(meta.get("id", results["ids"][0][i])),
                "name": meta.get("name", ""),
                "category": meta.get("category", ""),
                "neighborhood": meta.get("neighborhood", ""),
                "genre_type": meta.get("genre_type", ""),
                "budget_level": meta.get("budget_level", ""),
                "document": results["documents"][0][i],
                "distance": results["distances"][0][i] if results.get("distances") else None,
            })
        return rows
