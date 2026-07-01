"""Application-wide dependency injection container.

Populated once at startup in main.py, then imported from anywhere:
    from core import ctx
    ctx.db.get_all()
"""

import os


def data_path(*parts: str) -> str:
    """Resolve a path relative to the configurable DATA_DIR."""
    base = os.environ.get("DATA_DIR", "data")
    return os.path.join(base, *parts)


class AppContext:
    """Holds all shared application dependencies."""
    def __init__(self) -> None:
        self.db = None
        self.llm = None
        self.retriever = None
        self.router_agent = None
        self.answer_gen = None
        self.logger = None
        self.prefs = None
        self.memory = None
        self.config_path: str | None = None


ctx = AppContext()
