"""Who is asking: verify the Supabase session token and load the user's role.

Supabase signs access tokens with the project's key; the public half is served
at {SUPABASE_URL}/auth/v1/.well-known/jwks.json. The engine verifies the
signature and expiry itself, then reads the role and district from `profiles`.
Scoping is applied in each query, not in the page, so a mistake in the
interface cannot leak another district's works.

OPEN TO VIEW (T130): anyone may look. A request without a session is the PUBLIC viewer of
all districts (`viewer`), for read-only routes; saving a form or filming a site visit still
needs a signed-in account (`current_user`).

DEV MODE: with DRISHTI_AUTH=dev a request may name its role in the
X-Dev-Role header, so the app can run on a laptop without Supabase. It is
refused outright when running on Vercel.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

import httpx
import jwt
from fastapi import Header, HTTPException

from drishti import config
from drishti.db import connect

ROLES = ("MINISTRY", "DISTRICT", "FIELD")
_JWKS: dict = {"at": 0.0, "keys": None}
JWKS_TTL_S = 600


@dataclass(frozen=True)
class Principal:
    user_id: str
    role: str
    district_lgd: str | None = None
    name: str | None = None

    def scope_district(self) -> str | None:
        """The district this user is confined to, or None for all districts."""
        return self.district_lgd if self.role in ("DISTRICT", "FIELD") else None


def _dev_mode() -> bool:
    if os.environ.get("VERCEL"):
        return False
    return os.environ.get("DRISHTI_AUTH") == "dev"


def _jwks() -> jwt.PyJWKSet:
    if _JWKS["keys"] is None or time.time() - _JWKS["at"] > JWKS_TTL_S:
        url = f"{config.supabase_url()}/auth/v1/.well-known/jwks.json"
        _JWKS["keys"] = httpx.get(url, timeout=10).json()
        _JWKS["at"] = time.time()
    return jwt.PyJWKSet.from_dict(_JWKS["keys"])


def verify_token(token: str, jwks: jwt.PyJWKSet | None = None) -> dict:
    keys = jwks or _jwks()
    header = jwt.get_unverified_header(token)
    key = next((k for k in keys.keys if k.key_id == header.get("kid")), None)
    if key is None:
        raise HTTPException(401, "unknown signing key")
    try:
        return jwt.decode(token, key.key, algorithms=[header.get("alg", "ES256")],
                          audience="authenticated")
    except jwt.PyJWTError as exc:
        raise HTTPException(401, "invalid or expired session") from exc


def _profile(user_id: str) -> Principal:
    with connect() as con:
        row = con.execute("SELECT role, district_lgd, display_name FROM profiles "
                          "WHERE user_id = %s", (user_id,)).fetchone()
    if row is None:
        raise HTTPException(403, "this account has no DRISHTI role")
    return Principal(user_id, row["role"], row["district_lgd"], row["display_name"])


def current_user(authorization: str | None = Header(default=None),
                 x_dev_role: str | None = Header(default=None),
                 x_dev_district: str | None = Header(default=None)) -> Principal:
    if _dev_mode() and x_dev_role:
        if x_dev_role not in ROLES:
            raise HTTPException(400, "unknown role")
        return Principal("dev", x_dev_role, x_dev_district, f"Dev {x_dev_role.title()}")
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(401, "sign in required")
    claims = verify_token(authorization.split(" ", 1)[1])
    return _profile(claims["sub"])


PUBLIC = Principal("public", "PUBLIC", None, "Public view")


def viewer(authorization: str | None = Header(default=None),
           x_dev_role: str | None = Header(default=None),
           x_dev_district: str | None = Header(default=None)) -> Principal:
    """Who is looking, for read-only routes (T130): the signed-in user when the session is
    good, else the PUBLIC viewer of all districts. A stale token in an old tab never locks a
    visitor out of viewing; it grants nothing more than no token does."""
    if not authorization and not (_dev_mode() and x_dev_role):
        return PUBLIC
    try:
        return current_user(authorization, x_dev_role, x_dev_district)
    except (HTTPException, jwt.PyJWTError, httpx.HTTPError, ValueError, KeyError):
        return PUBLIC
