from sentence_transformers import CrossEncoder


class Reranker:
    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, docs: list[dict], top_k: int = 5) -> list[dict]:
        if not docs:
            return docs
        pairs = []
        for d in docs:
            text = " | ".join(filter(None, [
                d.get("name", ""),
                d.get("category", ""),
                d.get("genre_type", ""),
                d.get("neighborhood", ""),
                d.get("notes", ""),
            ]))
            pairs.append((query, text))
        scores = self.model.predict(pairs)
        ranked = sorted(zip(docs, scores), key=lambda x: -x[1])
        return [d for d, _ in ranked[:top_k]]
