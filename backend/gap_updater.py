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


GAP_UPDATER_PROMPT = """# Rôle
Tu es un diagnosticien pédagogique pour des formations « Learning by Concordance ».
SORTIE OBLIGATOIREMENT EN FRANÇAIS.

# Entrées
1. Le PROFIL D'APPRENTISSAGE ACTUEL de l'apprenant (peut être vide s'il s'agit de sa
   première formation), structuré par objectif d'apprentissage.
2. Les OBJECTIFS D'APPRENTISSAGE de la formation qui vient d'être évaluée.
3. L'ÉVALUATION (JSON) des réponses de l'apprenant pour cette formation — chaque scénario
   contient une évaluation de couverture, de raisonnement logique, de communication, et
   une évaluation par objectif (Satisfactory / Unsatisfactory).

# Tâche : METTRE À JOUR le profil (ne pas le réécrire de zéro)
- **Ajouter** les nouvelles lacunes observées dans cette évaluation, sous l'objectif
  correspondant. Une lacune est indiquée par : évaluation « Unsatisfactory » pour un objectif,
  et/ou couverture « Low »/« Medium », et/ou raisonnement « Unsatisfactory ».
- **Retirer** une lacune existante si la nouvelle évaluation montre que l'apprenant a
  maintenant une bonne performance sur ce point (alignement avec les experts).
- **Affiner** une lacune existante si la nouvelle évaluation apporte des précisions.
- Conserver les lacunes toujours pertinentes des formations précédentes.
- Regrouper par objectif d'apprentissage. Si un objectif n'a plus de lacune, garde-le avec
  une liste de lacunes vide (cela montre le progrès).

# Format de sortie
Retourne un profil structuré :
- overall_summary : court résumé (2-3 phrases) de l'état actuel et des progrès.
- objectives : un élément par objectif rencontré, avec ses lacunes ouvertes (summary + detail).
"""


def _llm() -> ChatAnthropic:
    return ChatAnthropic(
        model="claude-sonnet-4-6",
        temperature=0.3,
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

    human = f"""PROFIL D'APPRENTISSAGE ACTUEL (structuré):
{current_repr}

OBJECTIFS D'APPRENTISSAGE de la formation évaluée:
{chr(10).join('- ' + o for o in objectives)}

ÉVALUATION (JSON) de cette formation:
{json.dumps(evaluation_json, ensure_ascii=False, indent=2)}

Mets à jour le profil (ajout / retrait / affinage des lacunes) et retourne le profil complet."""

    result: LearningGapProfile = invoke_with_retry(
        structured.invoke,
        [SystemMessage(content=GAP_UPDATER_PROMPT), HumanMessage(content=human)],
    )
    data = result.model_dump()
    return render_markdown(data), data
