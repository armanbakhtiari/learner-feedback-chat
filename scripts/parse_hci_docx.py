#!/usr/bin/env python3
"""
Offline parser for the IHM (human-computer interaction) concordance Word document
→ ``data/hci_trainings.json``.

Run this ONCE locally when the source .docx changes; the JSON it produces is committed
and is what ``scripts/seed_hci.py`` reads. Like ``parse_training_pdf.py``, the document
parsing deliberately never runs in production — it is brittle by nature, and the
committed JSON is reviewable.

The document holds one *activity* followed by 10 *situations*, each with its own three
learning objectives and five scenarios. The output mirrors ``data/gastro_trainings.json``
with one documented addition — ``objectives`` is carried **per situation** rather than as
a single flat list, because eight of these situations become their own bank trainings and
the suggestion query agent embeds each training's objectives:

    top level → {activity_title, domain, likert_scale, entry_point_objectives, situations[]}
    situation → {index, title, text, educational_synthesis, objectives[], scenarios[]}
    scenario  → {title, hypothesis, new_information, experts[]}
    expert    → {expert_label, likert, justification}

Two source features are deliberately dropped:

- the per-scenario difficulty level ("Niveau 2 — MOYEN"). The schema has no slot for it,
  and a visible difficulty grade reads as a score, which Learning by Concordance avoids.
- ``educational_synthesis`` — this document has none, so it is emitted as ``null``. The
  column is nullable and ``pipeline._educational_synthesis`` simply passes no expert
  grounding block to the feedback agent. Do not invent one.

Usage:
    ./venv/bin/python scripts/parse_hci_docx.py [path/to/Formations_concordance_IHM_LOG2420.docx]
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT_DIR = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT_DIR))

from backend.likert import SCALES, values_for  # noqa: E402

DEFAULT_DOCX = (
    ROOT_DIR.parent / "Docs" / "HCI-trainings" / "Formations_concordance_IHM_LOG2420.docx"
)
OUT_PATH = ROOT_DIR / "data" / "hci_trainings.json"

ACTIVITY_TITLE = "Interaction humain-machine"
DOMAIN = "ihm"
LIKERT_SCALE = "appropriee"

# The first two situations are merged into the single mandatory entry point, so their
# six objectives are replaced by one broader set that encompasses both. Authored here
# rather than in the seeder so that the committed JSON is the whole content of record.
ENTRY_POINT_TITLE = "Cycle de développement et planification centrée utilisateur"
ENTRY_POINT_OBJECTIVES = [
    "Choisir un cycle de développement adapté au caractère volatil des exigences "
    "utilisateur d'une application interactive, et distinguer un processus agile d'un "
    "processus réellement centré utilisateur.",
    "Justifier le recours aux itérations et aux maquettes dès la définition des exigences "
    "par le coût croissant des changements d'exigences.",
    "Structurer une analyse coût-bénéfice de l'utilisabilité et en identifier les "
    "variables déterminantes.",
    "Utiliser cette analyse pour dimensionner l'effort d'utilisabilité et le nombre "
    "d'itérations à l'étape de planification du cycle ISO 9241-210.",
    "Formuler les objectifs et les engagements d'un projet en termes de ce que "
    "l'utilisateur accomplit avec l'interface.",
]

# Expected totals — the document is hand-authored, so assert rather than trust.
EXPECT_SITUATIONS = 10
EXPECT_SCENARIOS = 50
EXPECT_EXPERTS = 150
EXPECT_OBJECTIVES_PER_SITUATION = 3
EXPECT_EXPERTS_PER_SCENARIO = 3

# --- section markers, exactly as they appear in the document -----------------
RE_SITUATION = re.compile(r"^Situation\s+(\d+)\s*[—–-]\s*(.+)$")
RE_SCENARIO = re.compile(r"^Scénario\s+(\d+)\.(\d+)\b")
M_OBJECTIVES = "Objectifs d'apprentissage"
M_CONTEXT = "Mise en situation"
M_EXPERTS = "Réponses des experts"

RE_HYPOTHESIS = re.compile(r"^Si vous pensiez\s*(?:à|que)?\s*[…\.]{1,3}\s*")
RE_NEW_INFO = re.compile(r"^Et qu[’'`]alors\s*[…\.]{1,3}\s*")
RE_BULLET = re.compile(r"^[•·\-–•]\s*")


# ---------------------------------------------------------------- doc reading
def _blocks(document) -> List[Dict[str, Any]]:
    """
    The document body flattened into ordered blocks, because the parse is positional:
    a heading is followed by the table that belongs to it.

    Each block is ``{"kind": "p", "text": str}`` or ``{"kind": "tbl", "rows": [[str]]}``.
    """
    from docx.oxml.ns import qn
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    out: List[Dict[str, Any]] = []
    for child in document.element.body.iterchildren():
        if child.tag == qn("w:p"):
            text = Paragraph(child, document).text.strip()
            if text:
                out.append({"kind": "p", "text": text})
        elif child.tag == qn("w:tbl"):
            rows = [[cell.text.strip() for cell in row.cells] for row in Table(child, document).rows]
            out.append({"kind": "tbl", "rows": rows})
    return out


def _clean(text: str) -> str:
    """Collapse the whitespace Word scatters through a cell."""
    return re.sub(r"\s+", " ", text.replace("\xa0", " ")).strip()


def _objectives_from(rows: List[List[str]]) -> List[str]:
    """The objectives table is a single cell: a header line then one line per bullet."""
    cell = rows[0][0]
    lines = [_clean(RE_BULLET.sub("", line)) for line in cell.split("\n")]
    return [line for line in lines if line and not line.startswith(M_OBJECTIVES)]


def _scenario_from(rows: List[List[str]]) -> Dict[str, str]:
    """
    The scenario table is two single-cell rows, "Si vous pensiez à …" then "Et qu'alors …".
    The lead-in is stripped so the stored text starts at the substance, matching what
    ``backend/training_parser._clean_hypothesis`` produces for the migraine content.
    """
    hypothesis = new_information = ""
    for row in rows:
        text = _clean(row[0])
        if RE_HYPOTHESIS.match(text):
            hypothesis = RE_HYPOTHESIS.sub("", text)
        elif RE_NEW_INFO.match(text):
            new_information = RE_NEW_INFO.sub("", text)
    return {"hypothesis": hypothesis, "new_information": new_information}


def _experts_from(rows: List[List[str]]) -> List[Dict[str, str]]:
    """The expert table is a header row then one row per expert: label | réponse | justification."""
    experts: List[Dict[str, str]] = []
    for row in rows:
        if len(row) < 3:
            continue
        label, likert, justification = (_clean(c) for c in row[:3])
        if not label.lower().startswith("expert") or likert.lower() == "réponse":
            continue
        experts.append(
            {"expert_label": label, "likert": likert, "justification": justification}
        )
    return experts


# --------------------------------------------------------------------- parse
def parse(docx_path: Path) -> Dict[str, Any]:
    import docx

    blocks = _blocks(docx.Document(str(docx_path)))

    situations: List[Dict[str, Any]] = []
    current: Optional[Dict[str, Any]] = None
    scenario: Optional[Dict[str, Any]] = None
    pending: Optional[str] = None  # which table the last heading is expecting

    for block in blocks:
        if block["kind"] == "p":
            text = _clean(block["text"])

            m = RE_SITUATION.match(text)
            if m:
                current = {
                    # The "Situation N — " prefix is dropped: the seeder builds each
                    # training's title as "{activity} — {situation title}", where the
                    # prefix would read as noise.
                    "index": int(m.group(1)),
                    "title": _clean(m.group(2)),
                    "text": "",
                    "educational_synthesis": None,
                    "objectives": [],
                    "scenarios": [],
                }
                situations.append(current)
                scenario = None
                pending = "objectives"
                continue

            if current is None:
                continue  # front matter (cover page, table of contents)

            m = RE_SCENARIO.match(text)
            if m:
                # The "Niveau k — LABEL" suffix is intentionally discarded.
                scenario = {
                    "title": f"Scénario {m.group(1)}.{m.group(2)}",
                    "hypothesis": "",
                    "new_information": "",
                    "experts": [],
                }
                current["scenarios"].append(scenario)
                pending = "scenario"
                continue

            if text.startswith(M_CONTEXT):
                pending = "context"
                continue
            if text.startswith(M_EXPERTS):
                pending = "experts"
                continue

            if pending == "context" and not current["text"]:
                current["text"] = text
                pending = None
            continue

        # a table — belongs to whatever heading came last
        if current is None:
            continue  # the cover-page "Consigne" table
        if pending == "objectives":
            current["objectives"] = _objectives_from(block["rows"])
        elif pending == "scenario" and scenario is not None:
            scenario.update(_scenario_from(block["rows"]))
        elif pending == "experts" and scenario is not None:
            scenario["experts"] = _experts_from(block["rows"])
        pending = None

    return {
        "activity_title": ACTIVITY_TITLE,
        "domain": DOMAIN,
        "likert_scale": LIKERT_SCALE,
        "entry_point_title": ENTRY_POINT_TITLE,
        "entry_point_objectives": ENTRY_POINT_OBJECTIVES,
        "situations": situations,
    }


# ------------------------------------------------------------------ validate
def validate(data: Dict[str, Any]) -> None:
    errors: List[str] = []
    if data["likert_scale"] not in SCALES:
        print(f"❌ Unknown likert scale {data['likert_scale']!r} — add it to backend/likert.py")
        sys.exit(1)
    allowed = values_for(data["likert_scale"])

    situations = data["situations"]
    if len(situations) != EXPECT_SITUATIONS:
        errors.append(f"expected {EXPECT_SITUATIONS} situations, got {len(situations)}")

    n_scenarios = n_experts = 0
    for sit in situations:
        where = sit["title"][:40]
        if not sit["text"]:
            errors.append(f"{where!r}: empty situation text")
        if len(sit["objectives"]) != EXPECT_OBJECTIVES_PER_SITUATION:
            errors.append(
                f"{where!r}: expected {EXPECT_OBJECTIVES_PER_SITUATION} objectives, "
                f"got {len(sit['objectives'])}"
            )
        n_scenarios += len(sit["scenarios"])
        for sc in sit["scenarios"]:
            for field in ("hypothesis", "new_information"):
                if not sc[field]:
                    errors.append(f"{sc['title']!r}: empty {field}")
            n_experts += len(sc["experts"])
            if len(sc["experts"]) != EXPECT_EXPERTS_PER_SCENARIO:
                errors.append(
                    f"{sc['title']!r}: expected {EXPECT_EXPERTS_PER_SCENARIO} experts, "
                    f"got {len(sc['experts'])}"
                )
            labels = [e["expert_label"] for e in sc["experts"]]
            if len(set(labels)) != len(labels):
                errors.append(f"{sc['title']!r}: duplicate expert labels {labels}")
            for e in sc["experts"]:
                if e["likert"] not in allowed:
                    errors.append(f"{sc['title']!r}: likert {e['likert']!r} is not on the scale")
                if not e["justification"]:
                    errors.append(f"{sc['title']!r}: {e['expert_label']} has no justification")

    if n_scenarios != EXPECT_SCENARIOS:
        errors.append(f"expected {EXPECT_SCENARIOS} scenarios, got {n_scenarios}")
    if n_experts != EXPECT_EXPERTS:
        errors.append(f"expected {EXPECT_EXPERTS} expert responses, got {n_experts}")

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
    print(f"   scale    : {data['likert_scale']}")
    for sit in data["situations"]:
        n_exp = sum(len(sc["experts"]) for sc in sit["scenarios"])
        print(f"   - {sit['title'][:52]:<52} {len(sit['scenarios'])} scenarios, {n_exp} experts")


if __name__ == "__main__":
    main()
