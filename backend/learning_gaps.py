"""
Learning Gaps Extraction
========================

After a training is evaluated, this module derives the learner's *learning gaps* — one entry
per learning objective where the learner's reasoning diverged from the expert panel — together
with an evidence-based justification.

The gaps are persisted in the session (see ``backend/session_store.py``) and later consumed by
``backend/suggestions_agent.py`` to recommend further-practice situations from the bank.

Uses a single structured-output agent (``LearningGapsResult``), matching the existing
``with_structured_output`` pattern used by the evaluator and RAG modules.
"""

import os
import sys
import json
from pathlib import Path
from typing import Any, Dict

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_anthropic import ChatAnthropic

sys.path.append(str(Path(__file__).parent.parent))

from models import LearningGapsResult
from backend.llm_retry import invoke_with_retry


LEARNING_GAPS_PROMPT = """# Role
You are an Expert Educational Diagnostician for "Learning by Concordance" (LbC) trainings.
VERY IMPORTANT: Your output MUST be in French.

# Task
You are given:
1. The training's Learning Objectives.
2. A structured Evaluation (JSON) of a single learner's responses across several scenarios.
   Each scenario contains a coverage assessment, logical-reasoning rating, communication
   rating, and a per-learning-objective skills_assessment (Satisfactory / Unsatisfactory).

Identify the learner's LEARNING GAPS — produce ONE gap entry per Learning Objective for which
the learner shows meaningful divergence from the expert panel. A divergence is indicated by:
- skills_assessment marked "Unsatisfactory" for that objective in one or more scenarios, and/or
- "Low" or "Medium" coverage, and/or
- "Unsatisfactory" logical reasoning in scenarios where that objective applies.

# Rules
- Emit a gap ONLY for objectives where there is genuine divergence. If the learner is well
  aligned with experts on an objective across all scenarios, do NOT emit a gap for it.
- For each gap, write:
  * learning_objective: the objective verbatim.
  * gap_summary: ONE sentence describing the divergence.
  * justification: an evidence-based explanation referencing the scenarios and what the
    experts emphasised that the learner missed.
  * related_scenarios: the scenario identifiers where the gap appears
    (e.g. "situation 1 / scenario 2").
- If the learner is strongly aligned everywhere, return an empty list of gaps.
- Output French only.
"""


def get_llm_model() -> ChatAnthropic:
    return ChatAnthropic(
        model="claude-sonnet-4-6",
        temperature=0.3,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    )


def extract_learning_gaps(
    evaluations: Dict[str, Any],
    training_objectives: str,
    training_type: str = "migraine",
) -> Dict[str, Any]:
    """Derive the learner's learning gaps from an evaluation.

    Returns a dict ``{"gaps": [...], "training_type": ...}`` (LearningGapsResult.model_dump()
    plus the training type) so it can be stored as-is in the session.
    """
    print(f"\n🧭 Extracting learning gaps for training type: {training_type}")

    llm = get_llm_model()
    structured_llm = llm.with_structured_output(LearningGapsResult)

    human_content = f"""Training Objectives:
{training_objectives}

Evaluation (JSON):
{json.dumps(evaluations, indent=2, ensure_ascii=False)}

Identify the learner's learning gaps per learning objective, with justifications, in French.
"""

    messages = [
        SystemMessage(content=LEARNING_GAPS_PROMPT),
        HumanMessage(content=human_content),
    ]

    result: LearningGapsResult = invoke_with_retry(structured_llm.invoke, messages)
    payload = result.model_dump()
    payload["training_type"] = training_type
    print(f"✅ Extracted {len(payload.get('gaps', []))} learning gap(s)")
    return payload
