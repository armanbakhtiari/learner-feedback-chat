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
                "content": situation_text.strip(),
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
Experte de contenu — Réponse : Affaiblie. Justification : Je vais la rencontrer afin d'adresser la situation et clarifier mes attentes en lien avec ses tâches et responsabilités. Je vais possiblement faire de la reconnaissance dans un autre contexte afin de séparer mes deux messages.
Panéliste #2 — Renforcée : Il est important de rencontrer Julie. Il est possible de la féliciter, mais elle doit comprendre que ses projets à livrer demeurent sa priorité.
Panéliste #3 — Inchangée : Féliciter pour compétences comportementales et influence positive. Clarifier les attentes pour les échéances et faire un suivi serré.
Panéliste #4 — Inchangée : S'agissant d'un premier échange, fournir un feedback complet en mentionnant aussi les points forts, et bien expliquer la problématique et ses conséquences, y compris les délais non respectés.
Panéliste #5 — Renforcée : La rencontre doit lui faire prendre conscience de son impact sur les autres et son travail, avec des faits et son retard sur les projets.

Scénario 2
Si vous pensiez à… Faire une rencontre d'encadrement en lien avec la performance au travail et réitérer vos attentes face au projet.
Et qu'alors vous savez que… Julie est sensible et qu'elle prend les choses personnellement.
Experte de contenu — Réponse : Inchangée. Justification : Je me concentre sur ce que je vais adresser comme observation et comment je vais le communiquer à Julie. Je tiens compte de sa sensibilité, mais j'adresse tout de même la situation.
Panéliste #2 — Fortement renforcée : Il est mieux d'adresser la situation bien qu'elle soit sensible, plutôt qu'elle lise le non-verbal et se crée des perceptions.
Panéliste #4 — Inchangée : Les discussions sur la performance doivent se tenir dans un cadre constructif, peu importe la sensibilité, de façon bienveillante.
Panéliste #5 — Affaiblie : Ne pas recadrer, mais la laisser parler pour prise de conscience et suivre son évolution avec des rencontres serrées.

Scénario 3
Si vous pensiez à… Lors d'un échange informel, glisser un commentaire constructif avec humour et bienveillance.
Et qu'alors vous savez que… Julie est sensible et qu'elle prend les choses personnellement.
Experte de contenu — Réponse : Fortement affaiblie. Justification : Un message informel risque d'être mal perçu ou mal compris.
Panéliste #2 — Fortement affaiblie : Elle pourrait se faire des scénarios ou mal retirer le message de la blague; préférable de la rencontrer et d'adresser directement les enjeux.
Panéliste #4 — Inchangée : Le feedback devrait être donné de manière régulière et informelle; un humour bienveillant peut faciliter la réception.
Panéliste #5 — Renforcée : L'informel est tout aussi important que le formel; garder la communication ouverte.

Scénario 4
Si vous pensiez à… Lors d'un échange informel, glisser un commentaire constructif avec humour et bienveillance.
Et qu'alors vous savez que… Un projet important sous sa responsabilité est à remettre dans deux semaines.
Experte de contenu — Réponse : Affaiblie. Justification : Je prends une note pour faire un débriefing à la suite du projet; n'étant pas désengagée, je ne veux pas que cet échange impacte la fin du projet.
Panéliste #2 — Fortement affaiblie : Préférable de la rencontrer et d'adresser les enjeux pour qu'elle bien rende le projet à remettre dans deux semaines.
Panéliste #4 — Affaiblie : Donner le feedback au bon moment; si elle est stressée par un projet important, organiser une rencontre plus formelle.
Panéliste #5 — Renforcée : Le commentaire constructif doit inclure du renforcement positif lié aux deux projets à livrer.

Synthèse éducative — Bilan : Il est essentiel de souligner les points positifs de la performance de Julie tout en offrant des rétroactions constructives sur le respect des échéances. Malgré sa sensibilité, il faut communiquer clairement les attentes en lien avec sa prestation de travail."""


_GRH_SITUATION_3 = """Situation #3 : Employée à personnalité difficile
Vous êtes nouvellement gestionnaire d'une équipe de 12 personnes et vous avez une employée dont vous avez déjà entendu parler comme étant une personne ayant des opinions tranchées. Dès vos premières semaines, 4 personnes viennent vous confier vivre des enjeux avec cette employée. Elle est réactive lorsque ses collègues lui posent des questions. Elle personnalise les enjeux et c'est toujours la faute de ses collègues quand la collaboration est houleuse.

Scénario 1
Si vous pensiez à… La rencontrer immédiatement pour la questionner sur sa version des faits.
Et qu'alors vous savez que… elle a déjà été rencontrée par ses supérieurs en lien avec ce problème dans le passé.
Experte de contenu — Réponse : Fortement renforcée. Justification : Possiblement qu'elle a déjà un dossier; je m'assure de le consulter et de poursuivre ce qui a été entamé, en agissant avec vigilance car le lien de confiance débute.
Panéliste #2 — Fortement renforcée : Prendre sa version des faits et lui faire part de l'impact de son attitude sur ses collègues; trouver des solutions rapidement.
Panéliste #3 — Inchangée : Rencontrer l'employée et partager des attentes claires, incluant sa responsabilisation et ses comportements collaboratifs.
Panéliste #4 — Inchangée : Traiter la rencontre comme une première prise de contact, ton convivial, en restant objective.
Panéliste #5 — Renforcée : La problématique semble récurrente; ouvrir la discussion et voir comment elle a perçu les choses.

Scénario 2
Si vous pensiez à… Tenter de récolter des faits sur la situation.
Et qu'alors vous savez que… ces situations se passent lorsque vous n'êtes pas sur le terrain et que les informations partagées sont seulement basées sur des perceptions.
Experte de contenu — Réponse : Fortement renforcée. Justification : Être plus présente sur le terrain pour observer et obtenir des faits concrets, et questionner les collègues à la recherche de faits observables.
Panéliste #2 — Fortement renforcée : Demander des faits réels (événements, dates, paroles) pour augmenter la crédibilité de la rencontre.
Panéliste #4 — Inchangée : Rassembler les faits et les aborder de manière impartiale, rester objectif.
Panéliste #5 — Renforcée : Quand il y a des perceptions, on a le devoir de creuser et de ne pas aller trop vite.

Scénario 3
Si vous pensiez à… Ne rien faire pour l'instant, puisque ce sont seulement des perceptions de ses collègues.
Et qu'alors vous savez que… cette situation n'a aucun impact sur la performance de l'équipe.
Experte de contenu — Réponse : Inchangée. Justification : Je reste en mode observation et plus présente sur le terrain.
Panéliste #2 — Renforcée : La performance n'étant pas affectée, le sentiment d'urgence diminue, quoiqu'il faille s'en préoccuper dans le futur.
Panéliste #4 — Affaiblie : Une mauvaise atmosphère et un manque de collaboration peuvent avoir des conséquences à long terme sur l'engagement et le roulement.
Panéliste #5 — Fortement affaiblie : Il faut du courage managérial et agir; le bon climat de travail est en jeu.

Synthèse éducative — Bilan : Il faut observer la situation sur le terrain et la traiter de manière impartiale. Il faut intervenir afin de garder un climat de travail agréable et une collaboration harmonieuse."""


_GRH_SITUATION_4 = """Situation #4 : Employée qui quitte lors de sa première journée de travail
Sophia effectue sa première journée au travail. À l'heure du dîner, elle passe devant votre bureau et vous annonce qu'elle quitte, car le travail est trop difficile pour elle.

Scénario 1
Si vous pensiez à… L'inviter dans votre bureau pour discuter de la situation.
Et qu'alors vous savez que… vous avez besoin d'elle pour l'après-midi, donc vous tentez de la retenir.
Experte de contenu — Réponse : Inchangée. Justification : Comprendre la situation, identifier des éléments déclencheurs et des solutions pour mieux la soutenir, en posant des questions ouvertes.
Panéliste #1 — Renforcée : Insister pour la rencontrer afin qu'elle se donne la chance d'essayer vraiment le travail; évaluer les causes et ajustements.
Panéliste #2 — Fortement renforcée : La rencontrer pour comprendre les éléments difficiles; alléger les tâches et prévoir formation/accompagnement.
Panéliste #3 — Affaiblie : Discuter de ce qui est trop difficile spécifiquement et voir si c'est solutionnable.
Panéliste #4 — Inchangée : Comprendre les raisons, évaluer les difficultés et la pertinence d'accommodements, et obtenir des retours sur le recrutement et la formation.
Panéliste #5 — Fortement affaiblie : Le déclencheur de départ est déjà fait; aucun besoin de la retenir pour l'après-midi.

Scénario 2
Si vous pensiez à… L'inviter dans votre bureau pour discuter de la situation.
Et qu'alors vous savez que… l'employée pleure et semble très émotive.
Experte de contenu — Réponse : Renforcée. Justification : Je souhaite qu'elle ne quitte pas dans cet état; encore plus important de questionner et de mieux comprendre la situation.
Panéliste #1 — Renforcée : Laisser mon travail pour écouter la nouvelle employée; le timing d'intégration n'est peut-être pas le bon.
Panéliste #2 — Fortement renforcée : La rencontrer même émotive pour qu'elle se sente supportée et mettre en place les bonnes actions.
Panéliste #3 — Inchangée : Discuter de ce qu'elle trouve difficile exactement et voir si c'est solvable.
Panéliste #4 — Inchangée : Comprendre les raisons de son état, s'assurer qu'elle quitte dans de bonnes conditions, bien clore la relation.
Panéliste #5 — Renforcée : Accueillir les émotions des employés, mais jusqu'à une certaine limite.

Scénario 3
Si vous pensiez à… La laisser partir sans rien dire.
Et qu'alors vous savez que… c'était votre dernier choix lors du processus d'embauche et que vous aviez des doutes sur son éventuelle prestation de travail.
Experte de contenu — Réponse : Inchangée. Justification : Chercher tout de même à mieux comprendre la situation et questionner, sans mettre d'énergie au-delà de ce que je peux faire pour l'accompagner.
Panéliste #1 — Affaiblie : On ne laisse jamais partir quelqu'un qui a passé un processus rigoureux de dotation; l'expérience employée est importante.
Panéliste #2 — Inchangée : Le traitement doit être le même peu importe le rang du candidat dans le processus.
Panéliste #4 — Fortement affaiblie : La laisser partir sans comprendre renforcerait un biais de confirmation; des éléments de l'environnement de travail pourraient être en cause.
Panéliste #5 — Affaiblie : Être correct avec le comité de recrutement; si elle a été choisie, trop de jugement ne sert à rien.

Scénario 4
Si vous pensiez à… L'appeler après son départ pour planifier une rencontre afin de discuter de la situation.
Et qu'alors vous savez que… vous avez observé sa fermeture lors de son départ et les larmes sur son visage.
Experte de contenu — Réponse : Renforcée. Justification : S'assurer qu'elle est dans un état adéquat pour rentrer; ne pas forcer, mais rester soucieuse et ouverte à comprendre la situation.
Panéliste #1 — Inchangée : Boucler la boucle avec cette candidature; on ne laisse pas quelqu'un en détresse.
Panéliste #2 — Fortement renforcée : Revenir rapidement sur la situation pour comprendre les raisons de sa fermeture et trouver des solutions.
Panéliste #4 — Affaiblie : La rencontrer pour comprendre son état; si elle est fermée, proposer une discussion le lendemain.
Panéliste #5 — Fortement affaiblie : Si le départ est au bout d'une matinée, juste remercier la personne et lui souhaiter bonne continuation.

Synthèse éducative — Bilan : Comprendre les raisons du départ de l'employée, sans tenir compte du fait qu'elle n'était pas le premier choix lors du processus de recrutement."""


_GRH_SITUATION_5 = """Situation #5 : Propos qui nuisent à la réputation de l'entreprise
Sandra est gestionnaire en ressources humaines depuis 2 ans. Elle vient d'apprendre que Jonathan a publié sur les réseaux sociaux un message dans lequel il dénigre leur entreprise. C'est la deuxième fois que Jonathan publie un message nuisant à la réputation de l'entreprise, alors que cela fait partie de son contrat de travail.

Scénario 1
Comportement observé : Sandra rencontre Jonathan pour lui donner un avis verbal.
Experte de contenu — Réponse : Tout à fait acceptable. Justification : C'est une deuxième situation déjà adressée dans le passé; un fait concret pour intervenir.
Panéliste #2 — Tout à fait inacceptable : Important de le rencontrer pour qu'il comprenne l'impact de ses commentaires et comprendre pourquoi il les a faits; s'il vit des frustrations, il doit s'adresser aux bonnes personnes.
Panéliste #3 — Acceptable : Rencontrer l'employé; possiblement avis verbal, ou écrit selon ce qui a été fait à la première offense et la nature des propos; réviser les obligations de loyauté.
Panéliste #4 — Acceptable : Vérifier les faits; s'ils sont véridiques et vu la gravité et les attentes claires, un avertissement verbal est approprié, en rappelant les attentes et conséquences.
Panéliste #5 — Tout à fait acceptable : On ne peut pas tolérer cela, mais il faut une sensibilisation.

Scénario 2
Comportement observé : Après avoir validé les faits, Sandra rencontre immédiatement Jonathan pour le suspendre 2 jours.
Experte de contenu — Réponse : Inacceptable. Justification : Si la première fois aucune mesure disciplinaire n'a été appliquée, il faut une gradation des sanctions, en tenant compte de la gravité du message.
Panéliste #2 — Inacceptable : La suspension n'est peut-être pas la bonne solution sans d'abord connaître les raisons; gradation des sanctions selon la nature des propos.
Panéliste #4 — Inacceptable : La suspension semble excessive; l'avis verbal serait la première action selon le principe de gradation des sanctions.
Panéliste #5 — Inacceptable : La suspension est trop lourde; lui faire prendre conscience avant tout.

Scénario 3
Comportement observé : Sandra congédie immédiatement Jonathan.
Experte de contenu — Réponse : Tout à fait inacceptable. Justification : Il faut un processus de gradation des sanctions; c'est une deuxième situation à ce stade.
Panéliste #2 — Inacceptable : Jonathan doit d'abord être rencontré avec une gradation des sanctions; comprendre l'impact de ses gestes et ses frustrations.
Panéliste #4 — Tout à fait inacceptable : Sandra n'a pas vérifié les faits ni évalué la gravité; mesure inappropriée qui expose l'entreprise à des risques.
Panéliste #5 — Tout à fait inacceptable : Non-respect de la gradation des sanctions.

Synthèse éducative — Bilan : Il est important de sensibiliser l'employé et d'expliquer les comportements attendus. Au besoin, une sanction peut être appliquée selon la gravité du geste et l'échelle de gradation prévue par l'organisation."""


_GRH_SITUATION_6 = """Situation #6 : Conflit d'intérêts
Jérôme apprend que deux employés, Justine et Pierre-Luc, ont développé une relation amoureuse. Depuis qu'ils travaillent sur le projet ensemble, ils se fréquentent à l'extérieur du travail. Pierre-Luc confie à Jérôme qu'il a développé des sentiments pour Justine depuis 1 mois. Justine est la gestionnaire d'une équipe dans laquelle travaille Pierre-Luc.

Scénario 1
Comportement observé : Jérôme rencontre Justine pour clarifier ses attentes sur les comportements attendus entre Justine et Pierre-Luc au travail et la sensibiliser à ses potentiels enjeux de crédibilité en tant que gestionnaire.
Experte de contenu — Réponse : Tout à fait acceptable. Justification : Pertinent d'adresser la situation et le possible conflit d'intérêts, et de sensibiliser la gestionnaire quant à sa posture et sa crédibilité.
Panéliste #2 — Inacceptable : On ne peut empêcher les gens de tomber amoureux, mais comme Justine est la gestionnaire de Pierre-Luc, il faut changer l'une des deux personnes d'équipe pour éviter des enjeux de crédibilité ou de favoritisme.
Panéliste #3 — Acceptable : Rencontrer Justine et Pierre-Luc séparément, s'assurer du respect des politiques (harcèlement) et défaire la relation de supervision.
Panéliste #4 — Acceptable : Rien ne confirme une relation; discuter avec Justine pour comprendre, sans présumer; clarifier les attentes serait peut-être prématuré.
Panéliste #5 — Tout à fait acceptable : Aborder le sujet et la perception des autres, et envisager un changement de département, de superviseur ou d'entreprise.

Scénario 2
Comportement observé : Jérôme rencontre conjointement Justine et Pierre-Luc pour leur annoncer qu'un des deux doit quitter l'organisation s'il souhaite poursuivre la relation, car ils sont en conflit d'intérêts.
Experte de contenu — Réponse : Inacceptable. Justification : Si rien n'est mentionné dans leurs contrats, ce n'est pas une bonne première étape.
Panéliste #2 — Inacceptable : La relation ne peut perdurer dans le contexte actuel; s'il n'est pas possible de changer l'un d'équipe, alors préférable que l'un quitte pour crédibilité et justice.
Panéliste #4 — Inacceptable : Prématuré sans d'abord discuter avec Justine; explorer d'autres options comme la réorganisation des lignes hiérarchiques ou un transfert.
Panéliste #5 — Acceptable : Avoir un discours commun pour expliquer les impacts et les perceptions des autres.

Scénario 3
Comportement observé : Jérôme est vigilant en ce qui concerne la situation, mais n'intervient pas pour l'instant.
Experte de contenu — Réponse : Inacceptable. Justification : Jérôme devrait rencontrer Justine et Pierre-Luc individuellement pour les sensibiliser à l'enjeu éthique et au possible conflit d'intérêts.
Panéliste #2 — Inacceptable : Il doit y avoir une intervention, car cela peut nuire à la crédibilité et favoriser un sentiment d'injustice; une politique claire doit être en place.
Panéliste #4 — Inacceptable : Pertinent d'avoir une discussion avec Justine, avec tact et objectivité, selon que la relation existe ou non.
Panéliste #5 — Tout à fait inacceptable : Il faut intervenir dès qu'on le sait.

Synthèse éducative — Bilan : Il faut intervenir rapidement auprès de Justine et Pierre-Luc. Compte tenu du poste de gestionnaire de Justine, il faut réorganiser les équipes afin d'éviter un conflit d'intérêts."""


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
