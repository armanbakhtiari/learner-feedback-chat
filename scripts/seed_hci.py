"""
Seed the Supabase content catalogue from ``data/hci_trainings.json``.

That file is produced offline by ``scripts/parse_hci_docx.py`` from the IHM concordance
Word document (course LOG2420), which is a flat list of 10 situations. This script
groups them:

* The **entry-point situations** (``ENTRY_POINT_INDICES`` — situations 1 and 2) become ONE
  training carrying both, ordered by their number, seeded as ``origin='seed_mandatory'``.
  It joins the migraine entry point (``scripts/seed_supabase.py``) and the gastro one
  (``scripts/seed_gastro.py``): every learner is assigned all three and completing **any
  one** unlocks the feedback and suggestions. Because its two situations cover distinct
  ground, it carries the broader merged objective set authored in ``parse_hci_docx.py``
  (``entry_point_objectives``) rather than the six per-situation ones.
* Each of the other 8 situations becomes its own single-situation bank training
  (``origin='seed_bank'``) available to the suggestions feature, carrying **its own**
  three objectives — the suggestion query agent embeds a training's objectives, so
  situation-specific ones retrieve far better than one repeated flat list.

Grouping is by explicit index rather than by the ``"<Theme> <N>"`` title heuristic
``scripts/seed_gastro.py`` uses: these situation titles are all distinct topics.

Idempotent: it wipes and re-inserts only the *ihm* seeded trainings, so re-running is
safe and it never touches the migraine or gastro catalogues (see the matching domain
scoping in the other two seed scripts).

⚠️ Deleting a training cascades to any user_trainings/responses/evaluations attached to
it. On a database with real learner work, migrate instead of re-seeding — see
``scripts/migrate_gastro_entry_point.py``, which reshapes a catalogue in place.

Run locally with a populated .env:  ./venv/bin/python scripts/seed_hci.py
"""

import json
import os
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

from dotenv import load_dotenv

load_dotenv()

from backend.db import get_supabase
from backend.likert import values_for
from scripts.seed_gastro import _delete_existing_seed, insert_training

DATA_PATH = ROOT_DIR / "data" / "hci_trainings.json"

# Situations (by their ``index`` in the source document) gathered into the single
# mandatory training. Everything else becomes a one-situation bank training.
ENTRY_POINT_INDICES = (1, 2)


def _load() -> Dict[str, Any]:
    if not DATA_PATH.exists():
        print(f"❌ {DATA_PATH.relative_to(ROOT_DIR)} not found — run scripts/parse_hci_docx.py first")
        sys.exit(1)
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _validate(data: Dict[str, Any]) -> None:
    """Refuse to seed content whose Likert values aren't in the declared scale."""
    scale = data["likert_scale"]
    allowed = set(values_for(scale))
    if not allowed:
        print(f"❌ Unknown likert scale: {scale!r}")
        sys.exit(1)

    indices = {sit["index"] for sit in data["situations"]}
    missing = [i for i in ENTRY_POINT_INDICES if i not in indices]
    if missing:
        print(f"❌ Entry-point situations {missing} not found. Present: {sorted(indices)}")
        sys.exit(1)

    if not data.get("entry_point_objectives"):
        print("❌ entry_point_objectives is empty — the merged objective set is required")
        sys.exit(1)

    bad = {
        e["likert"]
        for sit in data["situations"]
        for sc in sit["scenarios"]
        for e in sc["experts"]
        if e["likert"] not in allowed
    }
    if bad:
        print(f"❌ Likert values outside the '{scale}' scale: {sorted(bad)}")
        sys.exit(1)


def seed() -> None:
    data = _load()
    _validate(data)

    sb = get_supabase()
    domain = data["domain"]
    scale = data["likert_scale"]
    activity = data["activity_title"]

    print(f"Seeding {domain} content ({activity}) ...")
    _delete_existing_seed(sb, domain)

    entry_situations = sorted(
        (s for s in data["situations"] if s["index"] in ENTRY_POINT_INDICES),
        key=lambda s: s["index"],
    )
    bank_situations = [s for s in data["situations"] if s["index"] not in ENTRY_POINT_INDICES]

    # Entry point: one training carrying both situations, under the merged objectives.
    entry_title = f"{activity} — {data['entry_point_title']}"
    insert_training(
        sb, title=entry_title, domain=domain,
        origin="seed_mandatory", scale=scale,
        objectives=data["entry_point_objectives"],
        situations=entry_situations,
    )
    n_scenarios = sum(len(s["scenarios"]) for s in entry_situations)
    print(f"  + {data['entry_point_title']} ({len(entry_situations)} situations, "
          f"{n_scenarios} scenarios)  [ENTRY POINT]")
    for s in entry_situations:
        print(f"      situation {s['index']}: {s['title']}")

    # Bank: one training per remaining situation, with that situation's own objectives.
    for situation in bank_situations:
        insert_training(
            sb, title=f"{activity} — {situation['title']}", domain=domain,
            origin="seed_bank", scale=scale, objectives=situation["objectives"],
            situations=[situation],
        )
        print(f"  + {situation['title']} ({len(situation['scenarios'])} scenarios)")

    print(f"Done. Seeded 1 entry point + {len(bank_situations)} bank trainings.")

    # Rebuild the suggestion vector store so it matches the freshly-seeded bank.
    if os.environ.get("CHROMA_API_KEY"):
        try:
            from backend.bank_rag import reindex_bank
            reindex_bank()
            print("Reindexed the bank vector store.")
        except Exception as e:
            print(f"⚠️  Bank reindex skipped: {e}")


if __name__ == "__main__":
    seed()
