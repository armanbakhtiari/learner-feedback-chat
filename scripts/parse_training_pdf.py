#!/usr/bin/env python3
"""
Offline parser for the SENSAI training-export PDF → ``data/gastro_trainings.json``.

Run this ONCE locally when the source PDF changes; the JSON it produces is committed
and is what ``scripts/seed_gastro.py`` reads. The PDF parsing deliberately never runs
in production — it is brittle by nature, and the committed JSON is reviewable.

The export has one *activity* (title, description, shared learning objectives) followed
by N *situations*. In this product **each situation is its own training**, so the parser
flattens to one entry per situation:

    situation → {title, text, educational_synthesis, scenarios[]}
    scenario  → {title, hypothesis, new_information, experts[]}
    expert    → {expert_label, likert, justification}

Panel members are anonymised: the identified clinician (an email address in the export)
becomes "Expert 1 (clinicien)" wherever it appears in the block, and the generated ones
become "Expert 2 (IA)" / "Expert 3 (IA)" in export order. The real address never reaches
the JSON or the database.

Usage:
    ./venv/bin/python scripts/parse_training_pdf.py [path/to/training_sensai.pdf]
"""

import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).parent.parent
DEFAULT_PDF = Path.home() / "Desktop" / "training_sensai.pdf"
OUT_PATH = ROOT_DIR / "data" / "gastro_trainings.json"

DOMAIN = "gastro"
LIKERT_SCALE = "pertinence"

# Expected totals — the export is hand-authored, so assert rather than trust.
EXPECT_SITUATIONS = 9
EXPECT_SCENARIOS = 30
EXPECT_EXPERTS = 90
EXPECT_OBJECTIVES = 14

# --- section markers, exactly as they appear in the export -------------------
M_OBJECTIVES = "Objectif(s) :"
M_SITUATIONS = "• Situations •"
M_SITUATION = "Titre de la situation :"
M_DESCRIPTION = "Description :"
M_SYNTHESIS = "• Synthèse éducative •"
M_SCENARIOS = "• Scénarios dans cette situation •"
M_SCENARIO = "• Titre du scénario:"
M_MEMBERS = "Réponses des membres:"
M_JUSTIFICATION = "Justification :"
M_LIKERT = "Score de l'échelle de Likert :"

# All four lead-in forms in the export: "Si vous pensiez …", "… pensiez à …",
# "… pensiez que …", "Si vous envisagiez …".
RE_HYPOTHESIS = re.compile(r"^Si vous(?: \w+){1,3}\s*[…\.]{1,3}\s*$")
RE_NEW_INFO = re.compile(r"^Et qu[’'`]alors\s*[…\.]{1,3}\s*$")
RE_EMAIL = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
RE_AI_MEMBER = re.compile(r"^Expert AI$")
RE_DATE = re.compile(r"^\d{2}-\d{2}-\d{4} à \d{2}:\d{2}:\d{2}$")
RE_SYNTH_HEADING = re.compile(r"^(Messages? clé des experts|Compléments d[’']apprentissage)$")

# Words that legitimately end in a hyphen when broken across lines. Every other
# line-final hyphen in this export is typographic hyphenation and is removed.
KEEP_HYPHEN_PREFIXES = {"post"}


# ----------------------------------------------------------------- extraction
def extract_lines(pdf_path: Path) -> List[str]:
    """PDF → de-hyphenated, whitespace-normalised lines."""
    import fitz  # pymupdf, already a project dependency

    doc = fitz.open(pdf_path)
    raw = "\n".join(page.get_text() for page in doc)
    doc.close()

    lines = [re.sub(r"[ \t ]+", " ", ln).strip() for ln in raw.split("\n")]

    # Re-join words split across a line break ("dispro-" + "portionnée").
    merged: List[str] = []
    i = 0
    while i < len(lines):
        line = lines[i]
        while line.endswith("-") and len(line) > 1:
            # Find the next non-empty line to glue on.
            j = i + 1
            while j < len(lines) and not lines[j]:
                j += 1
            if j >= len(lines):
                break
            stem = line[:-1]
            keep = stem.split()[-1].lower() in KEEP_HYPHEN_PREFIXES if stem.split() else False
            line = (line if keep else stem) + lines[j]
            i = j
        merged.append(line)
        i += 1
    return merged


def _join(lines: List[str]) -> str:
    """Collapse a run of wrapped lines into one paragraph."""
    return " ".join(ln for ln in lines if ln).strip()


def _index(lines: List[str], marker: str, start: int = 0) -> int:
    for i in range(start, len(lines)):
        if lines[i] == marker:
            return i
    return -1


# ------------------------------------------------------------------- parsing
def parse_objectives(lines: List[str]) -> List[str]:
    start = _index(lines, M_OBJECTIVES)
    end = _index(lines, M_SITUATIONS, start)
    if start < 0 or end < 0:
        raise ValueError("Could not locate the objectives section")

    objectives: List[str] = []
    current: List[str] = []
    for line in lines[start + 1:end]:
        if line.startswith("• "):
            if current:
                objectives.append(_join(current))
            current = [line[2:]]
        elif line and current:
            current.append(line)
    if current:
        objectives.append(_join(current))
    return objectives


def parse_synthesis(lines: List[str]) -> str:
    """Flatten the synthèse to headings on their own lines + one paragraph each."""
    blocks: List[str] = []
    current: List[str] = []
    for line in lines:
        if RE_SYNTH_HEADING.match(line):
            if current:
                blocks.append(_join(current))
            current = []
            blocks.append(line)
        elif line:
            current.append(line)
    if current:
        blocks.append(_join(current))
    return "\n".join(b for b in blocks if b).strip()


def parse_experts(lines: List[str]) -> List[Dict[str, str]]:
    """Parse the 'Réponses des membres:' block into anonymised expert entries."""
    # Locate every member header (an email = the clinician, "Expert AI" = generated).
    heads: List[tuple[int, bool]] = []
    for i, line in enumerate(lines):
        if RE_EMAIL.match(line):
            heads.append((i, True))
        elif RE_AI_MEMBER.match(line):
            heads.append((i, False))

    experts: List[Dict[str, str]] = []
    ai_seen = 0
    for n, (start, is_human) in enumerate(heads):
        end = heads[n + 1][0] if n + 1 < len(heads) else len(lines)
        block = lines[start + 1:end]

        j_at = _index(block, M_JUSTIFICATION)
        l_at = _index(block, M_LIKERT)
        if l_at < 0:
            raise ValueError(f"Member block without a Likert score: {lines[start]!r}")
        justification = _join(block[j_at + 1:l_at]) if 0 <= j_at < l_at else ""

        likert = ""
        for line in block[l_at + 1:]:
            if line.startswith("• "):
                likert = line[2:].strip()
                break
            if RE_DATE.match(line):
                break
        if not likert:
            raise ValueError(f"Member block without a Likert value: {lines[start]!r}")

        if is_human:
            label = "Expert 1 (clinicien)"
        else:
            ai_seen += 1
            label = f"Expert {ai_seen + 1} (IA)"
        experts.append({
            "expert_label": label,
            "likert": likert,
            "justification": justification,
        })

    # Keep the clinician first so the panel reads consistently everywhere.
    experts.sort(key=lambda e: e["expert_label"])
    return experts


def parse_scenario(lines: List[str]) -> Dict[str, Any]:
    title = next((ln for ln in lines if ln), "")

    hyp_at = next((i for i, ln in enumerate(lines) if RE_HYPOTHESIS.match(ln)), -1)
    new_at = next((i for i, ln in enumerate(lines) if RE_NEW_INFO.match(ln)), -1)
    mem_at = _index(lines, M_MEMBERS)
    if hyp_at < 0 or new_at < 0 or mem_at < 0:
        raise ValueError(f"Malformed scenario block: {title!r}")

    return {
        "title": title,
        "hypothesis": _join(lines[hyp_at + 1:new_at]),
        "new_information": _join(lines[new_at + 1:mem_at]),
        "experts": parse_experts(lines[mem_at + 1:]),
    }


def parse_situation(lines: List[str]) -> Dict[str, Any]:
    title = next((ln for ln in lines if ln), "")

    desc_at = _index(lines, M_DESCRIPTION)
    synth_at = _index(lines, M_SYNTHESIS)
    scen_at = _index(lines, M_SCENARIOS)
    if desc_at < 0 or synth_at < 0 or scen_at < 0:
        raise ValueError(f"Malformed situation block: {title!r}")

    # Split the scenarios section on each "• Titre du scénario:" header.
    scenarios: List[Dict[str, Any]] = []
    starts = [i for i in range(scen_at, len(lines)) if lines[i] == M_SCENARIO]
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        scenarios.append(parse_scenario(lines[start + 1:end]))

    return {
        "title": title,
        "text": _join(lines[desc_at + 1:synth_at]),
        "educational_synthesis": parse_synthesis(lines[synth_at + 1:scen_at]),
        "scenarios": scenarios,
    }


def parse(pdf_path: Path) -> Dict[str, Any]:
    lines = extract_lines(pdf_path)

    activity_title = ""
    for i, line in enumerate(lines):
        if line == "Titre de l'activité :":
            activity_title = next((ln for ln in lines[i + 1:] if ln), "")
            break

    objectives = parse_objectives(lines)

    starts = [i for i, ln in enumerate(lines) if ln == M_SITUATION]
    situations: List[Dict[str, Any]] = []
    for n, start in enumerate(starts):
        end = starts[n + 1] if n + 1 < len(starts) else len(lines)
        situations.append(parse_situation(lines[start + 1:end]))

    return {
        "activity_title": activity_title,
        "domain": DOMAIN,
        "likert_scale": LIKERT_SCALE,
        "objectives": objectives,
        "situations": situations,
    }


def validate(data: Dict[str, Any]) -> None:
    """Fail loudly rather than silently seeding half a training set."""
    errors: List[str] = []

    if not data["activity_title"]:
        errors.append("missing activity title")
    if len(data["objectives"]) != EXPECT_OBJECTIVES:
        errors.append(f"expected {EXPECT_OBJECTIVES} objectives, got {len(data['objectives'])}")
    if len(data["situations"]) != EXPECT_SITUATIONS:
        errors.append(f"expected {EXPECT_SITUATIONS} situations, got {len(data['situations'])}")

    n_scenarios = n_experts = 0
    for sit in data["situations"]:
        for field in ("title", "text", "educational_synthesis"):
            if not sit[field]:
                errors.append(f"situation {sit['title']!r}: empty {field}")
        if not sit["scenarios"]:
            errors.append(f"situation {sit['title']!r}: no scenarios")
        n_scenarios += len(sit["scenarios"])
        for sc in sit["scenarios"]:
            for field in ("title", "hypothesis", "new_information"):
                if not sc[field]:
                    errors.append(f"scenario {sc['title']!r}: empty {field}")
            n_experts += len(sc["experts"])
            labels = [e["expert_label"] for e in sc["experts"]]
            if len(set(labels)) != len(labels):
                errors.append(f"scenario {sc['title']!r}: duplicate expert labels {labels}")
            for e in sc["experts"]:
                if not e["likert"]:
                    errors.append(f"scenario {sc['title']!r}: expert without a Likert value")

    if n_scenarios != EXPECT_SCENARIOS:
        errors.append(f"expected {EXPECT_SCENARIOS} scenarios, got {n_scenarios}")
    if n_experts != EXPECT_EXPERTS:
        errors.append(f"expected {EXPECT_EXPERTS} expert responses, got {n_experts}")

    # The clinician's real address must never reach the JSON.
    if RE_EMAIL.pattern and "@" in json.dumps(data, ensure_ascii=False):
        errors.append("an email address survived anonymisation")

    if errors:
        print("❌ Validation failed:")
        for e in errors:
            print(f"   - {e}")
        sys.exit(1)


def main() -> None:
    pdf_path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_PDF
    if not pdf_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        sys.exit(1)

    print(f"Parsing {pdf_path} ...")
    data = parse(pdf_path)
    validate(data)

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(f"✅ Wrote {OUT_PATH.relative_to(ROOT_DIR)}")
    print(f"   activity   : {data['activity_title']}")
    print(f"   objectives : {len(data['objectives'])}")
    for sit in data["situations"]:
        n_exp = sum(len(sc["experts"]) for sc in sit["scenarios"])
        print(f"   - {sit['title']:<26} {len(sit['scenarios'])} scenarios, {n_exp} expert responses")


if __name__ == "__main__":
    main()
