"""
Singleton Supabase client for the backend.

The backend is the only component that writes to Supabase, using the
**service_role** key (which bypasses Row Level Security). Never expose this key
to the browser — the frontend uses the anon key + a Clerk JWT and may only read
its own `notifications` rows.
"""

import os
from functools import lru_cache

from supabase import Client, create_client


@lru_cache(maxsize=1)
def get_supabase() -> Client:
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise RuntimeError(
            "SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY must be set to use the database."
        )
    return create_client(url, key)
