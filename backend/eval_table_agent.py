"""
Evaluation-table agent (HTML).

Replaces the old matplotlib PNG generator. Given the structured evaluation JSON,
an LLM produces a self-contained, French, Learning-by-Concordance-neutral HTML
table (a `<div>` fragment with inline styles) to display in the completed-training
tab. No numeric scores, no pass/fail labels, no red/green semaphore colors — LbC
stays non-judgmental; it summarizes coverage and reasoning qualitatively per
scenario and per learning objective.
"""

import json
import os
import re
from typing import Any, Dict

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_anthropic import ChatAnthropic

from backend.llm_retry import invoke_with_retry


EVAL_TABLE_PROMPT = """# Role
You generate a summary HTML TABLE for a "Learning by Concordance" evaluation, to be
displayed in a web application.

**LANGUAGE: all visible text in the table MUST be in FRENCH** (headers and content).

# Input
An evaluation JSON: situations, each containing scenarios; each scenario has:
- expert_key_elements (the experts' key concepts)
- coverage (score_assessment High/Medium/Low + a justification whose line 1 lists the key
  themes the learner successfully addressed and line 2 lists the critical expert themes the
  learner missed)
- logical_reasoning (rating Satisfactory/Unsatisfactory + assessment)
- communication (rating + assessment)
- skills_assessment: per learning objective (ignore this for the table)

# Output
A SELF-CONTAINED HTML fragment (start with <div ...>, end with </div>), INLINE styles only
(no <style>, no <script>, no <html>/<body> tags).
- One clear table per situation; rows = scenarios. Use these columns, with French headers:
  1. « Scénario » (the hypothesis)
  2. « Éléments clés des experts » (from expert_key_elements)
  3. « Thèmes clés abordés par l'apprenant » (derive from coverage justification line 1)
  4. « Thèmes clés manqués par l'apprenant » (derive from coverage justification line 2)
  5. « Raisonnement » (from logical_reasoning.assessment)
  6. « Communication » (from communication.assessment)
- Summarize qualitatively. Do NOT show numeric scores, pass/fail labels, or red/green
  traffic-light colors (Learning-by-Concordance stays non-judgmental). Use a sober, neutral
  style (soft grey/blue), readable on a light theme.
- The HTML must be valid and stand alone (width 100%, wrap wide tables in a container with
  `overflow-x:auto`).

# Constraint
Respond with ONLY the HTML fragment. No text before or after, no Markdown ``` fences.
"""


def _llm() -> ChatAnthropic:
    return ChatAnthropic(
        model="claude-sonnet-4-6",
        temperature=0.2,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    )


def _strip_code_fences(text: str) -> str:
    text = text.strip()
    text = re.sub(r"^```(?:html)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    return text.strip()


def generate_evaluation_html(evaluation_json: Dict[str, Any]) -> str:
    """Return a self-contained HTML fragment summarizing the evaluation."""
    human = (
        "Evaluation (JSON):\n"
        + json.dumps(evaluation_json, ensure_ascii=False, indent=2)
        + "\n\nGenerate the summary table HTML fragment. All visible text must be in French."
    )
    response = invoke_with_retry(
        _llm().invoke,
        [SystemMessage(content=EVAL_TABLE_PROMPT), HumanMessage(content=human)],
    )
    return _strip_code_fences(response.content)
