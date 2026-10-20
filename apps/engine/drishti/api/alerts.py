"""Alerts: the review queue's cases with their lifecycle and audit trail (T060; migration 015).

    GET   /api/v1/alerts?state=&district=&page=   the cases in your area, open ones by default
                                                  (state=ALL for every case, or one state), with
                                                  counts per state and the moves you may make
    GET   /api/v1/alerts/audit/verify             the whole audit chain checked (ministry only)
    GET   /api/v1/alerts/{alert_id}               one case with its full trail
    PATCH /api/v1/alerts/{alert_id}               {from_state, to_state, note} -> the moved case

Staff only: these need a signed-in account (the public view has the prototype examples). District
scoping as everywhere: a district or field officer reaches only their district's cases, and a
case outside it answers 404, as if it did not exist. Without migration 015 the routes answer 503
and the rest of the site carries on.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Body, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from drishti import alerts
from drishti.api.routes import PAGE, _jsonable
from drishti.auth import Principal, current_user
from drishti.db import connect

router = APIRouter(prefix="/api/v1")
State = Literal["NEW", "TRIAGED", "IN_PLAN", "INSPECTED", "ISSUE_CONFIRMED", "CLEARED", "CLOSED"]

# one row per queue case (as /queue, migration 012), led by its highest-priority work
_QUEUE = ("SELECT DISTINCT ON (coalesce(a.case_id, w.work_id)) coalesce(a.case_id, w.work_id) "
          "AS key, w.work_id, w.district_lgd FROM works w JOIN assessments a USING (work_id) "
          "WHERE a.band IN ('CRITICAL', 'HIGH') AND {qscope} "
          "ORDER BY coalesce(a.case_id, w.work_id), a.priority DESC NULLS LAST, w.work_id")
_CASES = (f"WITH q AS ({_QUEUE}), al AS (SELECT * FROM alerts WHERE {{ascope}}), "
          "c AS (SELECT coalesce(q.key, al.alert_id) AS alert_id, "
          "coalesce(al.state, 'NEW') AS state, (q.key IS NOT NULL) AS in_queue, "
          "coalesce(q.work_id, al.work_id) AS work_id, "
          "coalesce(q.district_lgd, al.district_lgd) AS district_lgd, "
          "al.updated_at, al.updated_by, al.note "
          "FROM q FULL JOIN al ON al.alert_id = q.key) ")
_COLUMNS = ("c.*, w.district_name, w.state_name, w.work_type_code, w.description, w.amount, "
            "w.status, a.band, a.score, a.priority, a.headline, a.case_size")
_DETAIL = ("LEFT JOIN works w ON w.work_id = c.work_id "
           "LEFT JOIN assessments a ON a.work_id = c.work_id")


class Move(BaseModel):
    from_state: State
    to_state: State
    note: str | None = Field(default=None, max_length=500)


def _ready(con) -> None:
    if not alerts.ready(con):
        raise HTTPException(503, "alerts are not set up on this database yet "
                                 "(migration 015_alerts.sql)")


def _scoped(user: Principal) -> tuple[str, list]:
    d = user.scope_district()
    if d is None:
        return _CASES.format(qscope="TRUE", ascope="TRUE"), []
    return (_CASES.format(qscope="w.district_lgd = %s", ascope="district_lgd = %s"), [d, d])


def _shape(row: dict, user: Principal) -> dict:
    out = _jsonable(row)
    out["label"] = alerts.LABELS[row["state"]]
    out["moves"] = alerts.moves_for(row["state"], user.role)
    if isinstance(row.get("updated_at"), datetime):
        out["updated_at"] = row["updated_at"].astimezone(UTC).isoformat()
    return out


def _one(con, alert_id: str, user: Principal) -> dict:
    sql, args = _scoped(user)
    row = con.execute(f"{sql} SELECT {_COLUMNS} FROM c {_DETAIL} WHERE c.alert_id = %s",
                      args + [alert_id]).fetchone()
    if row is None:
        raise HTTPException(404, "no such case in your area")
    return dict(row)


def _trail(con, alert_id: str) -> list[dict]:
    rows = con.execute("SELECT seq, at, action, from_state, to_state, note, actor_role, "
                       "actor_name FROM audit_log WHERE alert_id = %s ORDER BY seq",
                       (alert_id,)).fetchall()
    return [{**r, "at": r["at"].astimezone(UTC).isoformat()} for r in rows]


@router.get("/alerts")
def list_alerts(state: str | None = None, district: str | None = None,
                page: int = Query(default=1, ge=1),
                user: Principal = Depends(current_user)) -> dict:
    if state not in (None, "ALL", *alerts.STATES):
        raise HTTPException(422, "unknown state")
    sql, args = _scoped(user)
    area, aargs = ("c.district_lgd = %s", [district]) if district else ("TRUE", [])
    if state is None:
        cond, wargs = f"{area} AND c.state <> 'CLOSED'", aargs
    elif state == "ALL":
        cond, wargs = area, aargs
    else:
        cond, wargs = f"{area} AND c.state = %s", aargs + [state]
    with connect() as con:
        _ready(con)
        counts = {s: 0 for s in alerts.STATES}
        for r in con.execute(f"{sql} SELECT c.state, count(*) AS n FROM c WHERE {area} "
                             f"GROUP BY c.state", args + aargs):
            counts[r["state"]] = r["n"]
        total = con.execute(f"{sql} SELECT count(*) AS n FROM c WHERE {cond}",
                            args + wargs).fetchone()["n"]
        rows = con.execute(f"{sql} SELECT {_COLUMNS} FROM c {_DETAIL} WHERE {cond} "
                           f"ORDER BY c.in_queue DESC, a.priority DESC NULLS LAST, c.alert_id "
                           f"LIMIT %s OFFSET %s", args + wargs + [PAGE, (page - 1) * PAGE])
        items = [_shape(dict(r), user) for r in rows]
    return {"total": total, "page": page, "page_size": PAGE, "counts": counts, "items": items}


@router.get("/alerts/audit/verify")
def verify(user: Principal = Depends(current_user)) -> dict:
    if user.role != "MINISTRY":
        raise HTTPException(403, "the audit chain check is for ministry accounts")
    with connect() as con:
        _ready(con)
        return alerts.verify_chain(con)


@router.get("/alerts/{alert_id:path}")
def get_alert(alert_id: str, user: Principal = Depends(current_user)) -> dict:
    with connect() as con:
        _ready(con)
        out = _shape(_one(con, alert_id, user), user)
        out["trail"] = _trail(con, alert_id)
    return out


@router.patch("/alerts/{alert_id:path}")
def move_alert(alert_id: str, move: Move = Body(...),
               user: Principal = Depends(current_user)) -> dict:
    note = (move.note or "").strip() or None
    with connect() as con:
        _ready(con)
        alerts.lock(con)                      # one writer at a time: one state, one chain
        case = _one(con, alert_id, user)
        try:
            alerts.check_move(case["state"], move.from_state, move.to_state, user.role, note)
        except alerts.MoveError as e:
            raise HTTPException(e.status, e.detail) from e
        now = datetime.now(UTC)
        if case["updated_at"] is None:        # first move: the case gets its row and 'open'
            con.execute("INSERT INTO alerts (alert_id, work_id, district_lgd, state, opened_at, "
                        "updated_at, updated_by) VALUES (%s, %s, %s, 'NEW', %s, %s, %s)",
                        (alert_id, case["work_id"], case["district_lgd"], now, now,
                         user.user_id))
            alerts.append(con, alert_id=alert_id, actor=user, action="open", from_state=None,
                          to_state="NEW", note=None, at=now)
        con.execute("UPDATE alerts SET state = %s, updated_at = %s, updated_by = %s, note = %s "
                    "WHERE alert_id = %s", (move.to_state, now, user.user_id, note, alert_id))
        alerts.append(con, alert_id=alert_id, actor=user, action="move",
                      from_state=move.from_state, to_state=move.to_state, note=note, at=now)
        out = _shape(_one(con, alert_id, user), user)
        out["trail"] = _trail(con, alert_id)
    return out
