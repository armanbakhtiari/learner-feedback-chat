#!/usr/bin/env python3
"""
One-off backfill of `evaluations.eval_table_json`.

Trainings completed before the structured evaluation table existed only have the old
LLM-authored `evaluation_html`, so the "Complétées" tab shows the "en cours de
génération" placeholder for them. Their `evaluation_json` is still stored, which is all
`build_eval_table` needs — no LLM call and no re-evaluation involved.

Usage:
    python scripts/backfill_eval_tables.py [--dry-run]

Required env vars (read from .env or the environment):
    SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from backend.db import repo
from backend.eval_table_agent import build_eval_table


def main() -> None:
    dry_run = "--dry-run" in sys.argv

    pending = repo.list_evaluations_missing_table()
    if not pending:
        print("✅ Every evaluation already has a table.")
        return

    print(f"Found {len(pending)} evaluation(s) without a table.{' (dry run)' if dry_run else ''}")
    built = 0
    for ev in pending:
        ut_id = ev["user_training_id"]
        ut = repo.get_user_training(ut_id)
        if not ut:
            print(f"  ⚠️  {ut_id}: user_training missing, skipped")
            continue

        training = repo.get_training_content(ut["training_id"])
        responses = {r["scenario_id"]: r for r in repo.get_responses(ut_id)}
        table = build_eval_table(ev.get("evaluation_json") or {}, training, responses)

        rows = sum(len(s["scenarios"]) for s in table["situations"])
        if not rows:
            # Content deleted, or the evaluation didn't line up with it — leave the
            # placeholder rather than writing an empty table.
            print(f"  ⚠️  {ut_id}: no rows built, skipped")
            continue

        if not dry_run:
            repo.update_eval_table(ut_id, table)
        built += 1
        print(f"  ✓ {ut_id}: {len(table['situations'])} situation(s), {rows} scenario(s)")

    verb = "Would backfill" if dry_run else "Backfilled"
    print(f"\n✅ {verb} {built}/{len(pending)} evaluation(s).")


if __name__ == "__main__":
    main()
