"""
Shared ChromaDB client factory.

Returns a Chroma Cloud client when the CHROMA_API_KEY env var is set (production),
otherwise falls back to a local PersistentClient under .chroma_db (local development).

Both backend/rag_tool.py and backend/bank_rag.py use this so there is a single,
consistent connection path. chromadb is imported inside the function so that importing
this module stays cheap (the heavy import only happens when a client is actually built,
which is itself gated behind the lazy-loaded RAG modules).
"""

import os
from pathlib import Path

ROOT_DIR = Path(__file__).parent.parent
CHROMA_PERSIST_DIR = ROOT_DIR / ".chroma_db"


def using_chroma_cloud() -> bool:
    """True when configured to talk to Chroma Cloud rather than a local store."""
    return bool(os.getenv("CHROMA_API_KEY"))


def get_chroma_client():
    """Build a Chroma client.

    Chroma Cloud when CHROMA_API_KEY is set (requires CHROMA_TENANT and
    CHROMA_DATABASE too); otherwise a local PersistentClient for development.
    """
    import chromadb

    if using_chroma_cloud():
        return chromadb.CloudClient(
            api_key=os.environ["CHROMA_API_KEY"],
            tenant=os.environ["CHROMA_TENANT"],
            database=os.environ["CHROMA_DATABASE"],
        )

    from chromadb.config import Settings

    CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(CHROMA_PERSIST_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
