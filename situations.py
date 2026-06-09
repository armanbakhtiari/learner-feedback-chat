"""
All Situations (situation text only)
====================================

A catalogue of every situation across all available trainings — **only the situation
description**, with no scenarios, expert/panelist responses, or learner answers.

These objects are used by the scenario-generation feature (``backend/scenario_generator.py``)
to create brand-new Learning-by-Concordance scenarios for the *exact* situations a learner was
evaluated on, focused on the learner's learning gaps.

Each situation object is::

    {
        "id": str,                 # stable unique id, e.g. "migraine_training_1_s1"
        "training_type": str,      # "migraine" | "grh_1st" | "nursing_1st" | ...
        "module": str,             # "training_1" | "training_2" | "training_3"
        "situation_index": int,    # 1-based index within the module
        "title": str,              # short heading derived from the situation text
        "text": str,               # the situation description only
    }

The *evaluated* training is always ``training_1`` of the selected ``training_type``;
``get_situations_for_training`` returns exactly those situations.
"""

import re
import importlib
from typing import Dict, List

# training_type -> (module file, list of training-variable names defined in that file)
_TRAINING_SOURCES = {
    "migraine": ("trainings_2_experts", ["training_1", "training_2", "training_3"]),
    "grh_1st": ("trainings_grh_1stLearner", ["training_1"]),
    "nursing_1st": ("trainings_nursing_1stLearner", ["training_1"]),
    "nursing_2nd": ("trainings_nursing_2ndLearner", ["training_1"]),
    "leadership_1st": ("trainings_leadership_1srLearner", ["training_1"]),
    "leadership_2nd": ("trainings_leadership_2ndLearner", ["training_1"]),
    "leadership_3rd": ("trainings_leadership_3rdLearner", ["training_1"]),
}

# The module whose situations are the ones the learner is actually evaluated on.
EVALUATED_MODULE = "training_1"

# Captures everything from a "<Situation N>" marker up to the first "<Scenario" marker.
_SITUATION_BLOCK_RE = re.compile(r"<Situation (\d+)>\s*(.*?)(?=<Scenario)", re.DOTALL)
# Strips a leading "Situation N:" label from a situation body.
_SITUATION_LABEL_RE = re.compile(r"^Situation\s*\d+\s*:?\s*", re.IGNORECASE)


def _make_title(text: str, index: int) -> str:
    """Derive a short heading from the situation text (first line, truncated)."""
    first_line = text.split("\n", 1)[0].strip()
    if not first_line:
        return f"Situation {index}"
    return first_line if len(first_line) <= 70 else first_line[:67].rstrip() + "…"


def _extract_situations(module_text: str) -> List[Dict[str, object]]:
    """Extract (index, situation-description-only) pairs from a training module string."""
    results = []
    for match in _SITUATION_BLOCK_RE.finditer(module_text):
        idx = int(match.group(1))
        body = match.group(2).strip()
        body = _SITUATION_LABEL_RE.sub("", body, count=1).strip()
        if body:
            results.append((idx, body))
    return results


def _build_all_situations() -> List[Dict[str, object]]:
    entries: List[Dict[str, object]] = []
    for training_type, (module_name, var_names) in _TRAINING_SOURCES.items():
        try:
            module = importlib.import_module(module_name)
        except Exception as e:  # pragma: no cover - defensive
            print(f"⚠️ situations.py: could not import {module_name}: {e}")
            continue
        for module_var in var_names:
            module_text = getattr(module, module_var, None)
            if not module_text:
                continue
            for idx, text in _extract_situations(module_text):
                entries.append({
                    "id": f"{training_type}_{module_var}_s{idx}",
                    "training_type": training_type,
                    "module": module_var,
                    "situation_index": idx,
                    "title": _make_title(text, idx),
                    "text": text,
                })
    return entries


ALL_SITUATIONS: List[Dict[str, object]] = _build_all_situations()


def get_situations_for_training(training_type: str) -> List[Dict[str, object]]:
    """Return the situations of the *evaluated* module (training_1) for a training type."""
    return [
        s for s in ALL_SITUATIONS
        if s["training_type"] == training_type and s["module"] == EVALUATED_MODULE
    ]


def get_situation(situation_id: str) -> Dict[str, object]:
    """Return a single situation object by id, or an empty dict if not found."""
    for s in ALL_SITUATIONS:
        if s["id"] == situation_id:
            return s
    return {}
