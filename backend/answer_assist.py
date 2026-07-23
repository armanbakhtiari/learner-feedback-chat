"""
Answer-assist agent.

Generates a suggested learner answer (Likert + justification) for ONE scenario, to
help a user complete a training. It is given only the situation text and the
scenario (hypothesis + new information) — it MUST NOT see expert responses or any
other learner's answers.
"""

import os
from typing import Any, Dict

from langchain_core.messages import SystemMessage, HumanMessage
from langchain_anthropic import ChatAnthropic

from models import AssistedAnswer
from backend.llm_retry import invoke_with_retry


ANSWER_ASSIST_PROMPT = """# Rôle
Tu es un assistant pédagogique qui aide un apprenant à formuler une réponse à un scénario
de « Learning by Concordance » (concordance de raisonnement).

# Contexte
On te donne une SITUATION clinique et un SCÉNARIO composé de :
- une hypothèse d'action ou de diagnostic (« Si vous pensiez ... »)
- une information nouvelle (« Et qu'alors ... »)

L'apprenant doit indiquer comment cette information nouvelle modifie la pertinence de
l'hypothèse, sur l'échelle de concordance à 5 niveaux :
« Fortement affaiblie », « Affaiblie », « Inchangée », « Renforcée », « Fortement renforcée ».

# Tâche
Propose UNE réponse plausible qu'un apprenant compétent pourrait donner :
- `likert` : le niveau de concordance choisi.
- `justification` : 2 à 4 phrases, en français, expliquant le raisonnement.

# Contraintes
- Réponds UNIQUEMENT à partir de la situation et du scénario fournis.
- Tu n'as PAS accès aux réponses d'experts : ne prétends pas les connaître.
- Reste nuancé et professionnel. Sortie en français.
"""


def _llm() -> ChatAnthropic:
    return ChatAnthropic(
        model="claude-sonnet-4-6",
        temperature=0.4,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
    )


def generate_assisted_answer(situation_text: str, hypothesis: str, new_information: str) -> Dict[str, Any]:
    """Return {"likert", "justification"} for a single scenario (no expert data used)."""
    structured = _llm().with_structured_output(AssistedAnswer)
    human = f"""SITUATION:
{situation_text}

SCÉNARIO:
Si vous pensiez ... {hypothesis}
Et qu'alors ... {new_information}

Propose une réponse (niveau de concordance + justification) en français."""
    result: AssistedAnswer = invoke_with_retry(
        structured.invoke,
        [SystemMessage(content=ANSWER_ASSIST_PROMPT), HumanMessage(content=human)],
    )
    return result.model_dump()
