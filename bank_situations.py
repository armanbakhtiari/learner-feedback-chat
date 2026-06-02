"""
Bank of Situations
==================

A domain-agnostic bank of the *remaining* training situations that are NOT used as
the currently evaluated training module. These situations are candidates suggested to
the learner for further practice, based on their learning gaps.

Sources:
  - Migraine: modules 2 and 3 (``training_2`` / ``training_3`` of ``trainings_2_experts``),
    split into individual situations. Module 1 stays the evaluated migraine training.
  - GRH (gestion des ressources humaines): situations 2 to 6 of the
    "Synthèses éducatives projet GRH" document. Situation 1 stays the evaluated GRH training.

Each bank entry is a dict::

    {
        "id": str,            # stable unique id
        "domain": str,        # "migraine" | "grh"
        "title": str,         # human readable title
        "objectives": str,    # learning objectives of the source training
        "content": str,       # full situation text (situation + scenarios + expert responses)
    }

This file is the single source of truth for the bank vector store (see
``backend/bank_rag.py``). It is always available regardless of which training the learner
selected for evaluation.
"""

import re
import hashlib
from typing import Dict, List, Iterator

from trainings_2_experts import (
    training_2 as _migraine_training_2,
    training_3 as _migraine_training_3,
    training_objectives as _migraine_objectives,
)


# =============================================================================
# Migraine bank entries (derived from modules 2 & 3, split per situation)
# =============================================================================

_MIGRAINE_MODULE_TITLES = {
    "m2": "Migraine — Module 2 : Traitement aigu et gestion des habitudes de vie de la migraine",
    "m3": "Migraine — Module 3 : Traitement préventif de la migraine",
}


def _split_situations(module_text: str) -> List[str]:
    """Extract each ``<Situation N>...</Situation N>`` block from a module string."""
    return re.findall(r"<Situation \d+>.*?</Situation \d+>", module_text, flags=re.DOTALL)


def _strip_expert_responses(situation_text: str) -> str:
    """Keep only the situation and its scenarios; drop expert/panelist and learner responses.

    The bank is a catalogue of candidate practice situations, so it intentionally excludes the
    experts' opinions and the learner's answers — only the situation context and the scenario
    prompts (the "Si vous pensiez à…" / "Et qu'alors…" pairs) are retained.
    """
    # Everything from "Experts' Responses:" until the end of the scenario block is removed.
    cleaned = re.sub(r"Experts' Responses:.*?(?=</Scenario)", "", situation_text, flags=re.DOTALL)
    # Collapse the blank lines left behind.
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()


def _build_migraine_entries() -> List[Dict[str, str]]:
    entries: List[Dict[str, str]] = []
    for module_key, module_text in (("m2", _migraine_training_2), ("m3", _migraine_training_3)):
        situations = _split_situations(module_text)
        module_title = _MIGRAINE_MODULE_TITLES[module_key]
        for idx, situation_text in enumerate(situations, start=1):
            entries.append({
                "id": f"migraine_{module_key}_s{idx}",
                "domain": "migraine",
                "title": f"{module_title} — Situation {idx}",
                "objectives": _migraine_objectives.strip(),
                "content": _strip_expert_responses(situation_text),
            })
    return entries


# =============================================================================
# GRH bank entries (situations 2 to 6)
# =============================================================================

_GRH_OBJECTIVES = """Training Objectives:
- Adopter un comportement exemplaire et conforme aux lois, aux normes formelles et informelles ainsi qu'aux codes sociaux en vigueur.
- Contribuer à développer, soutenir et modifier des comportements, des politiques et des règlements conformément à l'éthique du travail.
- Organiser le travail, gérer son temps et celui des autres et établir des priorités.
- Structurer les tâches de manière à être le plus efficace possible et à respecter les échéances."""


_GRH_SITUATION_2 = """Situation #2 : Employée positive dans l'équipe, mais peu efficace
Julie est une employée très positive dans l'équipe. Elle est impliquée dans les réunions et exerce une influence positive sur ses collègues. Toutefois, elle bavarde souvent avec ses collègues, ce qui l'amène à avoir de la difficulté à respecter les échéanciers des projets qui lui sont confiés.

Scénario 1
Si vous pensiez à… Féliciter Julie pour ses forces tout en lui parlant de vos préoccupations concernant sa prestation de travail.
Et qu'alors vous savez que… Elle n'a pas réussi à livrer deux de ses projets le mois dernier.

Scénario 2
Si vous pensiez à… Faire une rencontre d'encadrement en lien avec la performance au travail et réitérer vos attentes face au projet.
Et qu'alors vous savez que… Julie est sensible et qu'elle prend les choses personnellement.

Scénario 3
Si vous pensiez à… Lors d'un échange informel, glisser un commentaire constructif avec humour et bienveillance.
Et qu'alors vous savez que… Julie est sensible et qu'elle prend les choses personnellement.

Scénario 4
Si vous pensiez à… Lors d'un échange informel, glisser un commentaire constructif avec humour et bienveillance.
Et qu'alors vous savez que… Un projet important sous sa responsabilité est à remettre dans deux semaines."""


_GRH_SITUATION_3 = """Situation #3 : Employée à personnalité difficile
Vous êtes nouvellement gestionnaire d'une équipe de 12 personnes et vous avez une employée dont vous avez déjà entendu parler comme étant une personne ayant des opinions tranchées. Dès vos premières semaines, 4 personnes viennent vous confier vivre des enjeux avec cette employée. Elle est réactive lorsque ses collègues lui posent des questions. Elle personnalise les enjeux et c'est toujours la faute de ses collègues quand la collaboration est houleuse.

Scénario 1
Si vous pensiez à… La rencontrer immédiatement pour la questionner sur sa version des faits.
Et qu'alors vous savez que… elle a déjà été rencontrée par ses supérieurs en lien avec ce problème dans le passé.

Scénario 2
Si vous pensiez à… Tenter de récolter des faits sur la situation.
Et qu'alors vous savez que… ces situations se passent lorsque vous n'êtes pas sur le terrain et que les informations partagées sont seulement basées sur des perceptions.

Scénario 3
Si vous pensiez à… Ne rien faire pour l'instant, puisque ce sont seulement des perceptions de ses collègues.
Et qu'alors vous savez que… cette situation n'a aucun impact sur la performance de l'équipe."""


_GRH_SITUATION_4 = """Situation #4 : Employée qui quitte lors de sa première journée de travail
Sophia effectue sa première journée au travail. À l'heure du dîner, elle passe devant votre bureau et vous annonce qu'elle quitte, car le travail est trop difficile pour elle.

Scénario 1
Si vous pensiez à… L'inviter dans votre bureau pour discuter de la situation.
Et qu'alors vous savez que… vous avez besoin d'elle pour l'après-midi, donc vous tentez de la retenir.

Scénario 2
Si vous pensiez à… L'inviter dans votre bureau pour discuter de la situation.
Et qu'alors vous savez que… l'employée pleure et semble très émotive.

Scénario 3
Si vous pensiez à… La laisser partir sans rien dire.
Et qu'alors vous savez que… c'était votre dernier choix lors du processus d'embauche et que vous aviez des doutes sur son éventuelle prestation de travail.

Scénario 4
Si vous pensiez à… L'appeler après son départ pour planifier une rencontre afin de discuter de la situation.
Et qu'alors vous savez que… vous avez observé sa fermeture lors de son départ et les larmes sur son visage."""


_GRH_SITUATION_5 = """Situation #5 : Propos qui nuisent à la réputation de l'entreprise
Sandra est gestionnaire en ressources humaines depuis 2 ans. Elle vient d'apprendre que Jonathan a publié sur les réseaux sociaux un message dans lequel il dénigre leur entreprise. C'est la deuxième fois que Jonathan publie un message nuisant à la réputation de l'entreprise, alors que cela fait partie de son contrat de travail.

Scénario 1
Comportement observé : Sandra rencontre Jonathan pour lui donner un avis verbal.

Scénario 2
Comportement observé : Après avoir validé les faits, Sandra rencontre immédiatement Jonathan pour le suspendre 2 jours.

Scénario 3
Comportement observé : Sandra congédie immédiatement Jonathan."""


_GRH_SITUATION_6 = """Situation #6 : Conflit d'intérêts
Jérôme apprend que deux employés, Justine et Pierre-Luc, ont développé une relation amoureuse. Depuis qu'ils travaillent sur le projet ensemble, ils se fréquentent à l'extérieur du travail. Pierre-Luc confie à Jérôme qu'il a développé des sentiments pour Justine depuis 1 mois. Justine est la gestionnaire d'une équipe dans laquelle travaille Pierre-Luc.

Scénario 1
Comportement observé : Jérôme rencontre Justine pour clarifier ses attentes sur les comportements attendus entre Justine et Pierre-Luc au travail et la sensibiliser à ses potentiels enjeux de crédibilité en tant que gestionnaire.

Scénario 2
Comportement observé : Jérôme rencontre conjointement Justine et Pierre-Luc pour leur annoncer qu'un des deux doit quitter l'organisation s'il souhaite poursuivre la relation, car ils sont en conflit d'intérêts.

Scénario 3
Comportement observé : Jérôme est vigilant en ce qui concerne la situation, mais n'intervient pas pour l'instant."""


_GRH_SITUATIONS = [
    ("grh_s2", "GRH — Situation 2 : Employée positive dans l'équipe, mais peu efficace", _GRH_SITUATION_2),
    ("grh_s3", "GRH — Situation 3 : Employée à personnalité difficile", _GRH_SITUATION_3),
    ("grh_s4", "GRH — Situation 4 : Employée qui quitte lors de sa première journée", _GRH_SITUATION_4),
    ("grh_s5", "GRH — Situation 5 : Propos qui nuisent à la réputation de l'entreprise", _GRH_SITUATION_5),
    ("grh_s6", "GRH — Situation 6 : Conflit d'intérêts", _GRH_SITUATION_6),
]


def _build_grh_entries() -> List[Dict[str, str]]:
    return [
        {
            "id": sid,
            "domain": "grh",
            "title": title,
            "objectives": _GRH_OBJECTIVES,
            "content": content.strip(),
        }
        for sid, title, content in _GRH_SITUATIONS
    ]


# =============================================================================
# Public API
# =============================================================================

BANK_SITUATIONS: List[Dict[str, str]] = _build_migraine_entries() + _build_grh_entries()


def iter_bank_situations() -> Iterator[Dict[str, str]]:
    """Iterate over all bank situations."""
    return iter(BANK_SITUATIONS)


def get_bank_text(situation_id: str) -> str:
    """Return the full content text for a bank situation id, or '' if not found."""
    for entry in BANK_SITUATIONS:
        if entry["id"] == situation_id:
            return entry["content"]
    return ""


def get_bank_situation(situation_id: str) -> Dict[str, str]:
    """Return the full bank entry for an id, or an empty dict if not found."""
    for entry in BANK_SITUATIONS:
        if entry["id"] == situation_id:
            return entry
    return {}


def compute_bank_hash() -> str:
    """Hash the bank content so the vector store can detect changes and re-index."""
    hasher = hashlib.md5()
    for entry in BANK_SITUATIONS:
        hasher.update(entry["id"].encode("utf-8"))
        hasher.update(entry["content"].encode("utf-8"))
    return hasher.hexdigest()
