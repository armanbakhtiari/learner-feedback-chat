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


EVAL_TABLE_PROMPT = """# Rôle
Tu génères un TABLEAU HTML récapitulatif d'une évaluation « Learning by Concordance »,
en FRANÇAIS, destiné à être affiché dans une application web.

# Entrée
Un JSON d'évaluation : des situations, chacune contenant des scénarios ; chaque scénario a
- expert_key_elements (concepts clés des experts)
- coverage (score_assessment High/Medium/Low + justification)
- logical_reasoning (rating Satisfactory/Unsatisfactory + assessment)
- communication (rating + assessment)
- skills_assessment : par objectif d'apprentissage (present_in_scenario, learner_assessment, justification)

# Sortie
Un fragment HTML AUTONOME (commençant par <div ...> et se terminant par </div>), avec des
styles INLINE uniquement (pas de <style>, pas de <script>, pas de balises <html>/<body>).
- Un tableau clair par situation ; lignes = scénarios ; colonnes utiles : Scénario (hypothèse),
  Éléments clés des experts, Couverture, Raisonnement, Communication, Objectifs démontrés.
- Résume qualitativement. NE PAS afficher de score chiffré, NI d'étiquette réussite/échec,
  NI de couleurs rouge/vert de type feu de circulation. Utilise un style sobre et neutre
  (gris/bleu doux), lisible en thème clair.
- Le HTML doit être valide et se suffire à lui-même (largeur 100%, `overflow-x:auto` sur un
  conteneur pour les tableaux larges).

# Contrainte
Réponds UNIQUEMENT avec le fragment HTML. Aucun texte avant ou après, pas de balise Markdown ```.
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
        "Évaluation (JSON):\n"
        + json.dumps(evaluation_json, ensure_ascii=False, indent=2)
        + "\n\nGénère le fragment HTML du tableau récapitulatif, en français."
    )
    response = invoke_with_retry(
        _llm().invoke,
        [SystemMessage(content=EVAL_TABLE_PROMPT), HumanMessage(content=human)],
    )
    return _strip_code_fences(response.content)
