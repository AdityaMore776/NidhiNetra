"""Read the GPS stamp printed into a photo by GPS-camera apps (T310, ports T303).

eSAKSHI strips the phone's own GPS data (0 of 321 pilot photos keep it), but GPS Map Camera,
NoteCam and similar apps print latitude, longitude, date, time and PIN into the picture. The
local OCR reads that band; this reader turns its text into facts. Ported from
data/trial/geo_trial.py, where coordinates read right 12/12 by eye, with its three date fixes:

  - day-month first (Indian apps), month-day when that is impossible (AngleCam 07-19-2024)
  - a date followed by a time is the stamp; a painted plaque's dates have no time
  - GPS Map Camera prints the weekday before the date: a misread year is corrected by it

T051: the trial accepted dates up to 31 Dec 2026 only (the year it ran). The window is now
relative: from 2015 to one year after `latest` (default today), so it keeps working.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

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
WEEKDAYS = ["mon", "tues", "wednes", "thurs", "fri", "satur", "sun"]
EARLIEST = date(2015, 1, 1)
APP = re.compile(r"gps\s*map\s*camera|notecam|timestamp camera|gps camera", re.I)


def in_india(lat: float, lon: float) -> bool:
    return 6.0 <= lat <= 37.5 and 68.0 <= lon <= 97.5


def read_stamp(text: str, latest: date | None = None) -> dict:
    """{"lat", "lon", "date", "date_has_time", "date_fixed_by_weekday", "pin", "app_named"}."""
    latest = (latest or date.today()) + timedelta(days=366)
    t = text.replace("，", ",").replace("：", ":")
    out: dict = {"lat": None, "lon": None, "date": None, "pin": None,
                 "app_named": bool(APP.search(t))}
    for rx in LATLON:
        for m in rx.finditer(t):
            lat, lon = float(m.group(1)), float(m.group(2))
            if in_india(lat, lon):
                out["lat"], out["lon"] = lat, lon
                break
        if out["lat"] is not None:
            break
    found = []
    for rx, kind in DATES:
        for m in rx.finditer(t):
            a, b, c = (int(x) for x in m.groups())
            y = a if kind == "ymd" else (c + 2000 if kind == "dmy2" else c)
            tries = [(y, b, c)] if kind == "ymd" else [(y, b, a), (y, a, b)]
            for yy, mm, dd in tries:
                try:
                    d = date(yy, mm, dd)
                except ValueError:
                    continue
                if EARLIEST <= d <= latest:
                    timed = bool(re.match(r"\s*,?\s*\d{1,2}:\d{2}", t[m.end():m.end() + 8]))
                    found.append((not timed, m.start(), d))
                    break
    if found:
        untimed, pos, d = min(found)          # the first stamped date, else the first date
        out["date"], out["date_has_time"] = d, not untimed
        wd = re.search(r"\b(mon|tues|wednes|thurs|fri|satur|sun)day\b[\s,.]*$",
                       t[max(0, pos - 14):pos], re.I)
        if wd:
            want = WEEKDAYS.index(wd.group(1).lower())
            if d.weekday() != want:
                fixed = []
                for yy in (d.year - 1, d.year + 1):
                    try:
                        if d.replace(year=yy).weekday() == want:
                            fixed.append(d.replace(year=yy))
                    except ValueError:  # 29 February
                        pass
                out["date"], out["date_fixed_by_weekday"] = (fixed[0], True) if fixed else \
                    (None, False)
    pins = PIN.findall(t)
    out["pin"] = pins[0] if pins else None
    return out
