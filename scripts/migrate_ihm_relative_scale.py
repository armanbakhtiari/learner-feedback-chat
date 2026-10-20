"""
Move the live IHM rows from the former absolute ``appropriee`` wording onto the relative one.

The IHM scale used to ask how appropriate a decision *is* ("Totalement inappropriée" ..
"Totalement appropriée"); it now asks whether the new information makes it more or less
appropriate ("Beaucoup moins appropriée" .. "Beaucoup plus appropriée"). Learners already
have answers on the old wording — drafts and completed trainings — so re-seeding is not an
option (it cascades to their work). This rewrites the stored values in place, ordinally,
through ``backend.likert.APPROPRIEE_LEGACY_MAP``:

* ``expert_responses.likert`` of every IHM scenario (seeded and generated alike);
* ``user_responses.likert`` of every IHM scenario, completed trainings included, so a
  learner's answer and the experts' are always on the same scale.

The middle value is unchanged. Rows already on the new wording are left alone, so the
script is idempotent. Completed trainings' evaluation tables hold a copy of the answer:
rebuild them afterwards with ``scripts/backfill_eval_tables.py --all``.

Requires the migration ``20261019120000_grh_and_relative_scales.sql`` (the new enum values).

Dry run by default — pass --apply to write.

    ./venv/bin/python scripts/migrate_ihm_relative_scale.py            # show the counts
    ./venv/bin/python scripts/migrate_ihm_relative_scale.py --apply    # execute it
"""

import sys
from pathlib import Path
from typing import List

ROOT_DIR = Path(__file__).parent.parent
sys.path.append(str(ROOT_DIR))

from dotenv import load_dotenv

load_dotenv()

from backend.db import get_supabase
from backend.likert import APPROPRIEE_LEGACY_MAP

DOMAIN = "ihm"
CHUNK = 100  # ids per `in` filter, to keep request URLs short


def _chunks(ids: List[str]):
    for i in range(0, len(ids), CHUNK):
        yield ids[i:i + CHUNK]


def _ihm_scenario_ids(sb) -> List[str]:
    trainings = [t["id"] for t in sb.table("trainings").select("id").eq("domain", DOMAIN).execute().data]
    situations: List[str] = []
    for chunk in _chunks(trainings):
        situations += [s["id"] for s in sb.table("situations").select("id").in_("training_id", chunk).execute().data]
    scenarios: List[str] = []
    for chunk in _chunks(situations):
        scenarios += [s["id"] for s in sb.table("scenarios").select("id").in_("situation_id", chunk).execute().data]
    print(f"{DOMAIN}: {len(trainings)} trainings, {len(situations)} situations, {len(scenarios)} scenarios")
    return scenarios


def main() -> None:
    apply = "--apply" in sys.argv
    sb = get_supabase()
    scenario_ids = _ihm_scenario_ids(sb)
    renames = {old: new for old, new in APPROPRIEE_LEGACY_MAP.items() if old != new}

    for table in ("expert_responses", "user_responses"):
        total = 0
        for old, new in renames.items():
            n = 0
            for chunk in _chunks(scenario_ids):
                q = sb.table(table)
                if apply:
                    n += len(q.update({"likert": new}).in_("scenario_id", chunk).eq("likert", old).execute().data)
                else:
                    n += len(q.select("id").in_("scenario_id", chunk).eq("likert", old).execute().data)
            if n:
                print(f"  {table:<17} {old!r:>28} → {new!r}: {n}")
            total += n
        print(f"{table}: {total} row(s) {'updated' if apply else 'to update'}")

    if apply:
        print("\n✅ Done. Now rebuild the evaluation tables: scripts/backfill_eval_tables.py --all")
    else:
        print("\n(dry run — pass --apply to write)")


if __name__ == "__main__":
    main()
