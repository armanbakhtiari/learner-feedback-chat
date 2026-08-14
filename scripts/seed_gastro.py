"""
Seed the Supabase content catalogue from ``data/gastro_trainings.json``.

That file is produced offline by ``scripts/parse_training_pdf.py`` from the SENSAI
training export. Each *situation* in the export becomes its own training (a training =
1+ situations; these seeds use exactly one).

The first situation of each theme — "Douleur abdominale 1", "Diarrhée 1",
"Hémorragie digestive 1" — is an entry-point training (``origin='seed_mandatory'``),
joining the migraine entry point seeded by ``scripts/seed_supabase.py``. Every learner is
assigned all of them and completing **any one** unlocks the feedback and suggestions.
The remaining situations are bank trainings (``origin='seed_bank'``) available to the
suggestions feature.

Idempotent: it wipes and re-inserts only the *gastro* seeded trainings, so re-running is
safe and it never touches the migraine catalogue (or vice versa — see the matching
domain scoping in ``scripts/seed_supabase.py``).

⚠️ Deleting a training cascades to any user_trainings/responses/evaluations attached to
it. That is the existing behaviour of the seed scripts; the domain scoping keeps the
blast radius to the content being re-seeded.

Run locally with a populated .env:  ./venv/bin/python scripts/seed_gastro.py
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

DATA_PATH = ROOT_DIR / "data" / "gastro_trainings.json"

# The first situation of each clinical theme is an entry point; the rest go to the bank.
MANDATORY_TITLES = {"Douleur abdominale 1", "Diarrhée 1", "Hémorragie digestive 1"}


def _load() -> Dict[str, Any]:
    if not DATA_PATH.exists():
        print(f"❌ {DATA_PATH.relative_to(ROOT_DIR)} not found — run scripts/parse_training_pdf.py first")
        sys.exit(1)
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def _validate(data: Dict[str, Any]) -> None:
    """Refuse to seed content whose Likert values aren't in the declared scale."""
    scale = data["likert_scale"]
    allowed = set(values_for(scale))
    if not allowed:
        print(f"❌ Unknown likert scale: {scale!r}")
        sys.exit(1)

    titles = {sit["title"] for sit in data["situations"]}
    missing = MANDATORY_TITLES - titles
    if missing:
        print(f"❌ Expected entry-point situation(s) not found in the data: {sorted(missing)}")
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

    for situation in data["situations"]:
        s_title = situation["title"]
        is_mandatory = s_title in MANDATORY_TITLES
        origin = "seed_mandatory" if is_mandatory else "seed_bank"

        training = (
            sb.table("trainings")
            .insert({
                "title": f"{activity} — {s_title}",
                "domain": domain,
                "origin": origin,
                "likert_scale": scale,
                "learning_objectives": objectives,
            })
            .execute()
        ).data[0]

        sit_row = (
            sb.table("situations")
            .insert({
                "training_id": training["id"],
                "situation_index": 1,  # one situation per seeded training
                "title": s_title,
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

        tag = "  [ENTRY POINT]" if is_mandatory else ""
        print(f"  + {s_title} ({len(situation['scenarios'])} scenarios){tag}")

    print(f"Done. Seeded {len(data['situations'])} trainings.")

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
