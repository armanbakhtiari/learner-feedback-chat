"""
Seed the Supabase content catalogue from ``data/grh_trainings.json``.

That file is produced offline by ``scripts/parse_grh_docx.py`` from the GRH (human
resources management) concordance Word document. The document is a single short training
— two situations, seven scenarios — so it becomes ONE training carrying both situations,
seeded as ``origin='seed_mandatory'``. It joins the migraine, gastro and IHM entry points:
every learner is assigned all four (``repo.ensure_bootstrap`` picks it up on their next
dashboard load) and completing **any one** unlocks the feedback and suggestions. There is
no bank content for this domain, so the suggestion vector store is untouched.

The two situations use different scenario formats: situation 1 is *raisonnement*
(hypothesis + new information, the training's ``pertinence_relative`` scale) and situation
2 is *jugement* (an observed behaviour, each scenario overriding the scale with
``acceptabilite``). Both travel per scenario through ``insert_training``.

Idempotent: it wipes and re-inserts only the *grh* seeded trainings, so re-running is
safe and it never touches the other catalogues.

⚠️ Deleting a training cascades to any user_trainings/responses/evaluations attached to
it. On a database with real learner work, migrate instead of re-seeding — see
``scripts/migrate_gastro_entry_point.py``, which reshapes a catalogue in place.

Run locally with a populated .env:  ./venv/bin/python scripts/seed_grh.py
"""

import json
import sys
from pathlib import Path
from typing import Any, Dict

ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

from dotenv import load_dotenv

load_dotenv()

from backend.db import get_supabase
from backend.likert import scenario_scale, values_for
from scripts.seed_gastro import _delete_existing_seed, insert_training

DATA_PATH = ROOT_DIR / "data" / "grh_trainings.json"


def _load() -> Dict[str, Any]:
    if not DATA_PATH.exists():
        print(f"❌ {DATA_PATH.relative_to(ROOT_DIR)} not found — run scripts/parse_grh_docx.py first")
        sys.exit(1)
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _validate(data: Dict[str, Any]) -> None:
    """Refuse to seed content whose Likert values aren't on their scenario's scale."""
    bad = [
        (sc["hypothesis"][:40], e["likert"])
        for sit in data["situations"]
        for sc in sit["scenarios"]
        for e in sc["experts"]
        if e["likert"] not in values_for(scenario_scale(sc, data))
    ]
    if bad:
        print(f"❌ Likert values off their scenario's scale: {bad}")
        sys.exit(1)


def seed() -> None:
    data = _load()
    _validate(data)

    sb = get_supabase()
    domain = data["domain"]
    activity = data["activity_title"]

    print(f"Seeding {domain} content ({activity}) ...")
    _delete_existing_seed(sb, domain)

    situations = sorted(data["situations"], key=lambda s: s["index"])
    insert_training(
        sb, title=activity, domain=domain,
        origin="seed_mandatory", scale=data["likert_scale"],
        objectives=data["objectives"], situations=situations,
    )
    n_scenarios = sum(len(s["scenarios"]) for s in situations)
    print(f"  + {activity} ({len(situations)} situations, {n_scenarios} scenarios)  [ENTRY POINT]")
    for s in situations:
        kinds = ", ".join(sorted({sc.get("kind", "reasoning") for sc in s["scenarios"]}))
        print(f"      situation {s['index']}: {s['title']} ({kinds})")
    print("Done.")


if __name__ == "__main__":
    seed()
