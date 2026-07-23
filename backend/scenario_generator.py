"""
Gap-Focused Scenario Generator
==============================

Generates brand-new Learning-by-Concordance scenarios for the *exact* situations a learner was
evaluated on, focused on the learner's learning gaps. For each evaluated situation it produces
a fixed number of new scenarios (default 2).

Reuses the scenario-quality definitions and chain-of-thought from ``create_scenario.py`` and
the structured-output pattern (``with_structured_output``) used across the codebase.
"""

import os
import sys
import json
from pathlib import Path
from typing import Any, Dict, List

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_anthropic import ChatAnthropic

sys.path.append(str(Path(__file__).parent.parent))

from models import SituationScenarios
from create_scenario import (
    scenario_generation_system_prompt,
    scenario_generation_user_prompt,
    scenario_criteria,
    reasoning_scenario_definition,
)
from backend.llm_retry import invoke_with_retry

N_SCENARIOS_PER_SITUATION = 2


def _llm() -> ChatAnthropic:
    return ChatAnthropic(
        model="claude-sonnet-4-6",
        temperature=0.6,  # a bit of creativity for distinct scenarios
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    )


def generate_scenarios_for_situation(
    situation: Dict[str, Any],
    objectives: str,
    gaps: List[Dict[str, Any]],
    n_scenarios: int = N_SCENARIOS_PER_SITUATION,
) -> SituationScenarios:
    """Generate ``n_scenarios`` new gap-focused scenarios for one situation."""
    system_prompt = scenario_generation_system_prompt.format(
        scenario_criteria=scenario_criteria,
        reasoning_scenario_definition=reasoning_scenario_definition,
    )
    user_prompt = scenario_generation_user_prompt.format(
        objectives=objectives,
        situation=situation.get("text", ""),
        learning_gaps=json.dumps(gaps, indent=2, ensure_ascii=False),
        n_scenarios=n_scenarios,
    )

    structured = _llm().with_structured_output(SituationScenarios)
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_prompt),
    ]
    result: SituationScenarios = invoke_with_retry(structured.invoke, messages)

    # Defensive: cap to the requested number in case the model returns extras.
    if len(result.scenarios) > n_scenarios:
        result = SituationScenarios(scenarios=result.scenarios[:n_scenarios])
    return result


# Note: synthetic expert panels for generated scenarios are produced by the distinct
# `backend/expert_panel_agent.py` agent (kept separate from scenario invention).
