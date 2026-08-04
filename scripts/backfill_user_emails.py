#!/usr/bin/env python3
"""
One-off backfill of `users.email` from the Clerk Backend API.

Rows created before the email fallback existed (backend/auth.py) have `email = null`,
because Clerk's session token carries no `email` claim unless you add it in the
dashboard. Signed-in users get filled in automatically on their next request; this
script covers everyone else.

Usage:
    python scripts/backfill_user_emails.py

Required env vars (read from .env or the environment):
    SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY
    CLERK_SECRET_KEY
"""

import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

from backend.auth import fetch_clerk_email
from backend.db import repo


def main() -> None:
    rows = repo.list_users_missing_email()
    if not rows:
        print("✅ No users missing an email.")
        return

    print(f"Found {len(rows)} user(s) without an email.")
    filled = 0
    for row in rows:
        email = fetch_clerk_email(row["clerk_user_id"])
        if not email:
            print(f"  ⚠️  no email found for {row['clerk_user_id']}")
            continue
        repo.update_user_profile(row["id"], email=email)
        filled += 1
        print(f"  ✓ {row['clerk_user_id']} → {email}")

    print(f"\n✅ Backfilled {filled}/{len(rows)} user(s).")


if __name__ == "__main__":
    main()
