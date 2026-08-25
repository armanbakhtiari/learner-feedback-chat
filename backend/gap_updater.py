"""
Learning-gap updater agent.

After each training evaluation, this agent reads the learner's CURRENT learning-gap
profile plus the NEW evaluation and returns an UPDATED profile: it adds newly
observed gaps, removes gaps the learner has since resolved (good performance), and
refines existing gaps — always grouped under the corresponding learning objective.

The profile is stored per user (one evolving document). We render a clean French
Markdown `content` deterministically from the structured result so the UI ("Mon
apprentissage" tab) and the feedback agent both get a consistent document.
"""

import json
import os
from typing import Any, Dict, List, Tuple

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_anthropic import ChatAnthropic

from models import LearningGapProfile
from backend.llm_retry import invoke_with_retry


GAP_UPDATER_PROMPT = """# Role
You are an educational diagnostician for "Learning by Concordance" trainings.

**LANGUAGE: all text you produce (summaries and gap descriptions) MUST be in FRENCH.**

# Inputs
1. The learner's CURRENT LEARNING PROFILE (may be empty if this is their first training),
   structured by learning objective.
2. The LEARNING OBJECTIVES of the training that was just evaluated.
3. The EVALUATION (JSON) of the learner's responses for this training — each scenario contains
   a coverage assessment, a logical-reasoning rating, a communication rating, and a
   per-objective assessment (Satisfactory / Unsatisfactory).

# Task: UPDATE the profile (do NOT rewrite it from scratch)
- **Add** the new gaps observed in this evaluation, under the corresponding objective. A gap is
  indicated by: "Unsatisfactory" assessment for an objective, and/or "Low"/"Medium" coverage,
  and/or "Unsatisfactory" reasoning.
- **Remove** an existing gap if the new evaluation shows the learner now performs well on it
  (alignment with the experts).
- **Refine** an existing gap if the new evaluation adds precision.
- Keep the still-relevant gaps from previous trainings.
- Group by learning objective. If an objective no longer has any gap, keep it with an empty gap
  list (this shows progress).

# Output format
Return a structured profile:
- overall_summary: a short summary (2-3 sentences) of the current state and progress (in French).
- objectives: one item per objective encountered, with its open gaps (summary + detail, in French).
"""


def _llm() -> ChatAnthropic:
    return ChatAnthropic(
        model="claude-sonnet-4-6",
        temperature=0.3,
        # Scales with the number of learning objectives the profile is grouped by (14 for
        # the gastro set), so don't leave the ceiling implicit — see backend/evaluator.py.
        max_tokens=16000,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    )


def render_markdown(profile: Dict[str, Any]) -> str:
    """Render the structured profile into a French Markdown document."""
    lines: List[str] = ["# Profil d'apprentissage", ""]
    summary = profile.get("overall_summary", "").strip()
    if summary:
        lines.append(summary)
        lines.append("")
    for group in profile.get("objectives", []):
        obj = group.get("learning_objective", "").strip()
        lines.append(f"## {obj}")
        gaps = group.get("gaps", [])
        if not gaps:
            lines.append("- _Aucune lacune en cours — bonne concordance avec les experts._")
        else:
            for g in gaps:
                s = g.get("summary", "").strip()
                d = g.get("detail", "").strip()
                lines.append(f"- **{s}**" + (f" — {d}" if d else ""))
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def update_learning_gap(
    current_content: str,
    current_structured: Dict[str, Any],
    evaluation_json: Dict[str, Any],
    objectives: List[str],
) -> Tuple[str, Dict[str, Any]]:
    """
    Produce the updated (markdown_content, structured_dict) for the learner's profile.
    """
    structured = _llm().with_structured_output(LearningGapProfile)
    current_repr = json.dumps(current_structured, ensure_ascii=False, indent=2) if current_structured else "(profil vide)"

    human = f"""CURRENT LEARNING PROFILE (structured):
{current_repr}

LEARNING OBJECTIVES of the evaluated training:
{chr(10).join('- ' + o for o in objectives)}

EVALUATION (JSON) of this training:
{json.dumps(evaluation_json, ensure_ascii=False, indent=2)}

Update the profile (add / remove / refine gaps) and return the complete profile. Write all text in French."""

    result: LearningGapProfile = invoke_with_retry(
        structured.invoke,
        [SystemMessage(content=GAP_UPDATER_PROMPT), HumanMessage(content=human)],
    )
    data = result.model_dump()
    return render_markdown(data), data
