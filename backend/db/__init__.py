"""Supabase data layer (backend-mediated; service_role key)."""

from backend.db.client import get_supabase

__all__ = ["get_supabase"]
