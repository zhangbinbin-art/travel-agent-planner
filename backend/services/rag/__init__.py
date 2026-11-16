"""RAG 包入口：对外暴露检索能力。"""
from services.rag.store import index_exists, search  # noqa: F401

__all__ = ["search", "index_exists"]
