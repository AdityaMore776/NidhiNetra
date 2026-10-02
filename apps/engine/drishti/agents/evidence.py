"""A work's evidence facts, read one way by every engine and index (2 Oct 2026, foolproofing).

Evidence arrives as stored JSON (data/build_evidence.py, data/build_site_observations.py) and,
later, from uploads (the field app, a citizen's photo). Each engine used to read it with its own
`.get()` chains, so a malformed part broke things far from where it sat: one evidence row whose
file was not an object crashed the photo and vendor indexes, and with them the whole batch
(found by fuzzing, tests/evaluation/test_random_environment.py).

Here every part is checked once. Anything malformed is dropped, never guessed:
  file          not an object -> dropped; id -> text (or "file-N"); ext -> lower case, no dot
  fingerprint   not 64 hex digits -> ignored (no fingerprint is compared)
  pages, lines  not a positive number -> 0; readable -> only a real True
  stamp         not an object -> dropped; lat/lon kept only as a finite pair; date text or date
  certificate   not an object -> dropped; amounts -> numbers or None ("1,00,000" reads); a
                payment kept only as (date, amount) with a number; location -> text
  site reading  scores -> numbers within 0..1; plaque -> {scheme: True/False, dated items}
  judgement     a claim in words, a verdict among shown / not_shown / cant_tell, a reason text
"""

from __future__ import annotations

import math
import re
from datetime import date

PHOTO_EXT = {"jpg", "jpeg", "png", "tif", "tiff", "webp", "bmp", "heic"}
HEX64 = re.compile(r"[0-9a-f]{64}")
VERDICTS = ("shown", "not_shown", "cant_tell")
PLAQUE_LABELS = ("start", "completion", "sanction")


def num(x) -> float | None:
    """A finite number, or None. Text with Indian digit grouping ("1,00,000") reads too."""
    if isinstance(x, bool) or x is None:
        return None
    if isinstance(x, (int, float)):
        v = float(x)
    elif isinstance(x, str):
        try:
            v = float(x.replace(",", "").strip())
        except ValueError:
            return None
    else:
        return None
    return v if math.isfinite(v) else None


def _text(x) -> str:
    return x if isinstance(x, str) else ""


def _list(x) -> list:
    return list(x) if isinstance(x, (list, tuple)) else []


def _when(x):
    """A date as stored (ISO text or a date); anything else is no date."""
    return x if isinstance(x, (str, date)) else None


def _count(x) -> int:
    v = num(x)
    return int(v) if v is not None and v > 0 else 0


def _stamp(s) -> dict | None:
    if not isinstance(s, dict):
        return None
    out = dict(s)
    lat, lon = num(s.get("lat")), num(s.get("lon"))
    out["lat"], out["lon"] = (lat, lon) if lat is not None and lon is not None else (None, None)
    out["date"] = _when(s.get("date"))
    return out


def _payment(p) -> tuple | None:
    if not isinstance(p, (list, tuple)) or len(p) != 2:
        return None
    amount = num(p[1])
    return None if amount is None else (_when(p[0]), amount)


def _certificate(c) -> dict | None:
    if not isinstance(c, dict):
        return None
    out = dict(c)
    out["sanctioned_amount"] = num(c.get("sanctioned_amount"))
    out["sanction_date"] = _when(c.get("sanction_date"))
    out["payments"] = [q for p in _list(c.get("payments")) if (q := _payment(p))]
    out["location"] = _text(c.get("location"))
    code = c.get("vendor_code")
    out["vendor_code"] = code if isinstance(code, str) and code else None
    return out


def _score(x) -> float:
    v = num(x)
    return 0.0 if v is None else min(1.0, max(0.0, v))


def _site(s) -> dict | None:
    if not isinstance(s, dict):
        return None
    out = dict(s)
    groups = s.get("groups")
    out["groups"] = ({g: {k: _score(v.get(k)) for k in ("built", "not_built", "not_site")}
                      for g, v in groups.items() if isinstance(v, dict)}
                     if isinstance(groups, dict) else {})
    p = s.get("plaque")
    if isinstance(p, dict):
        out["plaque"] = {"scheme": p.get("scheme") is True, "dates": [
            {"label": d.get("label") if d.get("label") in PLAQUE_LABELS else None,
             "date": _when(d.get("date"))}
            for d in _list(p.get("dates")) if isinstance(d, dict)]}
    else:
        out.pop("plaque", None)
    return out


def _file(f, i: int) -> dict | None:
    if not isinstance(f, dict):
        return None
    out = dict(f)
    fid = f.get("id")
    out["id"] = str(fid) if fid not in (None, "") and not isinstance(fid, (dict, list)) \
        else f"file-{i + 1}"
    ext = f.get("ext")
    out["ext"] = ext.strip().lower().lstrip(".") if isinstance(ext, str) else ""
    sha = f.get("sha256")
    out["sha256"] = sha if isinstance(sha, str) and sha else None
    ph = f.get("phash")
    out["phash"] = ph.lower() if isinstance(ph, str) and HEX64.fullmatch(ph.lower()) else None
    out["pages"] = _count(f.get("pages"))
    out["text_lines"] = _count(f.get("text_lines"))
    out["readable"] = f.get("readable") is True
    out["stamps"] = [t for s in _list(f.get("stamps")) if (t := _stamp(s))]
    out["certificates"] = [t for c in _list(f.get("certificates")) if (t := _certificate(c))]
    out["site"] = _site(f.get("site"))
    return out


def files(work: dict) -> list[dict]:
    """The work's attached files, each checked; [] when there is no usable evidence."""
    ev = work.get("evidence") if isinstance(work, dict) else None
    if not isinstance(ev, dict):
        return []
    return [g for i, f in enumerate(_list(ev.get("files"))) if (g := _file(f, i))]


def photos(work: dict) -> list[dict]:
    return [f for f in files(work) if f["ext"] in PHOTO_EXT]


def papers(work: dict) -> list[dict]:
    return [f for f in files(work) if f["ext"] == "pdf"]


def judgements(work: dict) -> list[dict]:
    """A vision-language reader's verdicts on the work's claims (Site Progress)."""
    ev = work.get("evidence") if isinstance(work, dict) else None
    if not isinstance(ev, dict):
        return []
    out = []
    for j in _list(ev.get("site_judgements")):
        if not isinstance(j, dict) or not isinstance(j.get("claim"), str):
            continue
        out.append({"claim": j["claim"],
                    "verdict": j.get("verdict") if j.get("verdict") in VERDICTS else "cant_tell",
                    "reason": _text(j.get("reason")), "reader": _text(j.get("reader"))})
    return out
