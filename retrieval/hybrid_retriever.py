from retrieval.structured_db import StructuredDB
from retrieval.vector_store import VectorStore


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
            vector_results = self.vector_store.search(semantic_query, limit * 2)
            ids = [r["id"] for r in vector_results]
            if ids:
                return self.structured_db.query({"ids": ids}, limit)
            return []

        structured = self.structured_db.query(filters, limit)
        existing_ids = {r["id"] for r in structured}

        if semantic_query and len(structured) < limit:
            vector_results = self.vector_store.search(semantic_query, limit * 2)
            extra_ids = [r["id"] for r in vector_results if r["id"] not in existing_ids]
            if extra_ids:
                extra_rows = self.structured_db.query({"ids": extra_ids[:limit]}, limit)
                if filters.get("neighborhood"):
                    hood = filters["neighborhood"].lower()
                    extra_rows = [r for r in extra_rows if hood in (r.get("neighborhood") or "").lower()]
                if filters.get("category"):
                    cat = filters["category"].lower()
                    extra_rows = [r for r in extra_rows if cat in (r.get("category") or "").lower()]
                seen = existing_ids.copy()
                for r in extra_rows:
                    if r["id"] not in seen:
                        structured.append(r)
                        seen.add(r["id"])

        return structured[:limit]
