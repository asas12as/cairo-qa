"""Auto-seed script: rebuilds DuckDB + ChromaDB from bundled CSV data."""
import os
import sys

os.environ.setdefault("CONFIG_PATH", "config.docker.yaml")


def _is_empty(db_path: str) -> bool:
    import duckdb
    try:
        c = duckdb.connect(db_path)
        count = c.execute("SELECT COUNT(*) FROM places").fetchone()[0]
        c.close()
        return count == 0
    except Exception:
        return True


def seed():
    db_path = os.environ.get("DB_PATH", "/data/places.duckdb")
    vs_path = os.environ.get("VECTOR_STORE_PATH", "/data/chroma_db")
    csv_dir = os.environ.get("CSV_DIR", "/app/data/csv")

    if os.path.exists(db_path) and not _is_empty(db_path):
        print(f"Database at {db_path} already has data — skipping seed.")
        return

    from config import Config
    from retrieval.structured_db import StructuredDB
    from models.embedder import Embedder
    from retrieval.vector_store import VectorStore
    from ingestion.replace_data import replace_all

    config_path = os.environ["CONFIG_PATH"]
    config = Config(config_path)

    print("Connecting to DB...")
    db = StructuredDB(db_path)
    db.connect()
    db.create_table()

    print("Loading embedder...")
    embedder = Embedder(config.embedder.model)

    print("Connecting to vector store...")
    vs = VectorStore(vs_path, config.vector_store.collection, embedder)
    vs.get_or_create_collection()

    print(f"Seeding from {csv_dir}...")
    count = replace_all(csv_dir, db, vs)
    db.close()
    print(f"Done. {count} places loaded.")


if __name__ == "__main__":
    seed()
