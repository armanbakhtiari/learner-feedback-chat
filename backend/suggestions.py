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


QUERY_PROMPT = """You are a query agent for an educational recommendation system.
You are given a learner's LEARNING-GAP PROFILE. Produce ONE concise retrieval query
(written in French) capturing the underlying themes/skills of these gaps, so a semantic
search can find relevant practice SITUATIONS. Focus on transferable skills, not on a specific
patient name.
If a LEARNER REQUEST is also provided, it takes priority: steer the query toward the subject
the learner explicitly asked for, while still reflecting their gaps. If no LEARNER REQUEST is
given, build the query from the gap profile alone."""

SUGGESTION_PROMPT = """You are an educational recommendation agent.
You are given: (1) the learner's LEARNING-GAP PROFILE, (2) candidate TRAININGS retrieved from
the bank (each with a training_id, title, objectives, and content).
Choose 1 to 3 trainings that would best help the learner close their gaps, most relevant first.
Only keep a candidate whose subject area is consistent with the learner's demonstrated area of
practice — unless the learner has explicitly requested another subject, in which case honour
that request. Discard candidates belonging to an unrelated field that neither the learner's
profile nor their request points to, even if the wording looks superficially similar; it is
better to return fewer trainings than an off-topic one.
Use ONLY the provided training_ids (never invent one). For each choice, write a `rationale`
**in French** explicitly linking the training to the learner's gaps."""


def _empty_message(all_excluded: bool, preference: str = "") -> str:
    """Explain *why* there is nothing to suggest — the two reasons are very different."""
    if preference:
        return ("Aucune formation correspondant à votre demande n'est disponible pour le moment. "
                "Essayez une autre formulation ou laissez le champ vide pour des suggestions "
                "basées sur votre profil.")
    if all_excluded:
        return ("Vous avez déjà toutes les formations pertinentes de la banque, soit dans votre "
                "tableau de bord, soit parmi vos formations complétées. De nouvelles formations "
                "pourront vous être proposées lorsque la banque s'enrichira.")
    return "Aucune formation supplémentaire pertinente n'a été trouvée pour le moment."


def _generate_query(gap_content: str, preference: str = "") -> str:
    human = f"LEARNING-GAP PROFILE:\n{gap_content}"
    if preference:
        human += f"\n\nLEARNER REQUEST:\n{preference}"
    structured = _llm(0.3).with_structured_output(_GapQuery)
    result: _GapQuery = invoke_with_retry(
        structured.invoke,
        [SystemMessage(content=QUERY_PROMPT), HumanMessage(content=human)],
    )
    return result.query


def suggest_bank_trainings(user_id: str, gap_content: str, preference: str = "") -> Dict[str, Any]:
    """
    Path 1: gap profile → query → vector retrieve → pick 1–3 bank trainings.

    ``preference`` is the learner's optional free-text wish ("je voudrais des formations
    sur la migraine"). When empty, this behaves exactly as it did before it existed.
    """
    bank = ensure_bank_indexed()
    preference = (preference or "").strip()

    # Trainings the user already has (on the dashboard OR completed) are filtered out of
    # results. Nothing is removed from the vector store — the bank is shared, so the
    # exclusion is per-user and happens after retrieval.
    sb = repo.get_supabase()
    assigned = sb.table("user_trainings").select("training_id").eq("user_id", user_id).execute().data
    assigned_ids = {a["training_id"] for a in assigned}

    if not (gap_content or "").strip() and not preference:
        query = "situations d'entraînement pour approfondir les compétences cliniques"
    else:
        query = _generate_query(gap_content, preference)

    # Retrieve well beyond the 1-3 we need: the per-user exclusion below runs afterwards,
    # so a learner who has already taken several trainings would otherwise be left with
    # nothing to choose from.
    retrieved = bank.retrieve(query, top_k=24)

    # Deduplicate by training_id and drop already-assigned trainings.
    candidates: Dict[str, Dict[str, Any]] = {}
    excluded = 0
    for chunk in retrieved:
        tid = chunk.get("training_id")
        if not tid or tid == "unknown" or tid in candidates:
            continue
        if not repo.get_training(tid):  # skip stale/foreign vector-store entries
            continue
        if tid in assigned_ids:
            excluded += 1
            continue
        candidates[tid] = chunk
    if not candidates:
        return {"status": "exhausted" if excluded else "no_candidates",
                "query": query, "suggestions": [],
                "message": _empty_message(bool(excluded), preference)}

    candidates_text = "\n\n---\n\n".join(
        f"training_id: {tid}\ntitle: {c['title']}\nobjectives: {c['objectives']}\ncontent:\n{c['content']}"
        for tid, c in candidates.items()
    )
    human = f"LEARNING-GAP PROFILE:\n{gap_content or '(empty)'}\n"
    if preference:
        human += f"\nLEARNER REQUEST:\n{preference}\n"
    human += f"\nCANDIDATE TRAININGS:\n{candidates_text}\n\nChoose 1 to 3 trainings."
    structured = _llm(0.4).with_structured_output(_SuggestionResult)
    result: _SuggestionResult = invoke_with_retry(
        structured.invoke,
        [SystemMessage(content=SUGGESTION_PROMPT), HumanMessage(content=human)],
    )

    suggestions = []
    for s in result.suggestions:
        tr = repo.get_training(s.training_id)
        if not tr or s.training_id in assigned_ids:
            continue
        suggestions.append({"training_id": tr["id"], "title": tr["title"],
                            "objectives": tr.get("learning_objectives", []), "rationale": s.rationale})
    if not suggestions:
        # The agent is told to discard off-topic candidates rather than pad the list, so
        # an empty selection is a real answer — don't fall back to the raw retrieval.
        return {"status": "no_candidates", "query": query, "suggestions": [],
                "message": _empty_message(bool(excluded), preference)}
    return {"status": "success", "query": query, "suggestions": suggestions[:3]}
