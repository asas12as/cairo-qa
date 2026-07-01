import argparse
import atexit
import os
import time

import uvicorn
from duckdb import IOException
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api import router as api_router
from api.admin import router as admin_router
from api.auth import router as auth_router
from config import Config
from core import ctx

DATA_DIR = os.environ.get("DATA_DIR", "data")


def _connect_db(config, retries=3, delay=2):
    for attempt in range(retries):
        try:
            from retrieval.structured_db import StructuredDB
            db = StructuredDB(config.db.path)
            db.connect()
            db.create_table()
            return db
        except IOException as e:
            if attempt < retries - 1:
                print(f"DB locked (attempt {attempt+1}/{retries}), retrying in {delay}s...")
                time.sleep(delay)
            else:
                print(f"Cannot open database after {retries} attempts: {e}")
                exit(1)


def main():
    parser = argparse.ArgumentParser(description="Cairo Places QA System")
    parser.add_argument("--config", default=None, help="Path to config file")
    parser.add_argument("--ingest", help="Ingest a CSV file and exit")
    args = parser.parse_args()

    config_path = args.config or os.environ.get("CONFIG_PATH", "config.yaml")
    config = Config(config_path)
    ctx.db = _connect_db(config)
    ctx.config_path = config_path
    atexit.register(ctx.db.close)

    if args.ingest:
        from models.embedder import Embedder
        from retrieval.vector_store import VectorStore
        embedder = Embedder(config.embedder.model)
        vector_store = VectorStore(config.vector_store.path, config.vector_store.collection, embedder)
        vector_store.get_or_create_collection()
        from ingestion.pipeline import ingest_csv
        count = ingest_csv(args.ingest, ctx.db, vector_store)
        print(f"Ingested {count} places from {args.ingest}")
        return

    print("Loading embedder...")
    from models.embedder import Embedder
    embedder = Embedder(config.embedder.model)

    print("Connecting to vector store...")
    from retrieval.vector_store import VectorStore
    vector_store = VectorStore(config.vector_store.path, config.vector_store.collection, embedder)
    vector_store.get_or_create_collection()

    print("Loading LLM...")
    from agent.query_router import QueryRouter
    from agent.answer_generator import AnswerGenerator
    if os.environ.get("OLLAMA_API_KEY"):
        from models.ollama_llm import OllamaLLM
        ctx.llm = OllamaLLM(config)
        print(f"  Using Ollama API: {ctx.llm.model}")
    else:
        from models.local_llm import LocalLLM
        ctx.llm = LocalLLM(config)
        print("  Loading local model (this may take a moment)...")
    ctx.llm.load()

    from retrieval.hybrid_retriever import HybridRetriever
    from learning.conversation_logger import ConversationLogger
    from learning.conversation_memory import ConversationMemory
    from agent.user_preferences import UserPreferences
    from core import data_path

    ctx.retriever = HybridRetriever(ctx.db, vector_store)
    ctx.router_agent = QueryRouter()
    ctx.answer_gen = AnswerGenerator(ctx.llm)
    ctx.logger = ConversationLogger(data_path("conversations"))
    ctx.prefs = UserPreferences(data_path("user_profiles"))
    ctx.memory = ConversationMemory(DATA_DIR)

    app = FastAPI(title="Cairo Places QA", version="1.0.0")
    app.include_router(api_router)
    app.include_router(auth_router, prefix="/auth")
    app.include_router(admin_router, prefix="/admin")
    avatars_dir = data_path("profiles", "avatars")
    os.makedirs(avatars_dir, exist_ok=True)
    app.mount("/avatars", StaticFiles(directory=avatars_dir), name="avatars")
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

    print(f"Server starting on http://{config.server.host}:{config.server.port}")
    uvicorn.run(app, host=config.server.host, port=config.server.port)


if __name__ == "__main__":
    main()
