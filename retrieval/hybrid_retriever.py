from core import ctx
from retrieval.structured_db import StructuredDB
from retrieval.vector_store import VectorStore


_RRF_K = 60


def _rrf(ranked_lists: list[list[dict]]) -> list[dict]:
    scores = {}
    for rank_list in ranked_lists:
        for rank, item in enumerate(rank_list):
            item_id = item["id"]
            scores.setdefault(item_id, {"score": 0, "item": item})
            scores[item_id]["score"] += 1 / (_RRF_K + rank + 1)
    ranked = sorted(scores.values(), key=lambda x: -x["score"])
    return [r["item"] for r in ranked]


def _build_chroma_where(sql_filters: dict | None) -> dict | None:
    """Convert DuckDB-style filters to ChromaDB metadata where clause."""
    if not sql_filters:
        return None
    parts = {}
    if sql_filters.get("category"):
        parts["category"] = sql_filters["category"].lower()
    if sql_filters.get("neighborhood"):
        parts["neighborhood"] = sql_filters["neighborhood"].lower()
    if sql_filters.get("budget_level"):
        parts["budget_level"] = sql_filters["budget_level"].lower()
    if not parts:
        return None
    return {k: {"$eq": v} for k, v in parts.items()}


class HybridRetriever:
    def __init__(self, structured_db: StructuredDB, vector_store: VectorStore):
        self.structured_db = structured_db
        self.vector_store = vector_store

    def retrieve(self, router_output: dict, limit: int = 10) -> list[dict]:
        result_type = router_output.get("type", "hybrid")
        filters = router_output.get("filters", {}) or {}
        semantic_query = router_output.get("semantic_query", "")

        if result_type == "structured":
            return self.structured_db.query(filters, limit)

        if result_type == "semantic":
            if not semantic_query:
                return []
            chroma_where = _build_chroma_where(filters)
            vector_results = self.vector_store.search(semantic_query, limit * 2, where=chroma_where)
            ids = [r["id"] for r in vector_results]
            if ids:
                return self.structured_db.query({"ids": ids}, limit)
            return []

        structured = self.structured_db.query(filters, limit)
        semantic = []
        if semantic_query:
            chroma_where = _build_chroma_where(filters)
            vector_results = self.vector_store.search(semantic_query, limit * 2, where=chroma_where)
            if vector_results:
                ids = [r["id"] for r in vector_results]
                semantic = self.structured_db.query({"ids": ids}, limit * 2)

        merged = _rrf([structured, semantic])[:limit]

        reranker = getattr(ctx, "reranker", None)
        if reranker and semantic_query and len(merged) > 3:
            merged = reranker.rerank(semantic_query, merged, top_k=limit)

        return merged[:limit]
