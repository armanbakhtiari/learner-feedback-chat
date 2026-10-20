"""
Answer-assist agent.

Generates a suggested learner answer (Likert + justification) for ONE scenario, to
help a user complete a training. It is given only the situation text and the
scenario (hypothesis + new information) — it MUST NOT see expert responses or any
other learner's answers.
"""

import os
from typing import Any, Dict, Optional

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_anthropic import ChatAnthropic

from models import AssistedAnswer
from backend.likert import DEFAULT_SCALE, coerce, values_for
from backend.llm_retry import invoke_with_retry


ANSWER_ASSIST_PROMPT = """# Role
You are an educational assistant helping a learner formulate a response to a
"Learning by Concordance" scenario.

**LANGUAGE: your output (the justification) MUST be in FRENCH.**

# Context
You are given a professional SITUATION and a SCENARIO. {format}

The learner answers on this {n}-level scale (ordered from most negative to most positive):
{scale}

# Task
Propose ONE plausible response a competent learner could give:
- `likert`: one of the {n} values above, copied VERBATIM.
- `justification`: 2 to 4 sentences, in French, explaining the reasoning.

# Constraints
- Reason ONLY from the provided situation and scenario.
- You do NOT have access to any expert responses — do not pretend to know them.
- Stay nuanced and professional. Output in French.
"""


def _llm() -> ChatAnthropic:
    return ChatAnthropic(
        model="claude-sonnet-4-6",
        temperature=0.4,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    )


REASONING_FORMAT = """It consists of:
- an action/diagnostic hypothesis ("Si vous pensiez ...")
- a new piece of information ("Et qu'alors ...")
The learner indicates how this new information affects the hypothesis."""

JUDGMENT_FORMAT = """It is a single observed behaviour ("Comportement observé"), with no new
information. The learner judges how acceptable that behaviour is."""


def generate_assisted_answer(situation_text: str, hypothesis: str, new_information: str,
                             scale: Optional[str] = DEFAULT_SCALE,
                             kind: str = "reasoning") -> Dict[str, Any]:
    """Return {"likert", "justification"} for a single scenario (no expert data used)."""
    values = values_for(scale)
    scale_text = "\n".join(f'- "{v}"' for v in values)
    structured = _llm().with_structured_output(AssistedAnswer)
    if kind == "judgment":
        scenario_text = f"Comportement observé ... {hypothesis}"
    else:
        scenario_text = f"Si vous pensiez ... {hypothesis}\nEt qu'alors ... {new_information}"
    human = f"""SITUATION:
{situation_text}

SCENARIO:
{scenario_text}

Propose a response (a value from the scale + justification). Write the justification in French."""
    system = ANSWER_ASSIST_PROMPT.format(
        format=JUDGMENT_FORMAT if kind == "judgment" else REASONING_FORMAT,
        n=len(values), scale=scale_text,
    )
    result: AssistedAnswer = invoke_with_retry(
        structured.invoke,
        [SystemMessage(content=system), HumanMessage(content=human)],
    )
    answer = result.model_dump()
    answer["likert"] = coerce(answer.get("likert"), scale)
    return answer
