"""YouTube Creative Commons timelapses, found and checked with yt-dlp (no API key) (T151, T152).

The owner allowed CC BY YouTube downloads on 7 Oct 2026 (plan T150 §0); NC and ND stay refused. Each
candidate's licence is read from its own watch page (yt-dlp's `license` field), never assumed from
the
search filter. Titles that point to AI-made, miniature or game footage are dropped: they are not
real
construction.
"""

from __future__ import annotations

import re
import time
import urllib.parse

POLITE_S = 1.5
CC_FILTER = "EgIwAQ%3D%3D"      # YouTube's "Creative Commons" search filter
CC_BY = "Creative Commons Attribution license (reuse allowed)"

# titles that are not real construction footage
NOT_REAL = re.compile(r"\b(ai|a\.i\.|miniature|mini|tiny|toy|diorama|lego|minecraft|game|"
                      r"animation|animated|3d|render|cgi|simulation|model|shorts?|asmr|primitive)\b",
                      re.I)

QUERIES = (
    "construction timelapse", "building construction time lapse", "house construction timelapse",
    "construction site webcam timelapse", "road construction timelapse",
    "concrete road construction time lapse", "drain construction timelapse",
    "school building construction timelapse", "community hall construction",
    "india house construction time lapse", "village road construction india",
    "panchayat bhawan construction", "anganwadi construction", "cc road construction",
    "मकान निर्माण टाइमलैप्स", "सड़क निर्माण", "building construction time lapse fixed camera",
    "bridge construction timelapse", "brick house construction timelapse",
    "roof slab casting timelapse",
)

_last = [0.0]


def _wait() -> None:
    gap = POLITE_S - (time.monotonic() - _last[0])
    if gap > 0:
        time.sleep(gap)
    _last[0] = time.monotonic()


def search_url(query: str) -> str:
    return ("https://www.youtube.com/results?search_query=" + urllib.parse.quote_plus(query)
            + "&sp=" + CC_FILTER)


def search(query: str, n: int = 40) -> list[dict]:
    """Flat search results under the Creative Commons filter: id, title, duration, channel."""
    import yt_dlp
    _wait()
    opts = {"quiet": True, "extract_flat": True, "playlistend": n, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as y:
        info = y.extract_info(search_url(query), download=False)
    out = []
    for e in info.get("entries") or []:
        if e and e.get("id"):
            out.append({"id": e["id"], "title": e.get("title") or "",
                        "duration": e.get("duration"), "channel": e.get("channel") or "",
                        "channel_id": e.get("channel_id") or "", "query": query})
    return out


def plausible(c: dict, min_s: int = 20, max_s: int = 1800) -> bool:
    d = c.get("duration")
    if d is None or not (min_s <= d <= max_s):
        return False
    return not NOT_REAL.search(c.get("title", ""))


def meta(video_id: str) -> dict:
    """The watch page's own facts: licence, channel, size, upload date."""
    import yt_dlp
    _wait()
    with yt_dlp.YoutubeDL({"quiet": True, "skip_download": True}) as y:
        i = y.extract_info(f"https://www.youtube.com/watch?v={video_id}", download=False)
    return {"license": i.get("license") or "", "channel": i.get("channel") or "",
            "channel_id": i.get("channel_id") or "", "uploader": i.get("uploader") or "",
            "duration": i.get("duration"), "upload_date": i.get("upload_date") or "",
            "width": i.get("width"), "height": i.get("height"),
            "title": i.get("title") or "", "description": (i.get("description") or "")[:500]}


def work_type_guess(title: str) -> str:
    t = title.lower()
    if re.search(r"\broad|highway|सड़क|street", t):
        return "road"
    if re.search(r"\bdrain|nala|sewer", t):
        return "drain"
    if re.search(r"\bbridge|flyover|culvert", t):
        return "bridge"
    return "building"


def country_guess(c: dict) -> str:
    t = (c.get("title", "") + " " + c.get("description", "")).lower()
    if re.search(r"india|bharat|[ऀ-ॿ]|erode|chennai|kerala|bihar|delhi|mumbai|pune|"
                 r"tamil|telangana|hyderabad|bengal|punjab|rajasthan|gujarat|2bhk|lakh", t):
        return "IN"
    return ""


def manifest_row(c: dict, m: dict) -> dict:
    """A manifest.Video row; material and camera are first guesses for a person to check."""
    return {"id": f"yt-{c['id']}", "url": f"https://www.youtube.com/watch?v={c['id']}",
            "source": "youtube", "licence": "cc-by", "attribution": m.get("channel", ""),
            "channel": m.get("channel_id") or c.get("channel_id", ""),
            "work_type": work_type_guess(m.get("title", c.get("title", ""))),
            "material": "mixed", "country": country_guess({**c, **m}), "camera": "mixed",
            "notes": (m.get("title") or c.get("title", ""))[:120],
            "extra": {"duration": m.get("duration"), "upload_date": m.get("upload_date"),
                      "query": c.get("query", ""), "checked_by": "auto (needs a person)"}}
