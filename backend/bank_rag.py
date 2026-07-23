"""
Bank-of-Situations Vector Store + Retriever
===========================================

A dedicated vector database for the shared **bank of trainings** (Supabase trainings
with origin ``seed_bank`` / ``suggested_bank``, each a situation the learner can practice).
Unlike ``backend/rag_tool.py`` (which indexes per-training PDF knowledge bases), this module
indexes the *text* of candidate future-training situations.

It is used by ``backend/suggestions_agent.py`` to retrieve trainings relevant to a learner's
learning gaps on the "Suggest new trainings" tab. The bank grows over time (new bank
trainings), so it is (re)indexed at runtime whenever the DB bank content changes.

Mirrors the structure of ``AgenticRAGModule`` (Chroma client, OpenAI embeddings, hash-based
re-index guard) but its documents come from the Supabase bank rather than PDF files.
"""

import os
from typing import Any, Dict, List
from pathlib import Path

from langchain_openai import OpenAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

import sys
sys.path.append(str(Path(__file__).parent.parent))

from backend.db import repo


# Reuse the same persistent Chroma directory as the main RAG module.
ROOT_DIR = Path(__file__).parent.parent
CHROMA_PERSIST_DIR = ROOT_DIR / ".chroma_db"
BANK_COLLECTION_NAME = "bank_situations"

# Max records per collection.add() request (Chroma Cloud free-tier caps this at 300).
CHROMA_ADD_BATCH = 250


class BankRAGModule:
    """Vector store + retriever over the bank of situations."""

    def __init__(self, index: bool = True):
        self.collection_name = BANK_COLLECTION_NAME

        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.getenv("OPENAI_API_KEY"),
        )

        # ChromaDB client (Chroma Cloud in prod, local PersistentClient in dev).
        from .chroma_client import get_chroma_client
        self.chroma_client = get_chroma_client()

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

        # Index at first use if the collection is empty. Content changes are applied
        # via explicit reindex()/add_training() calls (seed script, new bank trainings),
        # which is Chroma-Cloud-friendly (no per-request re-embedding).
        if index:
            self._ensure_indexed()

    # ------------------------------------------------------------------ indexing

    def _ensure_indexed(self):
        """Index the bank once if the collection is empty."""
        doc_count = self.collection.count()
        if doc_count == 0:
            print(f"📚 [{self.collection_name}] Empty. Indexing bank of trainings from DB...")
            self._index_bank()
        else:
            print(f"📚 [{self.collection_name}] Using existing bank vector store ({doc_count} chunks)")

    def reindex(self):
        """Force a full rebuild from the current DB bank. Call after seeding/bank changes."""
        try:
            self.chroma_client.delete_collection(self.collection_name)
        except Exception:
            pass
        self.collection = self.chroma_client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )
        self._index_bank()

    def _entry_docs(self, entry: Dict[str, Any]):
        """Yield (id, document, metadata) for one bank training entry."""
        import json
        content = entry["content"]
        pieces = [content] if len(content) <= 2200 else self.text_splitter.split_text(content)
        for i, piece in enumerate(pieces):
            yield (
                f"{entry['id']}_{i}",
                piece,
                {
                    "training_id": entry["id"],
                    "domain": entry.get("domain", ""),
                    "title": entry.get("title", ""),
                    # Chroma metadata values must be scalars → serialize the objectives list.
                    "objectives": json.dumps(entry.get("objectives", []), ensure_ascii=False),
                    "chunk_index": i,
                    "total_chunks": len(pieces),
                },
            )

    def _add_docs(self, ids, docs, metas):
        if not docs:
            return
        embeddings = self.embeddings.embed_documents(docs)
        for start in range(0, len(docs), CHROMA_ADD_BATCH):
            end = start + CHROMA_ADD_BATCH
            self.collection.add(
                documents=docs[start:end],
                embeddings=embeddings[start:end],
                metadatas=metas[start:end],
                ids=ids[start:end],
            )

    def _index_bank(self):
        entries = repo.list_bank_trainings()
        all_ids: List[str] = []
        all_docs: List[str] = []
        all_metas: List[Dict[str, Any]] = []
        for entry in entries:
            for _id, doc, meta in self._entry_docs(entry):
                all_ids.append(_id)
                all_docs.append(doc)
                all_metas.append(meta)
        if not all_docs:
            print("⚠️ No bank trainings to index")
            return
        print(f"🔄 Embedding {len(all_docs)} bank chunks ({len(entries)} trainings)...")
        self._add_docs(all_ids, all_docs, all_metas)
        print(f"✅ Indexed {len(all_docs)} bank chunks")

    def add_training(self, entry: Dict[str, Any]):
        """Incrementally index a single new bank training (id/title/domain/objectives/content)."""
        ids, docs, metas = [], [], []
        for _id, doc, meta in self._entry_docs(entry):
            ids.append(_id); docs.append(doc); metas.append(meta)
        self._add_docs(ids, docs, metas)

    # ------------------------------------------------------------------ retrieval

    def retrieve(self, query: str, top_k: int = 6) -> List[Dict[str, Any]]:
        """Retrieve the top-k most relevant bank chunks for a query."""
        query_embedding = self.embeddings.embed_query(query)
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )

        import json
        chunks: List[Dict[str, Any]] = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                metadata = results["metadatas"][0][i] if results.get("metadatas") else {}
                distance = results["distances"][0][i] if results.get("distances") else 0
                try:
                    objectives = json.loads(metadata.get("objectives", "[]"))
                except Exception:
                    objectives = metadata.get("objectives", "")
                chunks.append({
                    "content": doc,
                    "training_id": metadata.get("training_id", "unknown"),
                    "domain": metadata.get("domain", "unknown"),
                    "title": metadata.get("title", "Unknown"),
                    "objectives": objectives,
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
    """Ensure the bank vector store is built (indexes once if empty). Safe to call often."""
    return get_bank_rag()


def reindex_bank() -> BankRAGModule:
    """Force a full rebuild of the bank vector store from the DB. Call after seeding."""
    bank = get_bank_rag()
    bank.reindex()
    return bank
