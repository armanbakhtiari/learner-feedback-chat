"""
Bank-of-Situations Vector Store + Retriever
===========================================

A dedicated vector database for the bank of situations (``bank_situations.BANK_SITUATIONS``).
Unlike ``backend/rag_tool.py`` (which indexes per-training PDF knowledge bases), this module
indexes the *text* of candidate future-training situations and is built **once, always**,
independently of which training the learner selected for evaluation.

It is used by ``backend/suggestions_agent.py`` to retrieve situations relevant to a learner's
learning gaps on the "Suggest new trainings" page.

Mirrors the structure of ``AgenticRAGModule`` (Chroma client, OpenAI embeddings, hash-based
re-index guard) but its documents come from Python text rather than PDF files.
"""

import os
from typing import Any, Dict, List
from pathlib import Path

from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

import sys
sys.path.append(str(Path(__file__).parent.parent))

from bank_situations import BANK_SITUATIONS, compute_bank_hash


# Reuse the same persistent Chroma directory as the main RAG module.
ROOT_DIR = Path(__file__).parent.parent
CHROMA_PERSIST_DIR = ROOT_DIR / ".chroma_db"
BANK_COLLECTION_NAME = "bank_situations"


class BankRAGModule:
    """Vector store + retriever over the bank of situations."""

    def __init__(self):
        self.collection_name = BANK_COLLECTION_NAME

        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )

        CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)

        # Lazy import of chromadb to avoid importing numpy at module import time.
        import chromadb
        from chromadb.config import Settings
        self.chroma_client = chromadb.PersistentClient(
            path=str(CHROMA_PERSIST_DIR),
            settings=Settings(anonymized_telemetry=False),
        )

        self.collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

        # Only split a situation if it is unusually long; one doc per situation otherwise.
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

        self.bank_hash_file = CHROMA_PERSIST_DIR / f".bank_hash_{self.collection_name}"

        self._ensure_indexed()

    # ------------------------------------------------------------------ indexing

    def _get_stored_hash(self) -> str:
        if self.bank_hash_file.exists():
            return self.bank_hash_file.read_text().strip()
        return ""

    def _save_hash(self, value: str):
        self.bank_hash_file.write_text(value)

    def _ensure_indexed(self):
        """Index the bank if empty or if its content changed since last index."""
        current_hash = compute_bank_hash()
        stored_hash = self._get_stored_hash()
        doc_count = self.collection.count()

        if doc_count == 0:
            print(f"📚 [{self.collection_name}] No documents. Indexing bank of situations...")
            self._index_situations()
            self._save_hash(current_hash)
            return

        if current_hash != stored_hash:
            print(f"📚 [{self.collection_name}] Bank changed. Re-indexing...")
            self._clear_and_reindex()
            self._save_hash(current_hash)
            return

        print(f"📚 [{self.collection_name}] Using cached bank vector store ({doc_count} chunks)")

    def _clear_and_reindex(self):
        try:
            self.chroma_client.delete_collection(self.collection_name)
        except Exception:
            pass
        self.collection = self.chroma_client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._index_situations()

    def _index_situations(self):
        all_chunks: List[str] = []
        all_metadatas: List[Dict[str, Any]] = []
        all_ids: List[str] = []

        for entry in BANK_SITUATIONS:
            situation_id = entry["id"]
            content = entry["content"]

            # Most situations fit comfortably in one chunk; split only the long ones.
            if len(content) <= 2200:
                pieces = [content]
            else:
                pieces = self.text_splitter.split_text(content)

            for i, piece in enumerate(pieces):
                all_chunks.append(piece)
                all_metadatas.append({
                    "situation_id": situation_id,
                    "domain": entry["domain"],
                    "title": entry["title"],
                    "objectives": entry["objectives"],
                    "chunk_index": i,
                    "total_chunks": len(pieces),
                })
                all_ids.append(f"{situation_id}_{i}")

        if not all_chunks:
            print("⚠️ No bank situations to index")
            return

        print(f"🔄 Generating embeddings for {len(all_chunks)} bank chunks...")
        embeddings = self.embeddings.embed_documents(all_chunks)
        self.collection.add(
            documents=all_chunks,
            embeddings=embeddings,
            metadatas=all_metadatas,
            ids=all_ids,
        )
        print(f"✅ Indexed {len(all_chunks)} bank chunks ({len(BANK_SITUATIONS)} situations)")

    # ------------------------------------------------------------------ retrieval

    def retrieve(self, query: str, top_k: int = 6) -> List[Dict[str, Any]]:
        """Retrieve the top-k most relevant bank chunks for a query."""
        query_embedding = self.embeddings.embed_query(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        chunks: List[Dict[str, Any]] = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                distance = results["distances"][0][i] if results.get("distances") else 0
                chunks.append({
                    "content": doc,
                    "situation_id": metadata.get("situation_id", "unknown"),
                    "domain": metadata.get("domain", "unknown"),
                    "title": metadata.get("title", "Unknown"),
                    "objectives": metadata.get("objectives", ""),
                    "relevance_score": 1 - distance,
                })
        return chunks


# Module-level singleton
_bank_rag_instance: BankRAGModule = None


def get_bank_rag() -> BankRAGModule:
    """Get (or lazily create) the bank RAG singleton, building the vector store if needed."""
    global _bank_rag_instance
    if _bank_rag_instance is None:
        _bank_rag_instance = BankRAGModule()
    return _bank_rag_instance


def ensure_bank_indexed() -> BankRAGModule:
    """Ensure the bank vector store is built. Safe to call on every /evaluate."""
    return get_bank_rag()
