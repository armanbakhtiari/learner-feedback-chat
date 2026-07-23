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
from typing import Any, Dict, List

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_anthropic import ChatAnthropic

from models import GeneratedExpertPanel
from backend.llm_retry import invoke_with_retry


EXPERT_PANEL_PROMPT = """Tu es un agent qui génère un PANEL D'EXPERTS synthétique pour un
scénario de « Learning by Concordance » nouvellement créé (aucun vrai expert ne l'a encore
évalué). Produis 5 réponses d'experts plausibles et NUANCÉES (labels « Expert 1 » .. « Expert 5 »),
chacune avec un niveau de concordance (Fortement affaiblie / Affaiblie / Inchangée / Renforcée /
Fortement renforcée) et une justification courte. Les experts doivent raisonner de façon crédible
et peuvent diverger entre eux, comme un vrai panel. SORTIE EN FRANÇAIS."""


def _llm() -> ChatAnthropic:
    return ChatAnthropic(
        model="claude-sonnet-4-6",
        temperature=0.5,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    )


def generate_expert_panel(situation_text: str, hypothesis: str, new_information: str) -> List[Dict[str, Any]]:
    """Generate a synthetic 5-expert panel for one newly generated scenario."""
    structured = _llm().with_structured_output(GeneratedExpertPanel)
    human = f"""SITUATION:
{situation_text}

SCÉNARIO:
Si vous pensiez ... {hypothesis}
Et qu'alors ... {new_information}

Génère un panel de 5 experts (label, niveau de concordance, justification)."""
    result: GeneratedExpertPanel = invoke_with_retry(
        structured.invoke,
        [SystemMessage(content=EXPERT_PANEL_PROMPT), HumanMessage(content=human)],
    )
    return [e.model_dump() for e in result.experts]
