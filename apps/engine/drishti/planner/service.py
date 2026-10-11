"""A district's plan for one day, from the database (T062). Nothing is stored: a plan's id holds
its inputs (district, day, hours), so the same id always gives the same plan.

  flagged     the district's review-queue cases (band CRITICAL or HIGH, one stop per case: the
              queue page's rule), valued by their stored priority
  spot        10% as many random lower-risk works (at least 1), sanctioned or completed (there is
              something at the site), drawn by a hash of the plan's id: the same plan always has
              the same spot checks, and the next day's plan has others
  checklist   each flagged stop's own top reasons (English and Hindi), then the visit's verdict
"""

from __future__ import annotations

import math
import re
from datetime import date, datetime, timedelta

from drishti.planner import plan as P
from drishti.planner.locate import Location, district_start, locate
from drishti.validation import pii

SPOT_SHARE = 0.10
DAY_STARTS = "09:00"
ID = re.compile(r"^(?P<district>[0-9A-Za-z]{1,8})_(?P<day>\d{4}-\d{2}-\d{2})_(?P<hours>\d{1,2})$")
MIN_HOURS, MAX_HOURS = 2, 12

VERDICT = ("Record what you found: the work matches the record, or it needs follow-up.",
           "जो मिला वह दर्ज करें: कार्य रिकॉर्ड से मेल खाता है, या आगे जाँच चाहिए।")
SPOT = ("Random spot check, not a finding: confirm the work exists as recorded and photograph it.",
        "यादृच्छिक जाँच, कोई निष्कर्ष नहीं: पुष्टि करें कि कार्य दर्ज विवरण के अनुसार मौजूद है "
        "और उसकी फ़ोटो लें।")
NOTES = [
    "Places are approximate. eSAKSHI records only a work's district; the planner reads the "
    "village or block named in the description and finds its post office. A stop marked "
    "'district' could not be placed and sits at the district's start point.",
    "Distances are estimates: the straight line x 1.3 for winding roads, at 30 km/h, with 40 "
    "minutes at each stop.",
    "A flagged work needs checking; it is not a finding against anyone.",
]


def plan_id(district: str, day: date, hours: int) -> str:
    return f"{district}_{day.isoformat()}_{hours}"


def parse_id(pid: str) -> tuple[str, date, int] | None:
    m = ID.match(pid or "")
    if not m:
        return None
    try:
        day = date.fromisoformat(m["day"])
    except ValueError:
        return None
    hours = int(m["hours"])
    if not MIN_HOURS <= hours <= MAX_HOURS:
        return None
    return m["district"], day, hours


QUEUE_SQL = """
SELECT * FROM (
  SELECT DISTINCT ON (coalesce(a.case_id, w.work_id))
         w.work_id, w.description, w.amount, w.status, w.work_type_code, w.recommended_date,
         a.band, a.score, a.priority, a.headline, a.parts, a.case_size
  FROM works w JOIN assessments a USING (work_id)
  WHERE w.district_lgd = %s AND a.band IN ('CRITICAL', 'HIGH')
  ORDER BY coalesce(a.case_id, w.work_id), a.priority DESC NULLS LAST, w.work_id
) one_per_case ORDER BY priority DESC NULLS LAST, work_id
"""

SPOT_SQL = """
SELECT w.work_id, w.description, w.amount, w.status, w.work_type_code, w.recommended_date,
       a.band, a.score
FROM works w LEFT JOIN assessments a USING (work_id)
WHERE w.district_lgd = %s AND coalesce(a.band, 'LOW') NOT IN ('CRITICAL', 'HIGH')
  AND w.status IN ('SANCTIONED', 'COMPLETED')
ORDER BY md5(w.work_id || %s), w.work_id
LIMIT %s
"""


def _num(v) -> float | None:
    return None if v is None else float(v)


def _checklist(row: dict) -> list[dict]:
    reasons = ((row.get("parts") or {}).get("reasons") or [])[:3]
    items = [{"en": pii.mask(r.get("text_en")), "hi": pii.mask(r.get("text_hi")),
              "check": r.get("source")} for r in reasons if r.get("text_en")]
    if not items and row.get("headline"):
        items = [{"en": pii.mask(row["headline"]), "hi": None, "check": None}]
    return items + [{"en": VERDICT[0], "hi": VERDICT[1], "check": None}]


def _place(loc: Location) -> dict:
    return {"lat": loc.lat, "lon": loc.lon, "precision": loc.precision,
            "place": loc.place.title() if loc.place else None}


def _work(row: dict, kind: str) -> dict:
    out = {
        "work_id": row["work_id"], "kind": kind,
        "description": pii.mask(row.get("description")),
        "amount": _num(row.get("amount")), "status": row.get("status"),
        "work_type_code": row.get("work_type_code"),
        "band": row.get("band"), "score": _num(row.get("score")),
        "case_size": row.get("case_size"),
    }
    if kind == "flagged":
        out["headline"] = pii.mask(row.get("headline"))
        out["checklist"] = _checklist(row)
    else:
        out["checklist"] = [{"en": SPOT[0], "hi": SPOT[1], "check": None}]
    return out


def _clock(minutes: float) -> str:
    t = datetime.strptime(DAY_STARTS, "%H:%M") + timedelta(minutes=round(minutes))
    return t.strftime("%H:%M")


def generate(con, district: str, day: date, hours: int, scope_where: str = "TRUE",
             scope_args: tuple = ()) -> dict | None:
    """The plan, or None when the district is unknown (or outside the user's area)."""
    meta = con.execute(
        f"SELECT w.district_lgd, max(w.district_name) AS district_name, "
        f"max(w.state_name) AS state_name FROM works w "
        f"WHERE w.district_lgd = %s AND {scope_where} GROUP BY w.district_lgd",
        (district, *scope_args)).fetchone()
    start = district_start(district)
    if meta is None or start is None:
        return None
    pid = plan_id(district, day, hours)
    flagged_rows = con.execute(QUEUE_SQL, (district,)).fetchall()
    k = max(1, math.ceil(SPOT_SHARE * len(flagged_rows))) if flagged_rows else 0
    spot_rows = con.execute(SPOT_SQL, (district, pid, k)).fetchall() if k else []

    works: dict[str, dict] = {}
    stops: dict[str, list[P.Stop]] = {"flagged": [], "spot": []}
    for kind, rows in (("flagged", flagged_rows), ("spot", spot_rows)):
        for r in rows:
            loc = locate(district, r.get("description")) or start
            works[r["work_id"]] = {**_work(dict(r), kind), "location": _place(loc)}
            value = float(r["priority"] or 0.0) if kind == "flagged" else 0.0
            stops[kind].append(P.Stop(r["work_id"], loc.lat, loc.lon, value, kind))

    home = (start.lat, start.lon)
    chosen = P.choose(home, stops["flagged"], stops["spot"], hours * 60.0)
    out_stops, here, clock = [], home, 0.0
    for i, s in enumerate(chosen.route, 1):
        leg = P.road_km(here, (s.lat, s.lon))
        clock += leg / P.SPEED_KMH * 60.0
        out_stops.append({"order": i, **works[s.key], "drive_km": round(leg, 1),
                          "arrive": _clock(clock), "leave": _clock(clock + P.STOP_MIN)})
        clock += P.STOP_MIN
        here = (s.lat, s.lon)
    back = P.road_km(here, home) if chosen.route else 0.0
    planned_km = P.tour_km(home, chosen.route)
    list_km = P.tour_km(home, P.list_order(chosen.route))
    precision: dict[str, int] = {}
    for w in works.values():
        p = w["location"]["precision"]
        precision[p] = precision.get(p, 0) + 1
    return {
        "id": pid, "date": day.isoformat(), "hours": hours,
        "district": {"code": district, "name": meta["district_name"],
                     "state": meta["state_name"]},
        "start": {**_place(start), "label": (start.place or "district centre").title()},
        "stops": out_stops,
        "next_trip": [works[s.key] for s in chosen.left],
        "spot_not_fitted": [works[s.key] for s in chosen.left_spot],
        "totals": {
            "flagged_in_queue": len(flagged_rows), "spot_checks_drawn": len(spot_rows),
            "stops": len(chosen.route),
            "flagged_visited": sum(s.kind == "flagged" for s in chosen.route),
            "road_km": round(planned_km, 1),
            "minutes": round(P.tour_minutes(home, chosen.route)),
            "back_by": _clock(clock + back / P.SPEED_KMH * 60.0) if chosen.route else None,
            "list_order_km": round(list_km, 1),
            "km_saved": round(list_km - planned_km, 1),
        },
        "precision": precision,
        "rules": {"speed_kmh": P.SPEED_KMH, "road_factor": P.ROAD_FACTOR,
                  "stop_minutes": P.STOP_MIN, "spot_share": SPOT_SHARE},
        "notes": NOTES,
    }
