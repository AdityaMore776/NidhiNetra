"""Capture tokens and storage for site visits (T123, plan T120 §9.4 check 1).

A capture token is issued when filming STARTS: an HMAC over (visit, work, kind, user, time) with
the server's secret DRISHTI_CAPTURE_SECRET. The upload must come back with that token, so a
visit is always tied to a filming the server saw begin, for that work, by that person; and the
video's SHA-256, computed by the capture page when filming ENDS, is stored with it. The video job
recomputes the hash of what reached storage: an edited file breaks the match ("sealed": false).

Honest limit, stated on the work page: in a phone's browser the page itself computes the hash, so
a modified page could seal a prepared file. The views must still match the site's own earlier
views, and the reuse check still runs; the Android app (later) moves the seal into the phone.

Storage is Supabase Storage (free tier) through its REST API with the service role key
(server-side only): the engine hands the page a one-time signed upload URL, so a video never
passes through the engine (Vercel functions take at most a few MB).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from dataclasses import dataclass

import httpx

TOKEN_TTL_S = 7 * 24 * 3600       # film offline, upload within a week
BUCKET = os.environ.get("DRISHTI_VIDEO_BUCKET", "site-visits")


class NotSetUp(RuntimeError):
    """A setting the feature needs is missing: the route answers 503, never a guess."""


def _secret() -> bytes:
    s = os.environ.get("DRISHTI_CAPTURE_SECRET", "")
    if len(s) < 16:
        raise NotSetUp("DRISHTI_CAPTURE_SECRET is not set (16+ characters)")
    return s.encode("utf-8")


def _b64(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).rstrip(b"=").decode("ascii")


def _unb64(s: str) -> bytes:
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


@dataclass(frozen=True)
class Claims:
    visit_id: str
    work_id: str
    kind: str
    user_id: str
    issued: int


def issue(visit_id: str, work_id: str, kind: str, user_id: str, now: int | None = None) -> str:
    body = json.dumps({"v": visit_id, "w": work_id, "k": kind, "u": user_id,
                       "t": int(now if now is not None else time.time())},
                      separators=(",", ":"), sort_keys=True).encode("utf-8")
    sig = hmac.new(_secret(), body, hashlib.sha256).digest()
    return f"{_b64(body)}.{_b64(sig)}"


def seed(visit_id: str) -> bytes:
    """A per-visit random seed only the server can compute (T158: the stretches of a long road a
    visit is asked to film are drawn from it when filming starts)."""
    return hmac.new(_secret(), b"stretches|" + visit_id.encode("utf-8"), hashlib.sha256).digest()


def check(token: str, now: int | None = None) -> Claims | None:
    """The token's claims when it is ours and not expired, else None."""
    try:
        body_s, sig_s = token.split(".", 1)
        body = _unb64(body_s)
        if not hmac.compare_digest(hmac.new(_secret(), body, hashlib.sha256).digest(),
                                   _unb64(sig_s)):
            return None
        d = json.loads(body)
        c = Claims(str(d["v"]), str(d["w"]), str(d["k"]), str(d["u"]), int(d["t"]))
    except (ValueError, KeyError, TypeError, AttributeError):
        return None
    t = int(now if now is not None else time.time())
    return c if 0 <= t - c.issued <= TOKEN_TTL_S else None


def _storage() -> tuple[str, str]:
    url, key = os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    if not url or not key:
        raise NotSetUp("storage is not set up (SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)")
    return url.rstrip("/"), key


def signed_upload(path: str, client=None) -> str:
    """A one-time URL the capture page PUTs the video to (Supabase Storage)."""
    base, key = _storage()
    http = client or httpx
    r = http.post(f"{base}/storage/v1/object/upload/sign/{BUCKET}/{path}",
                  headers={"Authorization": f"Bearer {key}", "apikey": key}, timeout=20)
    r.raise_for_status()
    part = r.json().get("url") or ""
    return f"{base}/storage/v1{part}" if part.startswith("/") else part


def signed_download(path: str, seconds: int = 3600, client=None) -> str:
    base, key = _storage()
    http = client or httpx
    r = http.post(f"{base}/storage/v1/object/sign/{BUCKET}/{path}",
                  headers={"Authorization": f"Bearer {key}", "apikey": key},
                  json={"expiresIn": seconds}, timeout=20)
    r.raise_for_status()
    part = r.json().get("signedURL") or r.json().get("signedUrl") or ""
    return f"{base}/storage/v1{part}" if part.startswith("/") else part


# ---- the video job's storage (server-side; the same bucket) ------------------------------------

class SupabaseStore:
    """Objects in the Supabase Storage bucket, with the service role key."""

    def __init__(self, client=None) -> None:
        self.base, self.key = _storage()
        self.http = client or httpx

    def _h(self, **extra) -> dict:
        return {"Authorization": f"Bearer {self.key}", "apikey": self.key, **extra}

    def get(self, path: str) -> bytes:
        r = self.http.get(f"{self.base}/storage/v1/object/{BUCKET}/{path}", headers=self._h(),
                          timeout=120)
        r.raise_for_status()
        return r.content

    def put(self, path: str, data: bytes, content_type: str = "image/jpeg") -> None:
        r = self.http.post(f"{self.base}/storage/v1/object/{BUCKET}/{path}", content=data,
                           headers=self._h(**{"Content-Type": content_type,
                                              "x-upsert": "true"}), timeout=60)
        r.raise_for_status()

    def delete(self, path: str) -> None:
        r = self.http.request("DELETE", f"{self.base}/storage/v1/object/{BUCKET}",
                              headers=self._h(), json={"prefixes": [path]}, timeout=60)
        r.raise_for_status()


class LocalStore:
    """Objects in a folder: for trials and tests (never for real videos in the repository)."""

    def __init__(self, root) -> None:
        from pathlib import Path
        self.root = Path(root)

    def get(self, path: str) -> bytes:
        return (self.root / path).read_bytes()

    def put(self, path: str, data: bytes, content_type: str = "image/jpeg") -> None:
        p = self.root / path
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)

    def delete(self, path: str) -> None:
        (self.root / path).unlink(missing_ok=True)
