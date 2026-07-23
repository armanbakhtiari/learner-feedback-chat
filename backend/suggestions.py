"""
"Suggest New Trainings" — DB-backed, vector-retrieval pipeline.

Path 1 (bank): recommend 1–3 existing bank trainings (origin seed_bank / suggested_bank)
for the learner's gaps, using the scaling-friendly agentic retrieval flow:
  1. Query Agent   — turn the learner's gap profile into a retrieval query.
  2. Retriever     — query the bank vector store (backend/bank_rag.py) for candidate trainings.
  3. Suggestion Agent — pick the 1–3 best candidates and explain how each closes a gap.

Path 2 (generate): for a completed training the user selects, generate brand-new
Learning-by-Concordance scenarios for that training's situation(s), targeting the user's
gaps (reuses backend/scenario_generator.py). Persisting a generated set as a completable
training is handled by the endpoint layer.
"""

import os
from typing import Any, Dict, List

from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_anthropic import ChatAnthropic

from backend.llm_retry import invoke_with_retry
from backend.bank_rag import ensure_bank_indexed
from backend.db import repo


# ------------------------------------------------------------------ models
class _GapQuery(BaseModel):
    query: str = Field(description="A single French retrieval query capturing the learner's gap themes")


class _Suggestion(BaseModel):
    training_id: str = Field(description="The id of a retrieved candidate bank training (verbatim)")
    rationale: str = Field(description="French explanation of how this training addresses the learner's gaps")


class _SuggestionResult(BaseModel):
    suggestions: List[_Suggestion] = Field(description="Between 1 and 3 suggestions, most relevant first")


def _llm(temp: float = 0.3) -> ChatAnthropic:
    return ChatAnthropic(model="claude-sonnet-4-6", temperature=temp,
                         anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"))


QUERY_PROMPT = """Tu es un agent de requête pour un système de recommandation pédagogique.
On te donne le PROFIL DE LACUNES d'un apprenant. Produis UNE requête concise (en français)
qui capte les thèmes/compétences sous-jacents de ces lacunes, afin qu'une recherche
sémantique trouve des SITUATIONS d'entraînement pertinentes. Concentre-toi sur les
compétences transférables, pas sur un nom de patient précis."""

SUGGESTION_PROMPT = """Tu es un agent de recommandation pédagogique.
On te donne : (1) le PROFIL DE LACUNES de l'apprenant, (2) des FORMATIONS candidates
récupérées de la banque (chacune avec un training_id, un titre, ses objectifs et son contenu).
Choisis 1 à 3 formations qui aideraient le mieux l'apprenant à combler ses lacunes, la plus
pertinente d'abord. Utilise UNIQUEMENT les training_id fournis (jamais inventés). Pour chaque
choix, écris un `rationale` en français reliant explicitement la formation aux lacunes."""


def _generate_query(gap_content: str) -> str:
    structured = _llm(0.3).with_structured_output(_GapQuery)
    result: _GapQuery = invoke_with_retry(
        structured.invoke,
        [SystemMessage(content=QUERY_PROMPT), HumanMessage(content=f"PROFIL DE LACUNES:\n{gap_content}")],
    )
    return result.query


def suggest_bank_trainings(user_id: str, gap_content: str) -> Dict[str, Any]:
    """Path 1: gap profile → query → vector retrieve → pick 1–3 bank trainings."""
    bank = ensure_bank_indexed()

    # Trainings the user already has (assigned/completed) are filtered out of results.
    sb = repo.get_supabase()
    assigned = sb.table("user_trainings").select("training_id").eq("user_id", user_id).execute().data
    assigned_ids = {a["training_id"] for a in assigned}

    if not (gap_content or "").strip():
        query = "situations d'entraînement pour approfondir les compétences cliniques"
    else:
        query = _generate_query(gap_content)

    retrieved = bank.retrieve(query, top_k=8)

    # Deduplicate by training_id and drop already-assigned trainings.
    candidates: Dict[str, Dict[str, Any]] = {}
    for chunk in retrieved:
        tid = chunk.get("training_id")
        if not tid or tid == "unknown" or tid in candidates or tid in assigned_ids:
            continue
        if not repo.get_training(tid):  # skip stale/foreign vector-store entries
            continue
        candidates[tid] = chunk
    if not candidates:
        return {"status": "no_candidates", "query": query, "suggestions": [],
                "message": "Aucune formation supplémentaire pertinente n'a été trouvée pour le moment."}

    candidates_text = "\n\n---\n\n".join(
        f"training_id: {tid}\ntitle: {c['title']}\nobjectives: {c['objectives']}\ncontent:\n{c['content']}"
        for tid, c in candidates.items()
    )
    structured = _llm(0.4).with_structured_output(_SuggestionResult)
    result: _SuggestionResult = invoke_with_retry(
        structured.invoke,
        [SystemMessage(content=SUGGESTION_PROMPT),
         HumanMessage(content=f"PROFIL DE LACUNES:\n{gap_content or '(vide)'}\n\nFORMATIONS candidates:\n{candidates_text}\n\nChoisis 1 à 3 formations.")],
    )

    suggestions = []
    for s in result.suggestions:
        tr = repo.get_training(s.training_id)
        if not tr or s.training_id in assigned_ids:
            continue
        suggestions.append({"training_id": tr["id"], "title": tr["title"],
                            "objectives": tr.get("learning_objectives", []), "rationale": s.rationale})
    if not suggestions:  # fallback to top retrieved
        for tid, c in list(candidates.items())[:3]:
            suggestions.append({"training_id": tid, "title": c["title"],
                                "objectives": c["objectives"],
                                "rationale": "Formation pertinente identifiée par la recherche dans la banque."})
    return {"status": "success", "query": query, "suggestions": suggestions[:3]}
