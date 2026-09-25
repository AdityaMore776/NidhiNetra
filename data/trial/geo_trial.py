r"""Trial 8 - Geo-Location on the real evidence: read the GPS stamp, then check place and time.

GPS-camera apps (GPS Map Camera, NoteCam, ...) burn latitude/longitude, address, PIN code and
time into the picture. The phone's own location data is usually stripped by the upload, so
the stamp is the only location there is. From the local OCR text (ocr_pages.py):

  1. read lat/long, date and PIN code from each photo's stamp (and GPS pages inside PDFs)
  2. place - is the point inside the district the work belongs to (official LGD outline)?
             if not, which district is it in, and how far outside?
  3. time  - is the stamp dated between recommendation and completion (+ 1 year)?
  4. reuse - the same spot and minute stamped on photos of different works

Run:  .venv-trial\Scripts\python.exe data\trial\geo_trial.py
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

import pandas as pd
from shapely.geometry import Point, shape
from shapely.prepared import prep

ROOT = Path(__file__).resolve().parents[2]
CACHE = ROOT / "data" / "trial" / "cache" / "ocr"
EVID = ROOT / "data" / "evidence"
BUILD = ROOT / "data" / "build"
OUT = ROOT / "data" / "trial" / "results"
GEO = ROOT / "apps" / "web" / "public" / "geo" / "districts.json"
KM_PER_DEG = 111.0
TODAY = date(2026, 9, 26)   # evidence was downloaded 25-26 Sep 2026
OUTSIDE_KM = 5.0          # the published outlines are simplified; closer than this is "at the border"

LATLON = [
    re.compile(r"lat(?:itude)?\s*[:：.]?\s*(\d{1,2}\.\d{3,})\s*°?\s*[nN]?[\s,;]*"
               r"lo?ng?(?:itude)?\s*[:：.]?\s*(\d{2,3}\.\d{3,})", re.I),
    re.compile(r"(\d{1,2}\.\d{4,})\s*°?\s*[nN]\b[\s,;/]*(\d{2,3}\.\d{4,})\s*°?\s*[eE]\b"),
    re.compile(r"(?<![\d.])(\d{1,2}\.\d{5,})\s*°?\s*[,;/]\s*(\d{2,3}\.\d{5,})(?![\d.])"),
]
DATES = [  # OCR often drops the space between date and time ("17-10-202508:43")
    (re.compile(r"(?<!\d)(\d{2})/(\d{2})/(20\d{2})"), "dmy"),
    (re.compile(r"(?<!\d)(\d{2})-(\d{2})-(20\d{2})"), "dmy"),
    (re.compile(r"(?<!\d)(20\d{2})-(\d{2})-(\d{2})(?!\d)"), "ymd"),
    (re.compile(r"(?<!\d)(\d{2})/(\d{2})/(\d{2})(?=[^\d/]|\d{1,2}:|$)"), "dmy2"),
]
PIN = re.compile(r"[A-Za-z][\s,]{0,2}([1-8]\d{5})(?![\d.])")   # "Gujarat 383462", not "2025 13..."


def in_india(lat: float, lon: float) -> bool:
    return 6.0 <= lat <= 37.5 and 68.0 <= lon <= 97.5


def read_stamp(text: str) -> dict:
    t = text.replace("，", ",").replace("：", ":")
    out: dict = {"lat": None, "lon": None, "date": None, "pin": None}
    for rx in LATLON:
        for m in rx.finditer(t):
            lat, lon = float(m.group(1)), float(m.group(2))
            if in_india(lat, lon):
                out["lat"], out["lon"] = lat, lon
                break
        if out["lat"] is not None:
            break
    # Every date in the text, remembering where it sits. A camera stamp is a date FOLLOWED BY A
    # TIME ("19/10/2025 09:44 AM", "Time: 09-11-2025 18:00"); a painted plaque's dates
    # ("Date of commencement: 12/08/2025") have no time, so the stamped date wins.
    found = []
    for rx, kind in DATES:
        for m in rx.finditer(t):
            a, b, c = (int(x) for x in m.groups())
            y = a if kind == "ymd" else (c + 2000 if kind == "dmy2" else c)
            # day-month first (Indian apps); month-day when that is impossible (AngleCam 07-19-2024)
            tries = [(y, b, c)] if kind == "ymd" else [(y, b, a), (y, a, b)]
            for yy, mm, dd in tries:
                try:
                    d = date(yy, mm, dd)
                except ValueError:
                    continue
                if date(2015, 1, 1) <= d <= date(2026, 12, 31):
                    timed = bool(re.match(r"\s*,?\s*\d{1,2}:\d{2}", t[m.end():m.end() + 8]))
                    found.append((not timed, m.start(), d))
                    break
    if found:
        _, pos, d = min(found)          # the first stamped date, else the first date at all
        out["date"], out["date_has_time"] = d, not min(found)[0]
        # GPS Map Camera prints the weekday just before the date: use it to catch a misread year
        wd = re.search(r"\b(mon|tues|wednes|thurs|fri|satur|sun)day\b[\s,.]*$", t[max(0, pos - 14):pos], re.I)
        if wd:
            want = ["mon", "tues", "wednes", "thurs", "fri", "satur", "sun"].index(wd.group(1).lower())
            if d.weekday() != want:
                fixed = []
                for yy in (d.year - 1, d.year + 1):
                    try:
                        if d.replace(year=yy).weekday() == want:
                            fixed.append(d.replace(year=yy))
                    except ValueError:  # 29 February
                        pass
                out["date"], out["date_fixed_by_weekday"] = (fixed[0], True) if fixed else (None, False)
    pins = [p for p in PIN.findall(t)]
    out["pin"] = pins[0] if pins else None
    return out


def main() -> None:
    manifest = [json.loads(line) for line in (EVID / "manifest.jsonl").read_text(encoding="utf-8").splitlines()]
    file_work = {Path(f["path"].replace("\\", "/")).stem: r["work_id"] for r in manifest for f in r["files"]}
    sample_of = {r["work_id"]: r["sample"] for r in manifest}
    w = pd.read_parquet(BUILD / "works.parquet").set_index("work_id")
    w["dlgd"] = pd.to_numeric(w.district_lgd, errors="coerce")

    feats = json.loads(GEO.read_text(encoding="utf-8"))["features"]
    polys = {int(f["properties"]["lgd"]): (f["properties"]["name"], shape(f["geometry"])) for f in feats}
    prepared = {k: prep(g) for k, (_, g) in polys.items()}
    # works carry Census-2011 district codes; the outlines carry LGD codes (district_crosswalk.py)
    cw = pd.read_parquet(BUILD / "district_crosswalk.parquet").dropna(subset=["lgd_code"])
    to_lgd = {int(c): int(lg) for c, lg in zip(cw.census_code, cw.lgd_code)}
    w["dlgd"] = w.dlgd.map(lambda c: to_lgd.get(int(c)) if pd.notna(c) else None)
    pin_map = pd.read_csv(Path.home() / "saakshya" / "data" / "raw" / "lgd" / "india-postal-lgd-mapping.csv",
                          dtype=str).drop_duplicates("pincode").set_index("pincode")
    pin_map["district_lgd"] = pin_map.district_lgd.map(lambda c: to_lgd.get(int(c)) if pd.notna(c) else None)

    rows = []
    for p in sorted(CACHE.glob("*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        text = " ".join(t for _, t, _ in d["lines"])
        has_app = bool(re.search(r"gps\s*map\s*camera|notecam|timestamp camera|gps camera", text, re.I))
        s = read_stamp(text)
        stem = Path(d["file"]).stem
        wid = file_work.get(stem)
        if wid is None or wid not in w.index:
            continue
        rows.append({"work_id": wid, "sample": sample_of.get(wid), "file": stem, "page": d["page"],
                     "kind": d["kind"], "gps_app_named": has_app, **s})
    r = pd.DataFrame(rows)
    stamped = r[r.lat.notna()].copy()
    res = {"items_read": int(len(r)), "photos": int((r.kind == "photo_band").sum()),
           "pdf_pages": int((r.kind == "pdf_page").sum()),
           "gps_app_named": int(r.gps_app_named.sum()),
           "with_coordinates": int(len(stamped)),
           "works_with_coordinates": int(stamped.work_id.nunique()),
           "works_in_pilot": int(r.work_id.nunique())}

    checks = []
    for x in stamped.itertuples():
        work = w.loc[x.work_id]
        pt = Point(x.lon, x.lat)
        own = int(work.dlgd) if pd.notna(work.dlgd) else None
        inside = bool(prepared[own].contains(pt)) if own in prepared else None
        km = None if inside or own not in polys else round(polys[own][1].distance(pt) * KM_PER_DEG, 1)
        found = next((polys[k][0] for k, g in prepared.items() if g.contains(pt)), None)
        rec = pd.to_datetime(work.recommended_date).date() if pd.notna(work.recommended_date) else None
        done = pd.to_datetime(work.completed_date).date() if pd.notna(work.completed_date) else None
        when = None
        if x.date and x.date > TODAY:
            when = "after_today"                     # camera clock wrong, or a misread digit
        elif x.date and rec:
            when = ("before_recommendation" if x.date < rec else
                    "long_after_completion" if done and (x.date - done).days > 365 else "in_window")
        pin_d = pin_map.district_lgd.get(x.pin) if x.pin else None
        checks.append({"work_id": x.work_id, "sample": x.sample, "file": x.file, "page": x.page,
                       "lat": x.lat, "lon": x.lon, "stamp_date": str(x.date) if x.date else None,
                       "district": work.district_name, "inside_own_district": inside,
                       "km_outside": km, "falls_in": found, "time": when,
                       "pin": x.pin, "pin_district_matches": (int(pin_d) == own) if pin_d and own else None,
                       "recommended": str(rec), "completed": str(done)})
    c = pd.DataFrame(checks)
    if not c.empty:
        far = c[(c.inside_own_district == False) & (c.km_outside > OUTSIDE_KM)]  # noqa: E712
        res["place"] = {"inside_own_district": int((c.inside_own_district == True).sum()),  # noqa: E712
                        "outside_within_5km_border": int(((c.inside_own_district == False) & (c.km_outside <= OUTSIDE_KM)).sum()),  # noqa: E712
                        "outside_more_than_5km": int(len(far)),
                        "examples_outside": far.head(15).to_dict("records")}
        res["time"] = c.time.value_counts(dropna=False).to_dict()
        res["time_examples"] = c[c.time.isin(["before_recommendation", "long_after_completion"])].head(15).to_dict("records")
        res["pin"] = c.pin_district_matches.value_counts(dropna=False).to_dict()
        spots = defaultdict(set)
        for x in c.itertuples():
            spots[(round(x.lat, 4), round(x.lon, 4), x.stamp_date)].add(x.work_id)
        res["same_spot_same_day_different_works"] = [{"spot": list(k[:2]), "date": k[2], "works": sorted(v)}
                                                     for k, v in spots.items() if len(v) > 1]
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "geo_trial.json").write_text(json.dumps(res, indent=2, default=str), encoding="utf-8")
    c.to_csv(OUT / "geo_checks.csv", index=False)
    print(json.dumps({k: v for k, v in res.items() if not k.endswith("examples") and k != "examples_outside"},
                     indent=2, default=str))


if __name__ == "__main__":
    main()
