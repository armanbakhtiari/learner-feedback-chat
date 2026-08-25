"""
Reshape the live gastro catalogue into a single "Douleur abdominale" entry point.

``scripts/seed_gastro.py`` produces the same end state, but it wipes and re-inserts the
seeded trainings, which cascades to every user_training / response / evaluation /
conversation hanging off them. Once real learners have completed something that is not
acceptable, so this script performs the same reshaping **in place**:

before                                     after
------                                     -----
Douleur abdominale 1   seed_mandatory  ->  archived        (kept only for learners who
                                                            already completed it — listed
                                                            in neither the mandatory set
                                                            nor the suggestion bank)
Douleur abdominale 2   seed_bank       ->  deleted, its content now lives in ...
Douleur abdominale 3   seed_bank       ->  deleted, its content now lives in ...
                                       ->  Douleur abdominale  seed_mandatory  (NEW,
                                            situations 1-3, all 11 scenarios)
Diarrhée 1             seed_mandatory  ->  seed_bank
Hémorragie digestive 1 seed_mandatory  ->  seed_bank

Learners who had completed "Douleur abdominale 1" keep that evaluation and its feedback
conversation intact, and are additionally assigned the new full training. Assignments for
trainings that leave the dashboard are removed **only when they carry no work** (no
responses and not completed); anything with work is left alone and reported.

Dry run by default — pass --apply to write.

    ./venv/bin/python scripts/migrate_gastro_entry_point.py            # show the plan
    ./venv/bin/python scripts/migrate_gastro_entry_point.py --apply    # execute it
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
from scripts.seed_gastro import (
    DATA_PATH,
    ENTRY_POINT_THEME,
    _number_of,
    _theme_of,
    insert_training,
)

DOMAIN = "gastro"
ARCHIVED_ORIGIN = "archived"  # in neither list_mandatory_trainings() nor list_bank_trainings()


def _titles(activity: str) -> Dict[str, str]:
    return {
        "entry": f"{activity} — {ENTRY_POINT_THEME}",
        "old_entry": f"{activity} — {ENTRY_POINT_THEME} 1",
        "absorbed": [f"{activity} — {ENTRY_POINT_THEME} {n}" for n in (2, 3)],
        "to_bank": [f"{activity} — Diarrhée 1", f"{activity} — Hémorragie digestive 1"],
    }


def _work_on(sb, training_id: str) -> List[Dict[str, Any]]:
    """user_trainings for this training, annotated with whether they carry real work."""
    uts = sb.table("user_trainings").select("id,user_id,status").eq("training_id", training_id).execute().data
    for ut in uts:
        resp = sb.table("user_responses").select("id").eq("user_training_id", ut["id"]).limit(1).execute().data
        ev = sb.table("evaluations").select("id").eq("user_training_id", ut["id"]).limit(1).execute().data
        ut["has_work"] = bool(resp or ev or ut["status"] == "completed")
    return uts


def migrate(apply: bool) -> None:
    data = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    activity = data["activity_title"]
    t = _titles(activity)
    sb = get_supabase()

    rows = sb.table("trainings").select("id,title,origin").eq("domain", DOMAIN).execute().data
    by_title = {r["title"]: r for r in rows}

    if by_title.get(t["entry"]):
        print(f"✅ '{t['entry']}' already exists — migration already applied. Nothing to do.")
        return
    missing = [x for x in [t["old_entry"], *t["absorbed"], *t["to_bank"]] if x not in by_title]
    if missing:
        print("❌ Expected trainings not found — is the catalogue in the pre-migration shape?")
        for m in missing:
            print(f"   missing: {m}")
        sys.exit(1)

    entry_situations = sorted(
        (s for s in data["situations"] if _theme_of(s["title"]) == ENTRY_POINT_THEME),
        key=lambda s: _number_of(s["title"]),
    )
    n_scen = sum(len(s["scenarios"]) for s in entry_situations)

    print(f"{'APPLYING' if apply else 'DRY RUN —'} gastro entry-point migration\n")
    print(f"1. create '{t['entry']}' (seed_mandatory, {len(entry_situations)} situations, {n_scen} scenarios)")

    # 2. archive the old single-situation entry point, keeping completed work reachable
    old = by_title[t["old_entry"]]
    old_uts = _work_on(sb, old["id"])
    keep = [u for u in old_uts if u["has_work"]]
    drop = [u for u in old_uts if not u["has_work"]]
    print(f"2. archive '{t['old_entry']}' — {len(keep)} assignment(s) with work kept, "
          f"{len(drop)} empty assignment(s) removed")

    # 3. delete the standalone situations now folded into the entry point
    for title in t["absorbed"]:
        tr = by_title[title]
        uts = _work_on(sb, tr["id"])
        blocked = [u for u in uts if u["has_work"]]
        if blocked:
            print(f"❌ '{title}' has {len(blocked)} assignment(s) with real work — refusing to delete it.")
            sys.exit(1)
        print(f"3. delete '{title}' (content now in the entry point; {len(uts)} empty assignment(s))")

    # 4. the other two theme openers move to the bank
    for title in t["to_bank"]:
        tr = by_title[title]
        uts = _work_on(sb, tr["id"])
        drop_n = len([u for u in uts if not u["has_work"]])
        keep_n = len(uts) - drop_n
        print(f"4. '{title}' -> seed_bank; {drop_n} empty assignment(s) removed from dashboards, "
              f"{keep_n} with work kept")

    if not apply:
        print("\nDry run only. Re-run with --apply to execute.")
        return

    print("\nexecuting ...")

    new_training = insert_training(
        sb, title=t["entry"], domain=DOMAIN, origin="seed_mandatory",
        scale=data["likert_scale"], objectives=data["objectives"],
        situations=entry_situations,
    )
    print(f"  created {new_training['id']}")

    if drop:
        sb.table("user_trainings").delete().in_("id", [u["id"] for u in drop]).execute()
    sb.table("trainings").update({"origin": ARCHIVED_ORIGIN}).eq("id", old["id"]).execute()
    print(f"  archived {old['id']} (kept {len(keep)} assignment(s) with work)")

    for title in t["absorbed"]:
        sb.table("trainings").delete().eq("id", by_title[title]["id"]).execute()
        print(f"  deleted {title}")

    for title in t["to_bank"]:
        tr = by_title[title]
        uts = _work_on(sb, tr["id"])
        empty = [u["id"] for u in uts if not u["has_work"]]
        if empty:
            sb.table("user_trainings").delete().in_("id", empty).execute()
        sb.table("trainings").update({"origin": "seed_bank"}).eq("id", tr["id"]).execute()
        print(f"  {title} -> seed_bank ({len(empty)} assignment(s) removed)")

    # Everyone picks the new entry point up on their next dashboard load, but do it now so
    # nobody has to wait for a request to land.
    from backend.db import repo
    for user in sb.table("users").select("id,clerk_user_id,email").execute().data:
        repo.ensure_bootstrap(user)
    print("  re-bootstrapped all users")

    if os.environ.get("CHROMA_API_KEY"):
        try:
            from backend.bank_rag import reindex_bank
            reindex_bank()
            print("  reindexed the bank vector store")
        except Exception as e:
            print(f"⚠️  bank reindex skipped: {e}")

    print("\n✅ migration complete")


if __name__ == "__main__":
    migrate(apply="--apply" in sys.argv)
