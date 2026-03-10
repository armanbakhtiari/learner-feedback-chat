"""
Agentic RAG Module

This module implements a sophisticated RAG (Retrieval-Augmented Generation) system
with ranking and query rewriting capabilities.

Architecture:
1. Retriever: Finds top 10 most relevant chunks from the document store
2. Ranking Agent: Evaluates if retrieved chunks can answer the query
3. Rewrite Agent: Improves the query if chunks are not relevant enough
4. Retry Logic: Up to 3 attempts to find relevant information

This module is domain-agnostic and can be used with any set of documents.
Supports multiple document folders (e.g., Docs_migraine, Docs_nursing) with
separate ChromaDB collections per training type.
"""

import os
import json
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from pydantic import BaseModel, Field
from langchain_openai import OpenAIEmbeddings
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document


# =============================================================================
# Pydantic Models for Structured Agent Outputs
# =============================================================================

class RankingResult(BaseModel):
    """Structured output for the Ranking Agent."""
    is_relevant: bool = Field(
        description="Whether the retrieved chunks contain relevant information to answer the query"
    )
    reasoning: str = Field(
        description="Brief explanation of the relevance decision"
    )


class RewrittenQuery(BaseModel):
    """Structured output for the Rewrite Agent."""
    query: str = Field(
        description="The rewritten search query optimized for better document retrieval"
    )


# Base paths
ROOT_DIR = Path(__file__).parent.parent
CHROMA_PERSIST_DIR = ROOT_DIR / ".chroma_db"

# Mapping of training types to document folders
TRAINING_DOCS_MAP = {
    "migraine": ROOT_DIR / "Docs_migraine",
    "nursing_1st": ROOT_DIR / "Docs_nursing",
    "nursing_2nd": ROOT_DIR / "Docs_nursing",
}


class AgenticRAGModule:
    """
    Agentic RAG module with ranking and query rewriting capabilities.

    Supports multiple document folders with separate ChromaDB collections
    per training type. Each training type indexes from its own docs folder.
    """

    def __init__(self, training_type: str = "migraine"):
        self.training_type = training_type
        self.docs_path = TRAINING_DOCS_MAP.get(training_type, TRAINING_DOCS_MAP["migraine"])
        self.collection_name = f"knowledge_base_{training_type}"
        # For nursing types, they share the same docs, so share the collection
        if training_type in ("nursing_1st", "nursing_2nd"):
            self.collection_name = "knowledge_base_nursing"

        self.embeddings = OpenAIEmbeddings(
            model="text-embedding-3-small",
            openai_api_key=os.getenv("OPENAI_API_KEY")
        )

        # Initialize base LLMs
        base_ranking_llm = ChatAnthropic(
            model="claude-sonnet-4-5",
            temperature=0.1,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
        )

        base_rewrite_llm = ChatAnthropic(
            model="claude-sonnet-4-5",
            temperature=0.3,
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY")
        )

        # Create structured output LLMs with Pydantic models
        self.ranking_llm = base_ranking_llm.with_structured_output(RankingResult)
        self.rewrite_llm = base_rewrite_llm.with_structured_output(RewrittenQuery)

        # Ensure persist directory exists
        CHROMA_PERSIST_DIR.mkdir(parents=True, exist_ok=True)

        # Initialize ChromaDB with persistent storage (lazy import to avoid numpy at module level)
        import chromadb
        from chromadb.config import Settings
        self.chroma_client = chromadb.PersistentClient(
            path=str(CHROMA_PERSIST_DIR),
            settings=Settings(anonymized_telemetry=False)
        )

        # Get or create collection for this training type
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

        # Text splitter configuration
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=2000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

        # Hash file per collection
        self.docs_hash_file = CHROMA_PERSIST_DIR / f".docs_hash_{self.collection_name}"

        # Initialize document store if needed (with change detection)
        self._ensure_documents_indexed()

    def _compute_docs_hash(self) -> str:
        """Compute a hash of all documents to detect changes"""
        if not self.docs_path.exists():
            return ""

        hasher = hashlib.md5()

        # Sort files for consistent ordering
        pdf_files = sorted(self.docs_path.glob("*.pdf"))

        for pdf_file in pdf_files:
            # Hash filename and file size (quick change detection)
            hasher.update(pdf_file.name.encode())
            hasher.update(str(pdf_file.stat().st_size).encode())
            hasher.update(str(pdf_file.stat().st_mtime).encode())

        return hasher.hexdigest()

    def _get_stored_hash(self) -> str:
        """Get the stored hash of previously indexed documents"""
        if self.docs_hash_file.exists():
            return self.docs_hash_file.read_text().strip()
        return ""

    def _save_hash(self, hash_value: str):
        """Save the current documents hash"""
        self.docs_hash_file.write_text(hash_value)

    def _ensure_documents_indexed(self):
        """Check if documents are indexed and up-to-date."""
        current_hash = self._compute_docs_hash()
        stored_hash = self._get_stored_hash()
        doc_count = self.collection.count()

        # Case 1: No documents in store - need to index
        if doc_count == 0:
            print(f"📚 [{self.collection_name}] No documents in vector store. Indexing documents...")
            self._index_documents()
            self._save_hash(current_hash)
            return

        # Case 2: Documents exist but hash changed - re-index
        if current_hash != stored_hash:
            print(f"📚 [{self.collection_name}] Documents have changed. Re-indexing...")
            self._clear_and_reindex()
            self._save_hash(current_hash)
            return

        # Case 3: Documents exist and hash matches - use cached
        print(f"📚 [{self.collection_name}] Using cached vector store ({doc_count} chunks)")

    def _clear_and_reindex(self):
        """Clear existing documents and re-index"""
        try:
            # Delete and recreate collection
            self.chroma_client.delete_collection(self.collection_name)
            self.collection = self.chroma_client.create_collection(
                name=self.collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            self._index_documents()
        except Exception as e:
            print(f"⚠️ Error during re-indexing: {e}")
            # Try to index anyway
            self._index_documents()

    def _index_documents(self):
        """Load and index all PDF documents from the docs folder"""
        if not self.docs_path.exists():
            print(f"⚠️ Documents folder not found: {self.docs_path}")
            return

        all_chunks = []
        all_metadatas = []
        all_ids = []

        # Process each PDF file
        for pdf_file in self.docs_path.glob("*.pdf"):
            print(f"📄 Processing: {pdf_file.name}")

            try:
                # Load PDF - PyMuPDFLoader provides page numbers in metadata
                from langchain_community.document_loaders import PyMuPDFLoader
                loader = PyMuPDFLoader(str(pdf_file))
                documents = loader.load()

                # Split into chunks while preserving page info
                chunks = self.text_splitter.split_documents(documents)

                # Add metadata and prepare for indexing
                for i, chunk in enumerate(chunks):
                    chunk_id = f"{pdf_file.stem}_{i}"

                    # Get page number from the original document metadata
                    original_page = chunk.metadata.get('page', 0)
                    page_number = original_page + 1 if isinstance(original_page, int) else 1

                    # Create clean document title from filename
                    doc_title = pdf_file.stem.replace("_", " ").replace("-", " ").strip()

                    metadata = {
                        "source": pdf_file.name,
                        "document_title": doc_title,
                        "page_number": page_number,
                        "chunk_index": i,
                        "total_chunks": len(chunks)
                    }

                    all_chunks.append(chunk.page_content)
                    all_metadatas.append(metadata)
                    all_ids.append(chunk_id)

                print(f"   ✅ Created {len(chunks)} chunks from {pdf_file.name}")

            except Exception as e:
                print(f"   ❌ Error processing {pdf_file.name}: {e}")
                continue

        if all_chunks:
            print(f"\n🔄 Generating embeddings for {len(all_chunks)} chunks...")

            # Generate embeddings
            embeddings = self.embeddings.embed_documents(all_chunks)

            # Add to ChromaDB
            self.collection.add(
                documents=all_chunks,
                embeddings=embeddings,
                metadatas=all_metadatas,
                ids=all_ids
            )

            print(f"✅ Successfully indexed {len(all_chunks)} chunks")
        else:
            print("⚠️ No chunks to index")

    def retrieve(self, query: str, top_k: int = 10) -> List[Dict[str, Any]]:
        """Retrieve the top-k most relevant chunks for a query."""
        # Generate query embedding
        query_embedding = self.embeddings.embed_query(query)

        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"]
        )

        # Format results
        chunks = []
        if results and results.get("documents"):
            for i, doc in enumerate(results["documents"][0]):
                chunk = {
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results.get("metadatas") else {},
                    "distance": results["distances"][0][i] if results.get("distances") else 0,
                    "relevance_score": 1 - results["distances"][0][i] if results.get("distances") else 1
                }
                chunks.append(chunk)

        return chunks

    def rank_chunks(self, query: str, chunks: List[Dict[str, Any]]) -> Tuple[bool, str]:
        """Ranking Agent: Evaluate if the retrieved chunks contain relevant information."""
        # Format chunks for the ranking agent
        chunks_text = "\n\n---\n\n".join([
            f"**Source: {chunk['metadata'].get('source', 'Unknown')}**\n{chunk['content']}"
            for chunk in chunks
        ])

        ranking_prompt = """You are a Ranking Agent that evaluates whether retrieved document chunks can answer a user's query.

Your task:
1. Analyze the query and the retrieved chunks
2. Determine if the chunks contain SUFFICIENT and RELEVANT information to answer the query
3. Be strict but fair - the chunks don't need to answer everything perfectly, but should provide meaningful information

You are domain-agnostic and can evaluate documents from any field (education, science, business, healthcare, etc.).

IMPORTANT:
- Set is_relevant=true if the chunks contain at least some useful information to address the query
- Set is_relevant=false ONLY if the chunks are completely unrelated or insufficient
- Consider that partial information is better than no information
- Provide a brief reasoning explaining your decision"""

        messages = [
            SystemMessage(content=ranking_prompt),
            HumanMessage(content=f"""
**User Query:** {query}

**Retrieved Chunks:**
{chunks_text}

Evaluate whether these chunks can help answer the user's query.
""")
        ]

        try:
            result: RankingResult = self.ranking_llm.invoke(messages)
            return result.is_relevant, result.reasoning

        except Exception as e:
            print(f"❌ Ranking agent error: {e}")
            return True, f"Ranking error: {e}"

    def rewrite_query(self, original_query: str, user_message: str, attempt: int) -> str:
        """Rewrite Agent: Improve the query to find more relevant chunks."""
        rewrite_prompt = f"""You are a Query Rewriting Agent. Your task is to reformulate a search query to find more relevant documents from a knowledge base.

The current query didn't retrieve relevant information from the document database. You need to rewrite it to be more effective.

This is attempt {attempt} of 3. Previous query failed to find relevant content.

Guidelines for rewriting:
1. Use different terminology or synonyms relevant to the domain
2. Make the query more specific or more general (depending on what might help)
3. Focus on key concepts and terminology
4. Consider alternative phrasings
5. Use terms that would likely appear in professional documents, guidelines, or reference materials"""

        messages = [
            SystemMessage(content=rewrite_prompt),
            HumanMessage(content=f"""
**Original User Message:** {user_message}

**Current Query (that didn't work):** {original_query}

Provide a better query to search the document database.""")
        ]

        try:
            result: RewrittenQuery = self.rewrite_llm.invoke(messages)
            return result.query

        except Exception as e:
            print(f"❌ Rewrite agent error: {e}")
            return f"{original_query} guidelines recommendations"

    def search(self, query: str, user_message: str = None, max_retries: int = 3) -> Dict[str, Any]:
        """
        Main RAG search with ranking and query rewriting.

        Returns a dictionary that includes 'found_relevant' to indicate whether
        relevant content was found after all attempts. When found_relevant=False
        after max_retries, callers should suggest web search to the user.
        """
        if user_message is None:
            user_message = query

        query_history = [query]
        current_query = query
        best_chunks = []
        best_relevance = False

        print(f"\n{'='*60}")
        print(f"🔍 AGENTIC RAG [{self.collection_name}]: Starting search")
        print(f"   Query: {query[:80]}...")
        print(f"{'='*60}")

        for attempt in range(1, max_retries + 1):
            print(f"\n📌 Attempt {attempt}/{max_retries}")
            print(f"   Current query: {current_query[:60]}...")

            # Step 1: Retrieve chunks
            chunks = self.retrieve(current_query, top_k=10)

            if not chunks:
                print(f"   ⚠️ No chunks retrieved")
                if attempt < max_retries:
                    current_query = self.rewrite_query(current_query, user_message, attempt)
                    query_history.append(current_query)
                continue

            print(f"   📚 Retrieved {len(chunks)} chunks")

            # Step 2: Rank chunks
            is_relevant, reasoning = self.rank_chunks(current_query, chunks)

            print(f"   🎯 Ranking result: {'✅ Relevant' if is_relevant else '❌ Not relevant'}")
            print(f"   💭 Reasoning: {reasoning[:80]}...")

            # Store best results
            if is_relevant or not best_chunks:
                best_chunks = chunks
                best_relevance = is_relevant

            if is_relevant:
                # Found relevant content, return it
                break

            # Step 3: Rewrite query if not relevant and not last attempt
            if attempt < max_retries:
                current_query = self.rewrite_query(current_query, user_message, attempt)
                query_history.append(current_query)
                print(f"   🔄 Rewritten query: {current_query[:60]}...")

        # Prepare final result
        if best_chunks:
            sources = list(set([
                chunk["metadata"].get("source", "Unknown")
                for chunk in best_chunks
            ]))

            formatted_chunks = []
            for chunk in best_chunks:
                formatted_chunks.append({
                    "content": chunk["content"],
                    "source": chunk["metadata"].get("source", "Unknown"),
                    "document_title": chunk["metadata"].get("document_title", "Unknown"),
                    "page_number": chunk["metadata"].get("page_number", 1),
                    "relevance_score": chunk.get("relevance_score", 0)
                })

            print(f"\n✅ RAG search completed")
            print(f"   Attempts: {len(query_history)}")
            print(f"   Sources: {sources}")
            print(f"   Relevant: {best_relevance}")

            return {
                "status": "success",
                "chunks": formatted_chunks,
                "sources": sources,
                "query_history": query_history,
                "attempts": len(query_history),
                "found_relevant": best_relevance
            }
        else:
            print(f"\n❌ RAG search failed - no chunks found")
            return {
                "status": "no_relevant_info",
                "error": "No relevant documents found after all attempts",
                "query_history": query_history,
                "attempts": len(query_history),
                "found_relevant": False
            }

    def format_chunks_for_context(self, chunks: List[Dict[str, Any]]) -> str:
        """Format retrieved chunks into a context string for the LLM."""
        if not chunks:
            return "No relevant documents found."

        formatted_parts = []

        # Group chunks by source
        chunks_by_source = {}
        for chunk in chunks:
            source = chunk.get("source", "Unknown")
            if source not in chunks_by_source:
                chunks_by_source[source] = []
            chunks_by_source[source].append(chunk)

        for source, source_chunks in chunks_by_source.items():
            doc_title = source_chunks[0].get("document_title", source)
            formatted_parts.append(f"\n### Source: {doc_title}\n")
            for chunk in source_chunks:
                page_num = chunk.get("page_number", "N/A")
                formatted_parts.append(f"[Page {page_num}]")
                formatted_parts.append(chunk["content"])
                formatted_parts.append("\n---\n")

        return "\n".join(formatted_parts)

    def reindex_documents(self):
        """Force reindexing of all documents"""
        print("🔄 Reindexing documents...")

        try:
            self.chroma_client.delete_collection(self.collection_name)
        except Exception:
            pass

        self.collection = self.chroma_client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )

        self._index_documents()
        self._save_hash(self._compute_docs_hash())


# Global instances per training type
_rag_module_instances: Dict[str, AgenticRAGModule] = {}


def get_rag_module(training_type: str = "migraine") -> AgenticRAGModule:
    """Get or create the RAG module instance for a training type"""
    global _rag_module_instances
    if training_type not in _rag_module_instances:
        _rag_module_instances[training_type] = AgenticRAGModule(training_type)
    return _rag_module_instances[training_type]


def search_documents(query: str, user_message: str = None, training_type: str = "migraine") -> Dict[str, Any]:
    """
    Search the document database using the agentic RAG module.

    Args:
        query: The search query (formulated for document retrieval)
        user_message: The original user message for context
        training_type: Which training's documents to search

    Returns:
        Dictionary with search results and metadata
    """
    rag_module = get_rag_module(training_type)
    return rag_module.search(query, user_message)
