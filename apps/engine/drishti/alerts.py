"""Alerts: every review-queue case, its lifecycle, and the audit log of every change (T060).

    NEW -> TRIAGED -> IN_PLAN -> INSPECTED -> ISSUE_CONFIRMED / CLEARED -> CLOSED
                  \\-> CLOSED (no visit needed: a note is required, and the digest names it)

On screen each step is named for what it means, not office jargon (LABELS): Not read yet, Read by
the office (an officer has read the reasons and chosen: plan a visit or close with a reason),
Visit planned, Site visited, Problem found / No problem found, Closed.

A queue case with no row in `alerts` is New; its row and the log's 'open' entry are written at
its first move (migration 015). Each audit entry carries the hash of the entry before it, so a
changed or removed past entry breaks the chain from that point on (`verify_chain`); the database
also refuses UPDATE, DELETE and TRUNCATE on the log.

Who may move a case: the district triages, plans and closes; the field officer (or the district)
records the visit and its verdict; the ministry may triage and close but plans no visits.

    python -m drishti.alerts digest      the daily digest for the database in DATABASE_URL
"""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime, timedelta

STATES = ("NEW", "TRIAGED", "IN_PLAN", "INSPECTED", "ISSUE_CONFIRMED", "CLEARED", "CLOSED")
# plain words, not office jargon: officers and the public read these (the web mirrors them)
LABELS = {"NEW": "Not read yet", "TRIAGED": "Read by the office", "IN_PLAN": "Visit planned",
          "INSPECTED": "Site visited", "ISSUE_CONFIRMED": "Problem found",
          "CLEARED": "No problem found", "CLOSED": "Closed"}
MOVES: dict[tuple[str, str], frozenset[str]] = {
    ("NEW", "TRIAGED"): frozenset({"DISTRICT", "MINISTRY"}),
    ("TRIAGED", "IN_PLAN"): frozenset({"DISTRICT"}),
    ("TRIAGED", "CLOSED"): frozenset({"DISTRICT", "MINISTRY"}),
    ("IN_PLAN", "INSPECTED"): frozenset({"DISTRICT", "FIELD"}),
    ("INSPECTED", "ISSUE_CONFIRMED"): frozenset({"DISTRICT", "FIELD"}),
    ("INSPECTED", "CLEARED"): frozenset({"DISTRICT", "FIELD"}),
    ("ISSUE_CONFIRMED", "CLOSED"): frozenset({"DISTRICT", "MINISTRY"}),
    ("CLEARED", "CLOSED"): frozenset({"DISTRICT", "MINISTRY"}),
}
# a verdict says what was seen; closing without a visit says why no visit was needed
NOTE_NEEDED = frozenset({("INSPECTED", "ISSUE_CONFIRMED"), ("INSPECTED", "CLEARED"),
                         ("TRIAGED", "CLOSED")})
GENESIS = "0" * 64
LOCK_KEY = 60060                  # pg_advisory_xact_lock: one writer at a time keeps one chain
STALE_DAYS = 14


class MoveError(Exception):
    def __init__(self, status: int, detail: str):
        super().__init__(detail)
        self.status = status
        self.detail = detail


def moves_for(state: str, role: str) -> list[str]:
    """The states this role may move a case in `state` to, in lifecycle order."""
    return [to for to in STATES if role in MOVES.get((state, to), ())]


def check_move(state: str, frm: str, to: str, role: str, note: str | None) -> None:
    if frm != state:
        raise MoveError(409, f"someone has already moved this case on to \"{LABELS[state]}\"; "
                             f"reload to see the latest")
    if (frm, to) not in MOVES:
        raise MoveError(400, f"a case at \"{LABELS[frm]}\" cannot move straight to "
                             f"\"{LABELS[to]}\"")
    if role not in MOVES[(frm, to)]:
        raise MoveError(403, f"a {role.lower()} account cannot move a case to \"{LABELS[to]}\"")
    if (frm, to) in NOTE_NEEDED and not (note or "").strip():
        raise MoveError(400, f"moving a case to \"{LABELS[to]}\" needs a note saying why")


def _utc(at: datetime) -> str:
    return at.astimezone(UTC).isoformat()


def entry_hash(prev: str, e: dict) -> str:
    body = {"prev": prev, "seq": e["seq"], "at": _utc(e["at"]), "alert_id": e["alert_id"],
            "actor_id": e["actor_id"], "actor_role": e["actor_role"],
            "actor_name": e["actor_name"], "action": e["action"],
            "from_state": e["from_state"], "to_state": e["to_state"], "note": e["note"]}
    raw = json.dumps(body, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def lock(con) -> None:
    con.execute("SELECT pg_advisory_xact_lock(%s)", (LOCK_KEY,))


def append(con, *, alert_id: str, actor, action: str, from_state: str | None, to_state: str,
           note: str | None, at: datetime) -> dict:
    """Add one entry at the end of the chain. The caller holds `lock(con)`."""
    last = con.execute("SELECT seq, hash FROM audit_log ORDER BY seq DESC LIMIT 1").fetchone()
    e = {"seq": (last["seq"] + 1) if last else 1, "at": at, "alert_id": alert_id,
         "actor_id": actor.user_id, "actor_role": actor.role, "actor_name": actor.name,
         "action": action, "from_state": from_state, "to_state": to_state, "note": note}
    prev = last["hash"] if last else GENESIS
    e["prev_hash"], e["hash"] = prev, entry_hash(prev, e)
    con.execute("INSERT INTO audit_log (seq, at, alert_id, actor_id, actor_role, actor_name, "
                "action, from_state, to_state, note, prev_hash, hash) VALUES (%(seq)s, %(at)s, "
                "%(alert_id)s, %(actor_id)s, %(actor_role)s, %(actor_name)s, %(action)s, "
                "%(from_state)s, %(to_state)s, %(note)s, %(prev_hash)s, %(hash)s)", e)
    return e


def verify_chain(con) -> dict:
    """Walk the whole log: each entry must point at the one before and hash to its own hash.
    broken_at = the first seq where that fails (a removed entry breaks the one after it)."""
    prev, n = GENESIS, 0
    for e in con.execute("SELECT * FROM audit_log ORDER BY seq"):
        n += 1
        if e["prev_hash"] != prev or entry_hash(prev, e) != e["hash"]:
            rest = con.execute("SELECT count(*) AS n FROM audit_log WHERE seq > %s",
                               (e["seq"],)).fetchone()["n"]
            return {"ok": False, "entries": n + rest, "broken_at": e["seq"]}
        prev = e["hash"]
    return {"ok": True, "entries": n, "broken_at": None}


def ready(con) -> bool:
    return con.execute("SELECT to_regclass('alerts') IS NOT NULL "
                       "AND to_regclass('audit_log') IS NOT NULL AS ok").fetchone()["ok"]


# ---- the daily digest -----------------------------------------------------------------------

def digest(con, now: datetime, stale_days: int = STALE_DAYS) -> str:
    """One line per district: cases in each state, those waiting too long, and cases closed in
    the last week without a visit (each is allowed, with a note; the digest makes them seen)."""
    stale_at = now - timedelta(days=stale_days)
    week_ago = now - timedelta(days=7)
    rows = con.execute(
        "WITH q AS (SELECT DISTINCT ON (coalesce(a.case_id, w.work_id)) "
        "coalesce(a.case_id, w.work_id) AS key, w.district_lgd, a.assessed_at "
        "FROM works w JOIN assessments a USING (work_id) WHERE a.band IN ('CRITICAL', 'HIGH') "
        "ORDER BY coalesce(a.case_id, w.work_id), a.priority DESC NULLS LAST) "
        "SELECT coalesce(al.district_lgd, q.district_lgd) AS district_lgd, "
        "coalesce(al.state, 'NEW') AS state, coalesce(al.updated_at, q.assessed_at) AS since "
        "FROM q FULL JOIN alerts al ON al.alert_id = q.key").fetchall()
    names = {r["district_lgd"]: r["name"]
             for r in con.execute("SELECT district_lgd, name FROM districts")}
    no_visit = {}
    for r in con.execute("SELECT al.district_lgd, count(*) AS n FROM audit_log l "
                         "JOIN alerts al USING (alert_id) WHERE l.from_state = 'TRIAGED' "
                         "AND l.to_state = 'CLOSED' AND l.at >= %s GROUP BY al.district_lgd",
                         (week_ago,)):
        no_visit[r["district_lgd"]] = r["n"]
    per: dict[str, dict] = {}
    for r in rows:
        d = per.setdefault(r["district_lgd"], {s: 0 for s in STATES} | {"stale": 0})
        d[r["state"]] += 1
        if r["state"] != "CLOSED" and r["since"] is not None and r["since"] < stale_at:
            d["stale"] += 1
    lines = [f"NidhiNetra alerts digest, {now.astimezone(UTC):%d %b %Y %H:%M} UTC"]
    for dl in sorted(set(per) | set(no_visit), key=lambda k: names.get(k) or str(k)):
        d = per.get(dl, {s: 0 for s in STATES} | {"stale": 0})
        parts = []
        for s in STATES[:-1]:
            if d[s] or s == "NEW":
                parts.append(f"{d[s]} {LABELS[s].lower()}")
        if d["stale"]:
            parts[0] += f" ({d['stale']} waiting over {stale_days} days)"
        if no_visit.get(dl):
            parts.append(f"{no_visit[dl]} closed without a visit this week")
        if not any(d[s] for s in STATES[:-1]) and not no_visit.get(dl):
            continue
        lines.append(f"{names.get(dl) or dl or 'district not known'}: {', '.join(parts)}")
    c = verify_chain(con)
    lines.append(f"audit chain: {'intact' if c['ok'] else 'BROKEN at entry ' + str(c['broken_at'])}"
                 f", {c['entries']} entries")
    return "\n".join(lines)


if __name__ == "__main__":
    import sys

    from drishti.db import connect

    if sys.argv[1:] != ["digest"]:
        sys.exit("usage: python -m drishti.alerts digest")
    with connect() as con:
        if not ready(con):
            sys.exit("alerts are not set up on this database yet (migration 015_alerts.sql)")
        print(digest(con, now=datetime.now(UTC)))
