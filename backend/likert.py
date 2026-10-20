"""
Learning-by-Concordance response scales.

A training declares which scale its scenarios use via ``trainings.likert_scale``; a
scenario may override it with ``scenarios.likert_scale`` (the GRH training mixes two
formats, each with its own scale — see ``scenario_scale``):

- ``concordance``         — how the new information changes the strength of the hypothesis
  (the migraine content, and the default for anything that predates this column).
- ``pertinence``          — how pertinent the hypothesis/action remains (the gastroenterology
  content, which also contains action scenarios where "renforcée" would not read).
- ``appropriee``          — whether the new information makes the proposed decision more or
  less appropriate (the human-computer interaction content). Until 2026-10 this scale was
  absolute ("Totalement inappropriée" .. "Totalement appropriée"); ``APPROPRIEE_LEGACY_MAP``
  maps those values onto the current ones.
- ``pertinence_relative`` — whether the new information makes the action hypothesis more or
  less pertinent (the GRH *raisonnement* scenarios).
- ``acceptabilite``       — how acceptable an observed behaviour is (the GRH *jugement*
  scenarios). Four values: there is deliberately no neutral middle.

Every scale is ordered from most negative to most positive. Every value here must exist in
the ``likert_scale`` Postgres enum.
"""

from typing import Any, Dict, List, Optional

DEFAULT_SCALE = "concordance"

SCALES = {
    "concordance": [
        "Fortement affaiblie",
        "Affaiblie",
        "Inchangée",
        "Renforcée",
        "Fortement renforcée",
    ],
    "pertinence": [
        "Pas du tout pertinente",
        "Peu pertinente",
        "Ni plus ni moins pertinente",
        "Pertinente",
        "Très pertinente",
    ],
    "appropriee": [
        "Beaucoup moins appropriée",
        "Moins appropriée",
        "Ni plus ni moins appropriée",
        "Plus appropriée",
        "Beaucoup plus appropriée",
    ],
    "pertinence_relative": [
        "Beaucoup moins pertinente",
        "Moins pertinente",
        "Ni plus ni moins pertinente",
        "Plus pertinente",
        "Beaucoup plus pertinente",
    ],
    "acceptabilite": [
        "Tout à fait inacceptable",
        "Inacceptable",
        "Acceptable",
        "Tout à fait acceptable",
    ],
}

# The former absolute ``appropriee`` values, mapped ordinally onto the relative ones.
# Used by scripts/parse_hci_docx.py (the source document still carries the old wording)
# and by scripts/migrate_ihm_relative_scale.py (rows stored before the change).
APPROPRIEE_LEGACY_MAP = {
    "Totalement inappropriée": "Beaucoup moins appropriée",
    "Inappropriée": "Moins appropriée",
    "Ni plus ni moins appropriée": "Ni plus ni moins appropriée",
    "Appropriée": "Plus appropriée",
    "Totalement appropriée": "Beaucoup plus appropriée",
}


def values_for(scale: Optional[str]) -> List[str]:
    """The ordered values of a scale, falling back to the default for unknown names."""
    return SCALES.get(scale or DEFAULT_SCALE, SCALES[DEFAULT_SCALE])


def scenario_scale(scenario: Dict[str, Any], training: Optional[Dict[str, Any]] = None) -> str:
    """The scale a scenario is answered on: its own override, else its training's."""
    return scenario.get("likert_scale") or (training or {}).get("likert_scale") or DEFAULT_SCALE


def neutral_for(scale: Optional[str]) -> str:
    """The middle value — used as a fallback when an LLM goes off-script."""
    values = values_for(scale)
    return values[len(values) // 2]


def coerce(value: Optional[str], scale: Optional[str]) -> str:
    """
    Snap an LLM-produced value onto the scale.

    Exact match first, then a case-insensitive match, then the middle value — the
    structured-output models can no longer use a fixed ``Literal`` (they must serve
    several scales), so the guard lives here instead of in the schema.
    """
    values = values_for(scale)
    text = (value or "").strip()
    if text in values:
        return text
    lowered = text.lower()
    for v in values:
        if v.lower() == lowered:
            return v
    return neutral_for(scale)
