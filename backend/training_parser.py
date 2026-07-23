"""
Parser for the marker-delimited training text used in ``trainings_2_experts.py``.

Turns a raw module string (``training_1`` / ``training_2`` / ``training_3``) into a
structured object:

    {
      "module_title": "Module 1 : Diagnostic et suivi de la migraine",
      "situations": [
        {
          "situation_index": 1,
          "text": "Vous voyez en clinique externe ...",
          "scenarios": [
            {
              "scenario_index": 1,
              "hypothesis": "Migraine",
              "new_information": "Elle vous décrit la douleur ...",
              "experts": [
                {"expert_label": "Expert 2", "likert": "Renforcée", "justification": "..."},
                ...
              ],
            },
            ...
          ],
        },
        ...
      ],
    }

The learner ("Learner's Response") blocks are intentionally ignored — real users
now supply their own answers.

The same structure is used both for seeding Supabase and for rebuilding the
evaluator input text from the DB (see ``build_evaluation_input``).
"""

import re
import unicodedata
from typing import Dict, List

# Canonical Learning-by-Concordance Likert values (must match the DB enum).
LIKERT_VALUES = [
    "Fortement affaiblie",
    "Affaiblie",
    "Inchangée",
    "Renforcée",
    "Fortement renforcée",
]


def _norm(s: str) -> str:
    """Lowercase + strip accents for fuzzy matching."""
    s = unicodedata.normalize("NFD", s)
    s = "".join(c for c in s if unicodedata.category(c) != "Mn")
    return s.lower().strip()


_LIKERT_LOOKUP = {_norm(v): v for v in LIKERT_VALUES}


def normalize_likert(raw: str) -> str:
    """Map a raw 'Reponse: ...' value to a canonical Likert value."""
    key = _norm(raw)
    # Trim trailing punctuation / stray words.
    key = re.sub(r"[^a-z ]", "", key).strip()
    if key in _LIKERT_LOOKUP:
        return _LIKERT_LOOKUP[key]
    # Fall back to longest canonical value contained in the string.
    for norm_key, canonical in sorted(_LIKERT_LOOKUP.items(), key=lambda kv: -len(kv[0])):
        if norm_key in key:
            return canonical
    raise ValueError(f"Unrecognized Likert value: {raw!r}")


_SITUATION_RE = re.compile(r"<Situation (\d+)>\s*(.*?)</Situation \d+>", re.DOTALL)
_SCENARIO_RE = re.compile(r"<Scenario (\d+)>\s*(.*?)</Scenario \d+>", re.DOTALL)
_SITUATION_LABEL_RE = re.compile(r"^Situation\s*\d+\s*:?\s*", re.IGNORECASE)
_SCENARIO_LABEL_RE = re.compile(r"^Scenario\s*\d+\s*:?\s*", re.IGNORECASE)


def _clean_hypothesis(raw: str) -> str:
    raw = raw.strip()
    raw = re.sub(r"^\.*\s*", "", raw)          # leading "..."
    raw = re.sub(r"^\d+\s*[-.)]\s*", "", raw)  # leading "2- " / "3. "
    return raw.strip()


def _parse_experts(block: str) -> List[Dict[str, str]]:
    """Parse the 'Experts' Responses:' portion of a scenario body."""
    experts: List[Dict[str, str]] = []
    # Split on each "Expert N:" header, keeping the label.
    parts = re.split(r"(Expert\s*\d+)\s*:", block)
    # parts = [pre, "Expert 2", body2, "Expert 3", body3, ...]
    for i in range(1, len(parts) - 1, 2):
        label = re.sub(r"\s+", " ", parts[i].strip())
        body = parts[i + 1]
        m_rep = re.search(r"Reponse\s*:\s*(.+?)(?:\n|Justification\s*:)", body, re.DOTALL | re.IGNORECASE)
        m_just = re.search(r"Justification\s*:\s*(.+)", body, re.DOTALL | re.IGNORECASE)
        if not m_rep:
            continue
        likert = normalize_likert(m_rep.group(1))
        justification = (m_just.group(1).strip() if m_just else "").strip()
        experts.append({
            "expert_label": label,
            "likert": likert,
            "justification": justification,
        })
    return experts


def _parse_scenario(idx: int, body: str) -> Dict[str, object]:
    body = _SCENARIO_LABEL_RE.sub("", body.strip(), count=1)
    # hypothesis: between "Si vous pensiez" [à] and "Et qu'alors"
    m_hyp = re.search(
        r"Si vous pensiez\s*(?:à)?\s*\.*\s*(.*?)\s*Et qu[’'`]?\s*alors",
        body, re.DOTALL | re.IGNORECASE,
    )
    # new_information: between "Et qu'alors" and "Experts' Responses"
    m_new = re.search(
        r"Et qu[’'`]?\s*alors\s*\.*\s*(.*?)\s*Experts?[’'`]?\s*Responses?\s*:",
        body, re.DOTALL | re.IGNORECASE,
    )
    hypothesis = _clean_hypothesis(m_hyp.group(1)) if m_hyp else ""
    new_information = (m_new.group(1).strip() if m_new else "")
    # experts: from "Experts' Responses:" up to "Learner's Response:" (or end)
    m_exp_block = re.search(
        r"Experts?[’'`]?\s*Responses?\s*:(.*?)(?:Learner[’'`]?s?\s*Response\s*:|$)",
        body, re.DOTALL | re.IGNORECASE,
    )
    experts = _parse_experts(m_exp_block.group(1)) if m_exp_block else []
    return {
        "scenario_index": idx,
        "hypothesis": hypothesis,
        "new_information": new_information,
        "experts": experts,
    }


def parse_module(module_text: str) -> Dict[str, object]:
    """Parse one training module string into structured situations/scenarios/experts."""
    # module title = first non-empty line after "Trainings Content:"
    module_title = ""
    m_title = re.search(r"Trainings? Content\s*:\s*\n+\s*(.+)", module_text)
    if m_title:
        module_title = m_title.group(1).strip()

    situations: List[Dict[str, object]] = []
    for sm in _SITUATION_RE.finditer(module_text):
        s_idx = int(sm.group(1))
        s_body = sm.group(2)
        # situation text = everything up to the first <Scenario ...>
        text_part = s_body.split("<Scenario", 1)[0]
        text = _SITUATION_LABEL_RE.sub("", text_part.strip(), count=1).strip()
        scenarios = [
            _parse_scenario(int(cm.group(1)), cm.group(2))
            for cm in _SCENARIO_RE.finditer(s_body)
        ]
        situations.append({
            "situation_index": s_idx,
            "text": text,
            "scenarios": scenarios,
        })
    return {"module_title": module_title, "situations": situations}


def parse_objectives(objectives_text: str) -> List[str]:
    """Parse the '- item' bullet list from a training_objectives string."""
    return [
        line.strip()[1:].strip()
        for line in objectives_text.splitlines()
        if line.strip().startswith("-")
    ]


def build_evaluation_input(
    training_title: str,
    objectives: List[str],
    situations: List[Dict[str, object]],
    responses_by_scenario: Dict[str, Dict[str, str]],
) -> str:
    """
    Rebuild the marker-delimited training text the evaluator expects, from DB
    content + the learner's typed answers.

    ``situations`` is the nested structure from ``repo.get_training_content(
    include_experts=True)`` — each situation has ``scenarios``, each scenario has
    ``experts`` [{expert_label, likert, justification}] and an ``id``.
    ``responses_by_scenario`` maps scenario id -> {"likert", "justification"}.
    """
    lines: List[str] = []
    lines.append("Now analyze the learner's responses to the following training.\n")
    lines.append("Training Objectives:")
    for obj in objectives:
        lines.append(f"- {obj}")
    lines.append("\nTrainings Content:\n")
    lines.append(training_title + "\n")

    for s_i, sit in enumerate(situations, start=1):
        lines.append(f"<Situation {s_i}>")
        lines.append(f"Situation {s_i}:")
        lines.append(str(sit.get("text", "")).strip() + "\n")
        for c_i, sc in enumerate(sit.get("scenarios", []), start=1):
            lines.append(f"<Scenario {c_i}>")
            lines.append(f"Scenario {c_i}:")
            lines.append("Si vous pensiez ...")
            lines.append(str(sc.get("hypothesis", "")).strip())
            lines.append("Et qu'alors ...")
            lines.append(str(sc.get("new_information", "")).strip() + "\n")
            lines.append("Experts' Responses:\n")
            for e in sc.get("experts", []):
                lines.append(f"{e['expert_label']}:")
                lines.append(f"Reponse: {e['likert']}")
                lines.append(f"Justification: {e['justification']}\n")
            resp = responses_by_scenario.get(sc.get("id"), {})
            lines.append("Learner's Response:")
            lines.append(f"Reponse: {resp.get('likert') or '(aucune)'}")
            lines.append(f"Justification: {resp.get('justification') or '(aucune justification fournie)'}")
            lines.append(f"</Scenario {c_i}>\n")
        lines.append(f"</Situation {s_i}>\n")

    return "\n".join(lines)


def situation_title(text: str, index: int) -> str:
    """Short heading derived from the situation text (first line, truncated)."""
    first = text.split("\n", 1)[0].strip()
    if not first:
        return f"Situation {index}"
    return first if len(first) <= 70 else first[:67].rstrip() + "…"
