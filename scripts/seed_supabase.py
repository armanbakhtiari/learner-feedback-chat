"""
Seed the Supabase content catalogue from ``trainings_2_experts.py`` (migraine).

Each *situation* becomes its own training (a training = 1+ situations; seeds use
exactly one). Migraine module 1 / situation 1 is the mandatory first training
(`origin='seed_mandatory'`); every other situation is a bank training
(`origin='seed_bank'`) available to the suggestions feature.

Idempotent: it wipes and re-inserts only the seeded trainings
(origin in seed_mandatory/seed_bank) so re-running is safe. User-generated data
(user_trainings, responses, evaluations, conversations, generated trainings) is
left untouched.

Run locally with a populated .env:  ./venv/bin/python scripts/seed_supabase.py
"""

import os
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

import trainings_2_experts as migraine
from backend.db import get_supabase
from backend.training_parser import (
    parse_module,
    parse_objectives,
    situation_title,
)

MODULE_VARS = ["training_1", "training_2", "training_3"]


def _delete_existing_seed(sb) -> None:
    """Remove previously seeded trainings (cascades to situations/scenarios/experts)."""
    existing = (
        sb.table("trainings")
        .select("id")
        .in_("origin", ["seed_mandatory", "seed_bank"])
        .execute()
    )
    ids = [row["id"] for row in existing.data]
    if ids:
        sb.table("trainings").delete().in_("id", ids).execute()
        print(f"  removed {len(ids)} existing seed trainings")


def seed() -> None:
    sb = get_supabase()
    objectives = parse_objectives(migraine.training_objectives)

    print("Seeding migraine content ...")
    _delete_existing_seed(sb)

    training_count = 0
    for module_var in MODULE_VARS:
        module_text = getattr(migraine, module_var)
        parsed = parse_module(module_text)
        module_title = parsed["module_title"]
        for situation in parsed["situations"]:
            s_idx = situation["situation_index"]
            is_mandatory = module_var == "training_1" and s_idx == 1
            origin = "seed_mandatory" if is_mandatory else "seed_bank"
            title = f"{module_title} — {situation_title(situation['text'], s_idx)}"

            training = (
                sb.table("trainings")
                .insert({
                    "title": title,
                    "domain": "migraine",
                    "origin": origin,
                    "learning_objectives": objectives,
                })
                .execute()
            ).data[0]
            training_id = training["id"]
            training_count += 1

            sit_row = (
                sb.table("situations")
                .insert({
                    "training_id": training_id,
                    "situation_index": 1,  # one situation per seeded training
                    "title": situation_title(situation["text"], s_idx),
                    "text": situation["text"],
                })
                .execute()
            ).data[0]
            situation_id = sit_row["id"]

            for sc_i, scenario in enumerate(situation["scenarios"], start=1):
                sc_row = (
                    sb.table("scenarios")
                    .insert({
                        "situation_id": situation_id,
                        "scenario_index": sc_i,
                        "hypothesis": scenario["hypothesis"],
                        "new_information": scenario["new_information"],
                    })
                    .execute()
                ).data[0]
                scenario_id = sc_row["id"]

                expert_rows = [
                    {
                        "scenario_id": scenario_id,
                        "expert_label": e["expert_label"],
                        "likert": e["likert"],
                        "justification": e["justification"],
                    }
                    for e in scenario["experts"]
                ]
                if expert_rows:
                    sb.table("expert_responses").insert(expert_rows).execute()

            tag = "  [MANDATORY]" if is_mandatory else ""
            print(f"  + {title} ({len(situation['scenarios'])} scenarios){tag}")

    print(f"Done. Seeded {training_count} trainings.")

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
