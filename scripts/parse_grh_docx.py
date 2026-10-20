#!/usr/bin/env python3
"""
Offline parser for the GRH (human resources management) concordance Word document
→ ``data/grh_trainings.json``.

Run this ONCE locally when the source .docx changes; the JSON it produces is committed
and is what ``scripts/seed_grh.py`` reads. Like ``parse_hci_docx.py``, the document
parsing deliberately never runs in production — it is brittle by nature, and the
committed JSON is reviewable.

The document is a SENSAI export: a *fiche descriptive* (title, objectives, ...) then two
situations, each followed by its scenarios and a *Synthèse éducative*. Unlike the other
content sets it mixes two scenario formats, which is why scenarios carry their own
``kind`` and (when it differs from the training's) ``likert_scale``:

- *Raisonnement* — "Si vous pensiez à… (votre hypothèse d'action)" / "Et qu'alors vous
  savez que… (nouvelle information)", on the ``pertinence_relative`` scale.
- *Jugement*     — a single "Comportement observé" to judge, no new information, on the
  4-value ``acceptabilite`` scale.

    top level → {activity_title, domain, likert_scale, objectives[], situations[]}
    situation → {index, title, text, educational_synthesis, scenarios[]}
    scenario  → {kind, likert_scale, hypothesis, new_information, experts[]}
    expert    → {expert_label, likert, justification}

Everything is positional: a marker row ("Si vous pensiez…", "Comportement observé :",
"Expert 2 : …", "Synthèse éducative") says what the *next* row holds. The source is
hand-authored and inconsistent ("Réponse Panéliste #1 :", "Expert #1 :", "Expert 2
Acceptable", justifications with or without their "Justification :" prefix), so the
markers are matched loosely and the result is validated against expected totals.

Dropped on purpose: scenario titles and image references (the schema has no slot for
them, and one title in situation 2 is a copy-paste of situation 1's).

Usage:
    ./venv/bin/python scripts/parse_grh_docx.py [path/to/SS_Formation-GRH-Demo_FR-LL_20260826.docx]
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.likert import SCALES, values_for  # noqa: E402

DEFAULT_DOCX = Path.home() / "Downloads" / "SS_Formation-GRH-Demo_FR-LL_20260826.docx"
OUT_PATH = ROOT_DIR / "data" / "grh_trainings.json"

ACTIVITY_TITLE = "Gestion des ressources humaines"
DOMAIN = "grh"
LIKERT_SCALE = "pertinence_relative"  # the training default — the raisonnement scenarios
JUDGMENT_SCALE = "acceptabilite"      # the per-scenario override for jugement scenarios

# Expected totals — the document is hand-authored, so assert rather than trust.
EXPECT_SCENARIOS_PER_SITUATION = [4, 3]
EXPECT_EXPERTS_PER_SCENARIO = 3
EXPECT_OBJECTIVES = 2

# --- markers, as they appear in the document ---------------------------------
RE_SITUATION = re.compile(r"^Situation\s*#?\s*(\d+)\s*:\s*(.+)$")
RE_SCENARIO = re.compile(r"^Scénario\s+(\d+)\b", re.IGNORECASE)
RE_EXPERT = re.compile(r"^(?:Réponses?\s+)?(?:Expert|Panéliste)\s*#?\s*(\d+)\s*:?\s*(.*)$",
                       re.IGNORECASE)
RE_JUSTIFICATION = re.compile(r"^Justification\s*[:/]?\s*", re.IGNORECASE)
M_OBJECTIVES = "Objectifs"
M_PAIR = "Si vous pensiez"
M_BEHAVIOUR = "Comportement observé"
M_QUESTIONS = ("Cette nouvelle information rend", "Le comportement observé est")
M_SYNTHESIS = "Synthèse éducative"
SKIPPED_PREFIXES = ("Titre :", "Image :", "Échelle de Likert")


# ---------------------------------------------------------------- doc reading
def _clean(text: str) -> str:
    """Collapse the whitespace Word scatters through a cell."""
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def _lines(text: str) -> List[str]:
    """A cell's non-empty lines, each cleaned — for multi-line cells (options, synthesis)."""
    return [c for c in (_clean(line) for line in text.split("\n")) if c]


def _items(document) -> List[Dict[str, Any]]:
    """
    The body flattened into ordered items: ``{"p": text}`` for a paragraph, or
    ``{"cells": [raw text, ...]}`` for a table row. Merged cells come back once per grid
    column with the same text, so consecutive duplicates are dropped.
    """
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    out: List[Dict[str, Any]] = []
    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            text = _clean(Paragraph(child, document).text)
            if text:
                out.append({"p": text})
        elif child.tag == qn("w:tbl"):
            for row in Table(child, document).rows:
                cells: List[str] = []
                for cell in row.cells:
                    raw = cell.text.strip()
                    if not cells or _clean(raw) != _clean(cells[-1]):
                        cells.append(raw)
                if any(_clean(c) for c in cells):
                    out.append({"cells": cells})
    return out


def _on_scale(raw: str, scale: str) -> str:
    """The scale value ``raw`` names (case/space-insensitive), or ``raw`` cleaned if none."""
    text = _clean(raw)
    for value in values_for(scale):
        if value.lower() == text.lower():
            return value
    return text


# --------------------------------------------------------------------- parse
def parse(docx_path: Path) -> Dict[str, Any]:
    import docx

    objectives: List[str] = []
    situations: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    scenario: Optional[Dict[str, Any]] = None
    expert: Optional[Dict[str, Any]] = None
    pending: Optional[str] = None  # what the next row holds

    for item in _items(docx.Document(str(docx_path))):
        if "p" in item:
            m = RE_SITUATION.match(item["p"])
            if m:
                current = {
                    "index": int(m.group(1)),
                    "title": _clean(m.group(2)),
                    "text": "",
                    "educational_synthesis": None,
                    "scenarios": [],
                }
                situations.append(current)
                scenario = expert = pending = None
            continue

        cells = item["cells"]
        first = _clean(cells[0])

        if current is None:
            # The fiche descriptive: only the objectives are kept.
            if first.startswith(M_OBJECTIVES):
                objectives = [line for line in _lines(cells[-1])
                              if not line.startswith(M_OBJECTIVES)]
            continue

        # ---- rows whose content was announced by the previous row
        if pending == "pair" and scenario is not None:
            scenario["kind"] = "reasoning"
            scenario["hypothesis"] = first
            scenario["new_information"] = _clean(cells[1]) if len(cells) > 1 else ""
            pending = None
            continue
        if pending == "behaviour" and scenario is not None:
            scenario["kind"] = "judgment"
            scenario["likert_scale"] = JUDGMENT_SCALE
            scenario["hypothesis"] = first
            scenario["new_information"] = ""
            pending = None
            continue
        if pending == "options" and scenario is not None:
            scenario["_options"] = _lines(cells[0])
            pending = None
            continue
        if pending == "justification" and expert is not None:
            expert["justification"] = _clean(RE_JUSTIFICATION.sub("", first))
            pending = None
            continue
        if pending == "synthesis":
            current["educational_synthesis"] = "\n".join(_lines(cells[0]))
            pending = None
            continue

        # ---- marker rows
        if RE_SCENARIO.match(first):
            scenario = {"kind": "", "likert_scale": None, "hypothesis": "",
                        "new_information": "", "experts": []}
            current["scenarios"].append(scenario)
            expert = None
            continue
        if first.startswith(M_PAIR):
            pending = "pair"
            continue
        if first.startswith(M_BEHAVIOUR):
            pending = "behaviour"
            continue
        if first.startswith(M_QUESTIONS):
            pending = "options"
            continue
        if first == M_SYNTHESIS:
            pending = "synthesis"
            scenario = expert = None
            continue
        m = RE_EXPERT.match(first)
        if m and scenario is not None:
            scale = scenario["likert_scale"] or LIKERT_SCALE
            expert = {
                "expert_label": f"Expert {int(m.group(1))}",
                "likert": _on_scale(m.group(2), scale),
                "justification": "",
            }
            scenario["experts"].append(expert)
            pending = "justification"
            continue
        if first.startswith(SKIPPED_PREFIXES):
            continue

        # ---- the situation's own text: the first free row before any scenario
        if scenario is None and not current["text"]:
            current["text"] = first

    return {
        "activity_title": ACTIVITY_TITLE,
        "domain": DOMAIN,
        "likert_scale": LIKERT_SCALE,
        "objectives": objectives,
        "situations": situations,
    }


# ------------------------------------------------------------------ validate
def validate(data: Dict[str, Any]) -> None:
    errors: List[str] = []
    for scale in (data["likert_scale"], JUDGMENT_SCALE):
        if scale not in SCALES:
            print(f"❌ Unknown likert scale {scale!r} — add it to backend/likert.py")
            sys.exit(1)

    if len(data["objectives"]) != EXPECT_OBJECTIVES:
        errors.append(f"expected {EXPECT_OBJECTIVES} objectives, got {len(data['objectives'])}")

    situations = data["situations"]
    counts = [len(s["scenarios"]) for s in situations]
    if counts != EXPECT_SCENARIOS_PER_SITUATION:
        errors.append(f"expected scenarios per situation {EXPECT_SCENARIOS_PER_SITUATION}, got {counts}")

    for sit in situations:
        where = f"situation {sit['index']}"
        if not sit["text"]:
            errors.append(f"{where}: empty situation text")
        if not sit["educational_synthesis"]:
            errors.append(f"{where}: no synthèse éducative")
        for c_i, sc in enumerate(sit["scenarios"], start=1):
            at = f"{where} / scenario {c_i}"
            scale = sc["likert_scale"] or data["likert_scale"]
            allowed = values_for(scale)
            options = sc.pop("_options", None)
            if options is not None and options != allowed:
                errors.append(f"{at}: the document's scale {options} is not '{scale}' {allowed}")
            if sc["kind"] not in ("reasoning", "judgment"):
                errors.append(f"{at}: could not tell the scenario format")
            if not sc["hypothesis"]:
                errors.append(f"{at}: empty hypothesis / observed behaviour")
            if sc["kind"] == "reasoning" and not sc["new_information"]:
                errors.append(f"{at}: empty new_information")
            if len(sc["experts"]) != EXPECT_EXPERTS_PER_SCENARIO:
                errors.append(f"{at}: expected {EXPECT_EXPERTS_PER_SCENARIO} experts, "
                              f"got {len(sc['experts'])}")
            labels = [e["expert_label"] for e in sc["experts"]]
            if len(set(labels)) != len(labels):
                errors.append(f"{at}: duplicate expert labels {labels}")
            for e in sc["experts"]:
                if e["likert"] not in allowed:
                    errors.append(f"{at}: {e['expert_label']} likert {e['likert']!r} is not on '{scale}'")
                if not e["justification"]:
                    errors.append(f"{at}: {e['expert_label']} has no justification")

    if errors:
        print("❌ Validation failed:")
        for e in errors:
            print(f"   - {e}")
        sys.exit(1)


def main() -> None:
    docx_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_DOCX
    if not docx_path.exists():
        print(f"❌ Document not found: {docx_path}")
        sys.exit(1)

    print(f"Parsing {docx_path} ...")
    data = parse(docx_path)
    validate(data)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"✅ Wrote {OUT_PATH.relative_to(ROOT_DIR)}")
    print(f"   activity : {data['activity_title']}")
    for sit in data["situations"]:
        kinds = ", ".join(sorted({sc["kind"] for sc in sit["scenarios"]}))
        print(f"   - {sit['title'][:52]:<52} {len(sit['scenarios'])} scenarios ({kinds})")


if __name__ == "__main__":
    main()
