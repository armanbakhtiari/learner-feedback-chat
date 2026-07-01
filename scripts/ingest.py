#!/usr/bin/env python3
"""
Offline Chroma ingestion script.

Run this ONCE locally to populate the vector store (Chroma Cloud in production, or the
local .chroma_db store in development) with:
  - one knowledge-base collection per training type that has PDF documents
    (knowledge_base_migraine, knowledge_base_nursing, ...)
  - the bank-of-situations collection (bank_situations)

The deployed backend never indexes; it only queries these collections. Re-run this
script whenever the source PDFs or the bank of situations change.

Usage:
    pip install -r requirements.txt
    python scripts/ingest.py

Required env vars (read from .env or the environment):
    OPENAI_API_KEY                          (embeddings)
    CHROMA_API_KEY, CHROMA_TENANT, CHROMA_DATABASE   (Chroma Cloud; omit for local dev)
"""

import os
import sys
from pathlib import Path

# Make the project root importable so `backend.*` and `bank_situations` resolve.
ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from dotenv import load_dotenv

load_dotenv()


def _check_env():
    missing = [v for v in ("OPENAI_API_KEY",) if not os.getenv(v)]
    if missing:
        print(f"❌ Missing required env var(s): {', '.join(missing)}")
        sys.exit(1)

    from backend.chroma_client import using_chroma_cloud

    if using_chroma_cloud():
        cloud_missing = [v for v in ("CHROMA_TENANT", "CHROMA_DATABASE") if not os.getenv(v)]
        if cloud_missing:
            print(f"❌ CHROMA_API_KEY is set but missing: {', '.join(cloud_missing)}")
            sys.exit(1)
        print("☁️  Target: Chroma Cloud")
    else:
        print("💾 Target: local .chroma_db (CHROMA_API_KEY not set)")


def ingest_knowledge_bases():
    """Index PDF documents for every training type that has a docs folder with PDFs."""
    from backend.rag_tool import AgenticRAGModule, TRAINING_DOCS_MAP, _has_documents

    # Dedup collections (e.g. nursing_1st and nursing_2nd share one collection).
    done_collections = set()
    summary = []

    for training_type in TRAINING_DOCS_MAP:
        if not _has_documents(training_type):
            print(f"⏭️  [{training_type}] no PDFs found, skipping")
            continue

        module = AgenticRAGModule(training_type, index=False)
        if module.collection_name in done_collections:
            print(f"⏭️  [{training_type}] collection '{module.collection_name}' already built")
            continue

        print(f"\n=== Ingesting '{module.collection_name}' (training_type={training_type}) ===")
        module.reindex_documents()
        done_collections.add(module.collection_name)
        summary.append((module.collection_name, module.collection.count()))

    return summary


def ingest_bank():
    """Index the bank of situations."""
    from backend.bank_rag import BankRAGModule

    print("\n=== Ingesting 'bank_situations' ===")
    module = BankRAGModule(index=True)
    return [(module.collection_name, module.collection.count())]


def main():
    _check_env()

    summary = []
    summary += ingest_knowledge_bases()
    summary += ingest_bank()

    print("\n" + "=" * 50)
    print("✅ Ingestion complete. Collections:")
    for name, count in summary:
        print(f"   - {name}: {count} chunks")
    print("=" * 50)


if __name__ == "__main__":
    main()
