"""
Learning-by-Concordance response scales.

A training declares which scale its scenarios use via ``trainings.likert_scale``:

- ``concordance`` — how the new information changes the strength of the hypothesis
  (the migraine content, and the default for anything that predates this column).
- ``pertinence``  — how pertinent the hypothesis/action remains (the gastroenterology
  content, which also contains action scenarios where "renforcée" would not read).

Both are ordered from most negative to most positive; index 2 is the neutral middle.
Every value here must exist in the ``likert_scale`` Postgres enum.
"""

from typing import List, Optional

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
}


def values_for(scale: Optional[str]) -> List[str]:
    """The ordered values of a scale, falling back to the default for unknown names."""
    return SCALES.get(scale or DEFAULT_SCALE, SCALES[DEFAULT_SCALE])


def neutral_for(scale: Optional[str]) -> str:
    """The middle ('no change') value — used as a fallback when an LLM goes off-script."""
    return values_for(scale)[2]


def coerce(value: Optional[str], scale: Optional[str]) -> str:
    """
    Snap an LLM-produced value onto the scale.

    Exact match first, then a case-insensitive match, then the neutral value — the
    structured-output models can no longer use a fixed ``Literal`` (they must serve two
    scales), so the guard lives here instead of in the schema.
    """
    values = values_for(scale)
    text = (value or "").strip()
    if text in values:
        return text
    lowered = text.lower()
    for v in values:
        if v.lower() == lowered:
            return v
    return values[2]
