"""
"Suggest New Trainings" Pipeline
================================

Given a learner's stored learning gaps, recommend 1–3 situations from the bank of situations
for further practice. The pipeline uses two structured-output agents:

  1. Query Agent (``generate_gap_query``): reads the learning gaps and produces a single
     retrieval query.
  2. Retriever: the query is run against the bank vector store (``backend/bank_rag.py``) to
     fetch the most relevant situation chunks.
  3. Suggestion Agent (``suggest_trainings``): given the gaps + retrieved situations, selects
     1–3 situations and explains how each addresses the learner's gaps.

Both agents use ``with_structured_output`` (Pydantic), matching the rest of the codebase.
"""

import os
import sys
import json
from pathlib import Path
from typing import Any, Dict, List

from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_anthropic import ChatAnthropic

sys.path.append(str(Path(__file__).parent.parent))

from bank_situations import get_bank_situation
from backend.bank_rag import ensure_bank_indexed
from backend.session_store import get_learning_gaps
from backend.llm_retry import invoke_with_retry


# =============================================================================
# Structured output models
# =============================================================================

class GapQuery(BaseModel):
    """Structured output for the Query Agent."""
    query: str = Field(
        description="A single retrieval query, in French, that captures the themes of the "
                    "learner's gaps to find relevant practice situations."
    )
    reasoning: str = Field(
        description="One-sentence explanation of why this query targets the learner's gaps."
    )


class TrainingSuggestion(BaseModel):
    """A single suggested situation for further training."""
    situation_id: str = Field(description="The id of the suggested bank situation")
    title: str = Field(description="The title of the suggested situation")
    domain: str = Field(description="The domain of the situation (e.g. 'migraine', 'grh')")
    rationale: str = Field(
        description="French explanation of how this situation addresses the learner's gaps"
    )


class SuggestionResult(BaseModel):
    """Structured output for the Suggestion Agent (1 to 3 suggestions)."""
    suggestions: List[TrainingSuggestion] = Field(
        description="Between 1 and 3 suggested situations, most relevant first"
    )


# =============================================================================
# Agents
# =============================================================================

def _llm(temperature: float = 0.3) -> ChatAnthropic:
    return ChatAnthropic(
        model="claude-sonnet-4-6",
        temperature=temperature,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    )


QUERY_AGENT_PROMPT = """You are a Query Agent for an educational recommendation system.
You are given a learner's LEARNING GAPS (per learning objective, with justifications).
Produce ONE concise retrieval query (in French) that captures the underlying themes/skills of
these gaps, so a semantic search can find practice SITUATIONS that would help close them.
Focus on the transferable skills and themes (e.g. "rétroaction constructive", "gestion de la
performance", "éthique et gradation des sanctions"), not on a specific patient/employee name."""


def generate_gap_query(gaps: List[Dict[str, Any]]) -> GapQuery:
    """Query Agent: turn the learning gaps into a single retrieval query."""
    structured = _llm(0.3).with_structured_output(GapQuery)
    messages = [
        SystemMessage(content=QUERY_AGENT_PROMPT),
        HumanMessage(content=f"""Learning gaps (JSON):
{json.dumps(gaps, indent=2, ensure_ascii=False)}

Produce a single French retrieval query that targets these gaps."""),
    ]
    return invoke_with_retry(structured.invoke, messages)


SUGGESTION_AGENT_PROMPT = """You are a Suggestion Agent for an educational recommendation system.
You are given:
1. A learner's LEARNING GAPS (per learning objective, with justifications).
2. A set of candidate SITUATIONS retrieved from a bank (each has an id, title, domain, learning
   objectives, and content).

Select the 1 to 3 situations that would best help the learner close their gaps, most relevant
first. You MUST only choose from the provided candidate situations and MUST use their exact
``situation_id`` and ``title``. For each chosen situation, write a French ``rationale`` that
explicitly links the situation to the learner's specific gaps.

Rules:
- Choose at least 1 and at most 3 situations.
- Never invent a situation_id that is not in the candidates.
- Prefer variety only if it serves the gaps; relevance to the gaps comes first.
- Output French for the rationale."""


def suggest_trainings(gaps: List[Dict[str, Any]], retrieved_chunks: List[Dict[str, Any]]) -> SuggestionResult:
    """Suggestion Agent: pick 1–3 situations from the retrieved candidates."""
    # Deduplicate candidate situations (a situation may appear via multiple chunks).
    candidates: Dict[str, Dict[str, Any]] = {}
    for chunk in retrieved_chunks:
        sid = chunk.get("situation_id")
        if not sid or sid in candidates:
            continue
        candidates[sid] = {
            "situation_id": sid,
            "title": chunk.get("title", ""),
            "domain": chunk.get("domain", ""),
            "objectives": chunk.get("objectives", ""),
            "content": chunk.get("content", ""),
        }

    candidates_text = "\n\n---\n\n".join(
        f"situation_id: {c['situation_id']}\ntitle: {c['title']}\ndomain: {c['domain']}\n"
        f"objectives: {c['objectives']}\ncontent:\n{c['content']}"
        for c in candidates.values()
    )

    structured = _llm(0.4).with_structured_output(SuggestionResult)
    messages = [
        SystemMessage(content=SUGGESTION_AGENT_PROMPT),
        HumanMessage(content=f"""Learning gaps (JSON):
{json.dumps(gaps, indent=2, ensure_ascii=False)}

Candidate situations:
{candidates_text}

Select 1 to 3 situations that best address the learner's gaps."""),
    ]
    result: SuggestionResult = invoke_with_retry(structured.invoke, messages)

    # Validate ids against the bank and backfill canonical title/domain to avoid drift.
    valid: List[TrainingSuggestion] = []
    for s in result.suggestions:
        entry = get_bank_situation(s.situation_id)
        if not entry:
            continue
        valid.append(TrainingSuggestion(
            situation_id=s.situation_id,
            title=entry["title"],
            domain=entry["domain"],
            rationale=s.rationale,
        ))
    # If validation dropped everything, fall back to the top retrieved candidates.
    if not valid:
        for c in list(candidates.values())[:3]:
            valid.append(TrainingSuggestion(
                situation_id=c["situation_id"],
                title=c["title"],
                domain=c["domain"],
                rationale="Situation pertinente identifiée par la recherche dans la banque de situations.",
            ))
    return SuggestionResult(suggestions=valid[:3])


# =============================================================================
# Orchestrator
# =============================================================================

def suggest_new_trainings(session_id: str) -> Dict[str, Any]:
    """End-to-end: load gaps → query → retrieve from bank → suggest 1–3 situations.

    Returns a dict ready to serialize to the frontend, or ``{"status": "no_gaps", ...}`` when
    the session has no stored learning gaps.
    """
    gaps_payload = get_learning_gaps(session_id)
    gaps = (gaps_payload or {}).get("gaps", []) if gaps_payload else []

    if not gaps:
        return {
            "status": "no_gaps",
            "message": "Aucune lacune d'apprentissage n'a été identifiée pour cette session.",
            "suggestions": [],
        }

    bank_rag = ensure_bank_indexed()

    gap_query = generate_gap_query(gaps)
    print(f"🔎 Gap query: {gap_query.query}")

    retrieved = bank_rag.retrieve(gap_query.query, top_k=6)
    print(f"   Retrieved {len(retrieved)} bank chunks")

    result = suggest_trainings(gaps, retrieved)

    return {
        "status": "success",
        "query": gap_query.query,
        "query_reasoning": gap_query.reasoning,
        "suggestions": [s.model_dump() for s in result.suggestions],
        "gaps": gaps,
    }
