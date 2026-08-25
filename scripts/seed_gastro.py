"""
Seed the Supabase content catalogue from ``data/gastro_trainings.json``.

That file is produced offline by ``scripts/parse_training_pdf.py`` from the SENSAI
training export, which is a flat list of situations. This script groups them:

* The **entry-point theme** (``ENTRY_POINT_THEME``) becomes ONE training carrying all of
  that theme's situations, ordered by their number — so "Douleur abdominale" is a single
  training with situations 1, 2 and 3 and every one of their scenarios. It is seeded as
  ``origin='seed_mandatory'``, joining the migraine entry point seeded by
  ``scripts/seed_supabase.py``. Every learner is assigned both and completing **either**
  unlocks the feedback and suggestions.
* Every other situation becomes its own single-situation bank training
  (``origin='seed_bank'``) available to the suggestions feature.

Idempotent: it wipes and re-inserts only the *gastro* seeded trainings, so re-running is
safe and it never touches the migraine catalogue (or vice versa — see the matching
domain scoping in ``scripts/seed_supabase.py``).

⚠️ Deleting a training cascades to any user_trainings/responses/evaluations attached to
it. On a database with real learner work, migrate instead of re-seeding — see
``scripts/migrate_gastro_entry_point.py``, which reshapes the catalogue in place.

Run locally with a populated .env:  ./venv/bin/python scripts/seed_gastro.py
"""

import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

from dotenv import load_dotenv

load_dotenv()

from backend.db import get_supabase
from backend.likert import values_for

DATA_PATH = ROOT_DIR / "data" / "gastro_trainings.json"

# Situations whose title starts with this are gathered into a single mandatory training.
# Everything else is a one-situation bank training.
ENTRY_POINT_THEME = "Douleur abdominale"


def _load() -> Dict[str, Any]:
    if not DATA_PATH.exists():
        print(f"❌ {DATA_PATH.relative_to(ROOT_DIR)} not found — run scripts/parse_training_pdf.py first")
        sys.exit(1)
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _theme_of(title: str) -> str:
    """'Douleur abdominale 2' -> 'Douleur abdominale'."""
    return re.sub(r"\s*\d+\s*$", "", title).strip()


def _number_of(title: str) -> int:
    """'Douleur abdominale 2' -> 2 (0 when unnumbered), so situations order 1,2,3."""
    m = re.search(r"(\d+)\s*$", title)
    return int(m.group(1)) if m else 0


def _validate(data: Dict[str, Any]) -> None:
    """Refuse to seed content whose Likert values aren't in the declared scale."""
    scale = data["likert_scale"]
    allowed = set(values_for(scale))
    if not allowed:
        print(f"❌ Unknown likert scale: {scale!r}")
        sys.exit(1)

    themes = {_theme_of(sit["title"]) for sit in data["situations"]}
    if ENTRY_POINT_THEME not in themes:
        print(f"❌ Entry-point theme {ENTRY_POINT_THEME!r} not found. Themes present: {sorted(themes)}")
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


def _delete_existing_seed(sb, domain: str) -> None:
    """Remove previously seeded trainings for THIS domain (cascades to children)."""
    existing = (
        sb.table("trainings")
        .select("id")
        .eq("domain", domain)
        .in_("origin", ["seed_mandatory", "seed_bank"])
        .execute()
    )
    ids = [row["id"] for row in existing.data]
    if ids:
        sb.table("trainings").delete().in_("id", ids).execute()
        print(f"  removed {len(ids)} existing {domain} seed trainings")


def insert_training(sb, *, title: str, domain: str, origin: str, scale: str,
                    objectives: List[str], situations: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Insert one training with its situations, scenarios and expert responses.

    ``situations`` is a list of the parsed-JSON situation objects, in the order they
    should be presented — the evaluator's positional "situation N" keys follow it.
    """
    training = (
        sb.table("trainings")
        .insert({
            "title": title,
            "domain": domain,
            "origin": origin,
            "likert_scale": scale,
            "learning_objectives": objectives,
        })
        .execute()
    ).data[0]

    for s_i, situation in enumerate(situations, start=1):
        sit_row = (
            sb.table("situations")
            .insert({
                "training_id": training["id"],
                "situation_index": s_i,
                "title": situation["title"],
                "text": situation["text"],
                "educational_synthesis": situation["educational_synthesis"],
            })
            .execute()
        ).data[0]

        for sc_i, scenario in enumerate(situation["scenarios"], start=1):
            sc_row = (
                sb.table("scenarios")
                .insert({
                    "situation_id": sit_row["id"],
                    "scenario_index": sc_i,
                    "hypothesis": scenario["hypothesis"],
                    "new_information": scenario["new_information"],
                })
                .execute()
            ).data[0]

            expert_rows = [
                {
                    "scenario_id": sc_row["id"],
                    "expert_label": e["expert_label"],
                    "likert": e["likert"],
                    "justification": e["justification"],
                }
                for e in scenario["experts"]
            ]
            if expert_rows:
                sb.table("expert_responses").insert(expert_rows).execute()

    return training


def seed() -> None:
    data = _load()
    _validate(data)

    sb = get_supabase()
    domain = data["domain"]
    scale = data["likert_scale"]
    objectives: List[str] = data["objectives"]
    activity = data["activity_title"]

    print(f"Seeding {domain} content ({activity}) ...")
    _delete_existing_seed(sb, domain)

    entry_situations = sorted(
        (s for s in data["situations"] if _theme_of(s["title"]) == ENTRY_POINT_THEME),
        key=lambda s: _number_of(s["title"]),
    )
    bank_situations = [s for s in data["situations"] if _theme_of(s["title"]) != ENTRY_POINT_THEME]

    # Entry point: one training carrying every situation of the theme.
    insert_training(
        sb, title=f"{activity} — {ENTRY_POINT_THEME}", domain=domain,
        origin="seed_mandatory", scale=scale, objectives=objectives,
        situations=entry_situations,
    )
    n_scenarios = sum(len(s["scenarios"]) for s in entry_situations)
    titles = ", ".join(s["title"] for s in entry_situations)
    print(f"  + {ENTRY_POINT_THEME} ({len(entry_situations)} situations, {n_scenarios} scenarios)  [ENTRY POINT]")
    print(f"      situations: {titles}")

    # Bank: one training per remaining situation.
    for situation in bank_situations:
        insert_training(
            sb, title=f"{activity} — {situation['title']}", domain=domain,
            origin="seed_bank", scale=scale, objectives=objectives,
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
