"""
Clerk JWT verification for FastAPI (backend-mediated auth).

The browser attaches the Clerk session JWT as `Authorization: Bearer <token>`.
We verify it against Clerk's JWKS (RS256), extract the `sub` (Clerk user id),
upsert the user, and (on first sign-in) bootstrap their mandatory training +
empty learning-gap doc.

Config (env):
  CLERK_ISSUER    e.g. https://<slug>.clerk.accounts.dev  (or your prod domain)
  CLERK_JWKS_URL  optional; defaults to <CLERK_ISSUER>/.well-known/jwks.json
"""

import os
import ssl
from functools import lru_cache
from typing import Any, Dict, Optional

import certifi
import jwt
from fastapi import Depends, Header, HTTPException
from jwt import PyJWKClient

from backend.db import repo


def _issuer() -> str:
    iss = os.environ.get("CLERK_ISSUER", "").rstrip("/")
    if not iss:
        raise RuntimeError("CLERK_ISSUER must be set to verify Clerk tokens.")
    return iss


def _jwks_url() -> str:
    return os.environ.get("CLERK_JWKS_URL") or f"{_issuer()}/.well-known/jwks.json"


@lru_cache(maxsize=1)
def _jwks_client() -> PyJWKClient:
    # PyJWKClient caches keys internally and refreshes on unknown kid.
    # Pass a certifi-backed SSL context so JWKS fetch verifies TLS even where the
    # system CA store isn't wired into Python's urllib (e.g. some macOS installs).
    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    return PyJWKClient(_jwks_url(), ssl_context=ssl_ctx)


def verify_clerk_token(token: str) -> Dict[str, Any]:
    try:
        signing_key = _jwks_client().get_signing_key_from_jwt(token)
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=_issuer(),
            options={"verify_aud": False},  # Clerk session tokens omit `aud` by default
        )
        return claims
    except Exception as e:  # invalid signature / expired / wrong issuer
        raise HTTPException(status_code=401, detail=f"Invalid authentication token: {e}")


def _display_name(claims: Dict[str, Any]) -> Optional[str]:
    if claims.get("name"):
        return claims["name"]
    first, last = claims.get("first_name"), claims.get("last_name")
    full = " ".join(p for p in [first, last] if p)
    return full or None


async def get_current_user(authorization: Optional[str] = Header(default=None)) -> Dict[str, Any]:
    """FastAPI dependency → the Supabase `users` row for the authenticated Clerk user."""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    claims = verify_clerk_token(token)

    clerk_user_id = claims.get("sub")
    if not clerk_user_id:
        raise HTTPException(status_code=401, detail="Token missing subject")

    user = repo.get_user_by_clerk_id(clerk_user_id)
    if user is None:
        user = repo.create_user(
            clerk_user_id,
            email=claims.get("email"),
            full_name=_display_name(claims),
        )
        repo.ensure_bootstrap(user)
    return user


CurrentUser = Depends(get_current_user)
