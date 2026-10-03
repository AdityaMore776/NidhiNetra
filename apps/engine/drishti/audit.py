"""The audit trail: one append-only row per thing an officer did (T060).

Why a hash chain. A plain log of actions can be edited: someone with database
access changes what a row says, or removes it, and nothing afterwards notices. So
each row carries the hash of the row before it. Change or delete any earlier row
and every hash after it no longer matches, and `verify_chain()` says exactly
which row it broke at.

What is recorded is what was *done* to a work record - acknowledged, asked for a
visit, saw the work - never a judgement about a person, and never an MP's name.
That is the same wording rule the engines follow (drishti/agents/contract.py).

The entry_id is deliberately outside the hash. It is the chain's position, not
part of what the officer did, so re-numbering rows after a restore cannot be
mistaken for a rewritten action.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

# any value works as long as every writer uses the same one; this is a domain
# separator so a hash from here can never be mistaken for a hash from elsewhere
DOMAIN = "drishti-audit-v1"

GENESIS = "0" * 64

# one lock for the whole table: appending must be serialised, or two officers
# acting at the same moment would read the same prev_hash and fork the chain
_LOCK = 4711


def canonical(entry: dict[str, Any]) -> str:
    """The exact text that gets hashed, so a re-read produces the same hash.

    Keys sorted, no whitespace, and a fixed separator for times. Postgres hands
    back a datetime with a timezone attached and Python's str() of it varies with
    the session's settings, so any timestamp is normalised to UTC ISO first.
    """
    def plain(value: Any) -> Any:
        if hasattr(value, "isoformat"):
            return value.astimezone(value.tzinfo).isoformat() if value.tzinfo else value.isoformat()
        if isinstance(value, dict):
            return {k: plain(v) for k, v in value.items()}
        if isinstance(value, (list, tuple)):
            return [plain(v) for v in value]
        return value

    body = {k: plain(v) for k, v in entry.items() if k not in ("hash", "prev_hash")}
    return json.dumps(body, sort_keys=True, separators=(",", ":"), default=str)


def hash_of(prev_hash: str, entry: dict[str, Any]) -> str:
    """The hash of one entry: the previous entry's hash, then this entry's own text."""
    payload = f"{DOMAIN}\n{prev_hash}\n{canonical(entry)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def record(con, *, actor: str, role: str, action: str, entity: str, entity_id: Any,
           work_id: str | None = None, before: dict | None = None,
           after: dict | None = None, note: str | None = None) -> dict:
    """Append one entry and return it.

    Takes the caller's open connection and commits nothing: the caller is already
    inside the transaction that made the change, so the entry and the change land
    together or not at all.
    """
    with con.cursor() as cur:
        # serialise every append, so the chain has one order and cannot fork
        cur.execute("SELECT pg_advisory_xact_lock(%s)", (_LOCK,))
        cur.execute("SELECT hash FROM audit_log ORDER BY entry_id DESC LIMIT 1")
        row = cur.fetchone()
        prev_hash = row["hash"] if row else GENESIS

        # The moment is taken from the database and then hashed with everything
        # else, so a re-read of the row reproduces the same hash. Letting the
        # column default to now() would leave the time outside the hash, and a row
        # could then have its timestamp rewritten without the chain noticing.
        cur.execute("SELECT now() AS at")
        at = cur.fetchone()["at"]
        entry = {"actor": actor, "role": role, "action": action, "entity": entity,
                 "entity_id": str(entity_id), "work_id": work_id, "before": before,
                 "after": after, "note": note, "at": at}
        digest = hash_of(prev_hash, entry)
        cur.execute(
            "INSERT INTO audit_log (actor, role, action, entity, entity_id, work_id, "
            "before, after, note, at, prev_hash, hash) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
            "RETURNING entry_id",
            (actor, role, action, entity, str(entity_id), work_id,
             json.dumps(before) if before else None,
             json.dumps(after) if after else None,
             note, at, prev_hash, digest))
        entry_id = cur.fetchone()["entry_id"]
    return {**entry, "entry_id": entry_id, "prev_hash": prev_hash, "hash": digest}


def verify_chain(con) -> dict:
    """Walk the chain and report where, if anywhere, it no longer holds.

    Returns {"ok": True, "entries": n} or {"ok": False, "entries": n, "broken_at": id,
    "why": "..."}. Callers show this to an officer rather than trusting it silently:
    a chain that verifies is the claim being made, not a background assumption.
    """
    with con.cursor() as cur:
        cur.execute("SELECT entry_id, prev_hash, hash, actor, role, action, entity, "
                    "entity_id, work_id, before, after, note, at FROM audit_log ORDER BY entry_id")
        rows = cur.fetchall()

    prev = GENESIS
    for r in rows:
        fields = {"actor": r["actor"], "role": r["role"], "action": r["action"],
                  "entity": r["entity"], "entity_id": r["entity_id"], "work_id": r["work_id"],
                  "before": r["before"], "after": r["after"], "note": r["note"],
                  "at": r["at"]}
        if r["prev_hash"] != prev:
            return {"ok": False, "entries": len(rows), "broken_at": r["entry_id"],
                    "why": "this entry does not follow the one before it: an earlier row "
                           "was changed or removed"}
        if hash_of(prev, fields) != r["hash"]:
            return {"ok": False, "entries": len(rows), "broken_at": r["entry_id"],
                    "why": "this entry's own text no longer matches its hash: the row "
                           "was edited after it was written"}
        prev = r["hash"]
    return {"ok": True, "entries": len(rows)}


def for_work(con, work_id: str) -> list[dict]:
    """Everything done about one work, oldest first. What the work's page shows."""
    with con.cursor() as cur:
        cur.execute("SELECT entry_id, at, actor, role, action, note FROM audit_log "
                    "WHERE work_id = %s ORDER BY entry_id", (work_id,))
        return [{"entry_id": r["entry_id"], "at": r["at"], "actor": r["actor"],
                 "role": r["role"], "action": r["action"], "note": r["note"]}
                for r in cur.fetchall()]