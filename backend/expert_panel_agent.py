"""
Expert-panel agent.

A distinct agent that synthesizes a plausible panel of expert responses for a
*newly generated* Learning-by-Concordance scenario (path-2 "create new scenarios"),
so the generated training is completable and evaluable by concordance even though no
real experts have answered it yet.

Kept separate from ``scenario_generator`` (which invents the scenarios) so the two
concerns — generating the challenge vs. generating the expert reference — stay
independent.
"""

import os
from typing import Any, Dict, List, Optional

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_anthropic import ChatAnthropic

from models import GeneratedExpertPanel
from backend.likert import DEFAULT_SCALE, coerce, values_for
from backend.llm_retry import invoke_with_retry


EXPERT_PANEL_PROMPT = """You generate a synthetic EXPERT PANEL for a newly created
"Learning by Concordance" scenario (no real expert has evaluated it yet). Produce 5 plausible,
NUANCED expert responses (labels "Expert 1" .. "Expert 5"), each with a rating copied VERBATIM
from this scale ({scale}) and a short justification. The experts should reason credibly and may
diverge from one another, like a real panel. **Write all justifications in FRENCH.**"""


def _llm() -> ChatAnthropic:
    return ChatAnthropic(
        model="claude-sonnet-4-6",
        temperature=0.5,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    )


def generate_expert_panel(situation_text: str, hypothesis: str, new_information: str,
                          scale: Optional[str] = DEFAULT_SCALE) -> List[Dict[str, Any]]:
    """Generate a synthetic 5-expert panel for one newly generated scenario."""
    scale_text = " / ".join(values_for(scale))
    structured = _llm().with_structured_output(GeneratedExpertPanel)
    human = f"""SITUATION:
{situation_text}

SCENARIO:
Si vous pensiez ... {hypothesis}
Et qu'alors ... {new_information}

Generate a panel of 5 experts (label, rating, justification). Write justifications in French."""
    result: GeneratedExpertPanel = invoke_with_retry(
        structured.invoke,
        [SystemMessage(content=EXPERT_PANEL_PROMPT.format(scale=scale_text)),
         HumanMessage(content=human)],
    )
    panel = [e.model_dump() for e in result.experts]
    for e in panel:
        e["likert"] = coerce(e.get("likert"), scale)
    return panel
