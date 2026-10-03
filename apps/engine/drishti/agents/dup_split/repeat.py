"""Is this work already sanctioned at this site? The Duplicate check's evidence (T100, 3 Oct 2026).

The owner: "compare works in the given area to works that have already been sanctioned, and
understand if this is a repeated work ... account for continuations ... simple and very accurate".

Measured (data/trial/simple_certain_trial.py): from the record's words alone a repeat is right
about 2 times in 3 at best (the strictest text rule 13 of 16 on the team's 289 pairs read by eye,
finding 12% of the real repeats; 8 same, 6 grey, 11 different on the dashboard), because the
district is the finest place a record names: one village has many roads, lights and borewells.
So what is ASKED comes from the cost estimate form (work["cost_form"]), and words only give notes.

  at_site     a sanctioned work of the same kind of asset (the form's family of work types) whose
              own form puts a map pin within PIN_METRES of this work's pin; a linear work (road,
              drain, wall, pipeline ...) by both ends. Certain by construction: two pins, one place.
  declared    the work this one continues, extends, upgrades or rebuilds, named by the agency on
              the form (work.nature, work.earlier_work_id), and its record in the district
  look_alike  sanctioned works of the same work type whose description names the same place in
              the same words (the strictest text rule: 90%+ alike, every place word shared, no
              plot / ward number, side, floor, gender or community apart, no continuation word,
              not several sites, not a series of 3+ copies). A note: the form asks the agency.

"Sanctioned" = recorded as sanctioned or completed (or carrying a sanction or completion date);
"earlier" = first recorded (recommended, else sanctioned, else completed) before this work, the
work id breaking a tie, so of two works at one site only the later one is asked about.
"""

from __future__ import annotations

import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date

from drishti import records
from drishti.agents.dup_split.match import (
    SERIES_COPIES,
    STAGED,
    _count_copies,
    _localise,
    genders,
    place_agreement,
    place_words,
    segment,
    sides,
    site_numbers,
    text_sim,
)
from drishti.agents.statistical.scope import many_sites, undescribed
from drishti.cost_form import catalog

PIN_METRES = 50.0                 # two pins this close are one site
TEXT_MIN = 0.90                   # look-alike wording (the trial's strictest rule)
PLACE_MIN = 100.0                 # every place word shared
DECLARED_NATURES = ("continuation", "extension", "upgrade", "reconstruction")
SANCTIONED = ("SANCTIONED", "COMPLETED")
# A ground floor and a first floor, an SC colony and a BC colony are two works (read by eye on
# the team's labelled pairs and the dashboard, 3 Oct 2026).
FLOOR = re.compile(r"\b(ground|first|1st|second|2nd|third|3rd|top)\s+floor\b", re.I)
COMMUNITY = re.compile(r"\b(sc|st|bc|obc|ebc|mbc|gen|general|minority)\b(?=[\s.,-]*"
                       r"(colony|basti|tola|para|mohalla|wada|wadi|sahi|nagar|area|hostel))",
                       re.I)


def metres(a: tuple[float, float], b: tuple[float, float]) -> float:
    """Great-circle distance in metres between two (lat, lon) points."""
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * 6_371_000 * math.asin(min(1.0, math.sqrt(h)))


def _num(v) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return None
    return float(v)


def _part(form, key: str) -> dict:
    """One part of the form as a dict ({} for anything else: a damaged form never breaks it)."""
    v = form.get(key) if isinstance(form, dict) else None
    return v if isinstance(v, dict) else {}


def _work_type(rec: Rec) -> str | None:
    t = _part(rec.form, "work").get("work_type")
    return t if isinstance(t, str) and t else rec.work_type


def pins(form) -> list[tuple[tuple[float, float], tuple[float, float] | None]]:
    """Each site's map pin and, for a linear work, its other end; sites without a pin left out."""
    out = []
    sites = form.get("sites") if isinstance(form, dict) else None
    for s in sites if isinstance(sites, list) else []:
        loc = s.get("location") if isinstance(s, dict) else None
        if not isinstance(loc, dict):
            continue
        lat, lon = _num(loc.get("lat")), _num(loc.get("lon"))
        if lat is None or lon is None:
            continue
        elat, elon = _num(loc.get("end_lat")), _num(loc.get("end_lon"))
        out.append(((lat, lon), (elat, elon) if elat is not None and elon is not None else None))
    return out


def same_site(a, b, linear: bool) -> float | None:
    """Metres between two sites when they are one site, else None. A linear work is one site
    only when both its ends meet the other's (in either direction): sharing one end is a road
    that starts where another ends, not the same road."""
    (sa, ea), (sb, eb) = a, b
    if not linear:
        d = metres(sa, sb)
        return d if d <= PIN_METRES else None
    if ea is None or eb is None:
        return None
    d = min(max(metres(sa, sb), metres(ea, eb)), max(metres(sa, eb), metres(ea, sb)))
    return d if d <= PIN_METRES else None


def _apart(a: str, b: str) -> bool:
    """Something in the two descriptions that makes them two works."""
    def floor(t):
        return {m.group(1).lower().replace("1st", "first").replace("2nd", "second")
                .replace("3rd", "third") for m in FLOOR.finditer(t)}

    def community(t):
        return {m.group(1).lower() for m in COMMUNITY.finditer(t)}

    # any difference, a number or a side named in one description only included: the trial's
    # "nothing apart" (data/trial/simple_certain_trial.py)
    return any(x != y for x, y in (
        (site_numbers(a), site_numbers(b)), (segment(a), segment(b)), (sides(a), sides(b)),
        (genders(a), genders(b)), (floor(a), floor(b)), (community(a), community(b))))


@dataclass
class Rec:
    work_id: str
    district: str
    work_type: str
    mp: str
    description: str
    status: str | None
    rec: date | None
    sanction: date | None
    done: date | None
    amount: float
    form: dict | None = None
    raw_place: str = ""
    place: str = ""            # raw_place minus its district's boilerplate (match._localise)
    copies: int = 1            # identical wording filed by one MP in the district
    sites: list = field(default_factory=list)

    @property
    def first(self) -> date | None:
        return self.rec or self.sanction or self.done

    @property
    def sanctioned(self) -> bool:
        return (self.status or "").upper() in SANCTIONED or bool(self.sanction or self.done)

    @property
    def family(self) -> str | None:
        found = catalog.family_of(_work_type(self))
        return found[0] if found else None

    @property
    def linear(self) -> bool:
        return catalog.is_linear(_work_type(self))

    def before(self, other: Rec) -> bool:
        """Recorded before the other work (the work id breaks a tie)."""
        if self.first is None or other.first is None:
            return False
        return (self.first, self.work_id) < (other.first, other.work_id)

    @classmethod
    def of(cls, w: dict) -> Rec | None:
        w = records.work(w)                    # every column in its expected type, or absent
        desc = w.get("description")
        form = w.get("cost_form") if isinstance(w.get("cost_form"), dict) else None
        r = cls(work_id=str(w.get("work_id") or ""), district=str(w.get("district_lgd") or "NA"),
                work_type=str(w.get("work_type_code") or "NA"), mp=str(w.get("mp_name") or "NA"),
                description=str(desc or ""), status=w.get("status"),
                rec=w.get("recommended_date"), sanction=w.get("sanction_date"),
                done=w.get("completed_date"), amount=float(w.get("amount") or 0),
                form=form, raw_place="" if undescribed(desc) else place_words(desc),
                sites=pins(form))
        if not r.work_id or r.first is None or (undescribed(desc) and not r.sites):
            return None
        return r


def looks_alike(a: Rec, b: Rec) -> float | None:
    """Text likeness when the two descriptions name the same asset at the same place in the same
    words (module note), else None."""
    if (a.work_type != b.work_type or not a.place or not b.place
            or a.copies >= SERIES_COPIES or b.copies >= SERIES_COPIES):
        return None
    da, db = a.description, b.description
    if (STAGED.search(da) or STAGED.search(db) or many_sites(da) or many_sites(db)
            or _apart(da, db) or place_agreement(a.place, b.place) < PLACE_MIN):
        return None
    t = text_sim(da, db)
    return t if t >= TEXT_MIN else None


def declared(form: dict | None) -> tuple[str | None, str | None]:
    """(nature, earlier work id) the agency declared on the form, when it names one."""
    work = _part(form, "work")
    nature, wid = work.get("nature"), work.get("earlier_work_id")
    if nature in DECLARED_NATURES and isinstance(wid, str) and wid.strip():
        return nature, wid.strip()
    return None, None


def answers(form: dict | None) -> dict[str, dict]:
    """The agency's answers about earlier sanctioned works (form["earlier_works"]):
    {work id: {earlier_work, answer, difference}}."""
    out = {}
    raw = form.get("earlier_works") if isinstance(form, dict) else None
    for a in raw if isinstance(raw, list) else []:
        if isinstance(a, dict) and isinstance(a.get("earlier_work"), str):
            out[a["earlier_work"].strip()] = a
    return out


@dataclass
class RepeatIndex:
    """Every work by district, compared on demand."""

    by_district: dict[str, list[Rec]] = field(default_factory=dict)
    _ids: dict[str, Rec] = field(default_factory=dict)

    @classmethod
    def build(cls, works) -> RepeatIndex:
        idx = cls()
        for w in works:
            r = Rec.of(w)
            if r is not None:
                idx.by_district.setdefault(r.district, []).append(r)
                idx._ids[r.work_id] = r
        for recs in idx.by_district.values():
            _localise(recs)
            _count_copies(recs)
        return idx

    def covers(self, district) -> bool:
        return str(district or "NA") in self.by_district

    def get(self, work_id: str | None) -> Rec | None:
        return self._ids.get(work_id or "")

    def check(self, work: dict) -> dict | None:
        """What is on record for this work (module note), or None if it cannot be compared."""
        me = Rec.of(work)
        if me is None:
            return None
        known = self._ids.get(me.work_id)
        recs = self.by_district.get(me.district, [])
        others = [x for x in recs if x.work_id != me.work_id]
        if known is None or known.description != me.description:
            _localise(others + [me])          # a work the index does not hold: on the spot
            _count_copies(others + [me])
        else:
            me.place, me.copies = known.place, known.copies
        earlier = [x for x in others if x.sanctioned and x.before(me)]
        fam = me.family

        at_site = []
        for x in earlier:
            if not x.sites or not me.sites or x.family is None or x.family != fam:
                continue
            best = min((d for a in me.sites for b in x.sites
                        if (d := same_site(a, b, me.linear)) is not None), default=None)
            if best is not None:
                at_site.append((x, best))

        nature, wid = declared(me.form)
        link = None
        if wid:
            x = self._ids.get(wid)
            link = {"nature": nature, "work_id": wid, "rec": x if x and x.district == me.district
                    else None}

        alike = []
        if me.place:
            postings: dict[str, list[Rec]] = defaultdict(list)
            for x in earlier:
                for p in set(x.place.split()):
                    postings[p].append(x)
            seen = set()
            for p in set(me.place.split()):
                for x in postings.get(p, []):
                    if x.work_id in seen:
                        continue
                    seen.add(x.work_id)
                    if (t := looks_alike(me, x)) is not None:
                        alike.append((x, t))
        if known is None or known.description != me.description:
            _localise(others)                 # leave the index as it was
            _count_copies(others)
        alike.sort(key=lambda p: (-p[1], p[0].work_id))
        at_site.sort(key=lambda p: (p[1], p[0].work_id))
        return {"me": me, "at_site": at_site, "declared": link, "look_alike": alike[:5],
                "answers": answers(me.form), "compared": len(others),
                "sanctioned_earlier": len(earlier), "place_named": bool(me.place)}

    def candidates(self, work: dict) -> list[Rec]:
        """The sanctioned works the form must ask the agency about: those at the same site by
        map pin, then the look-alikes by words."""
        found = self.check(work)
        if not found:
            return []
        out = [x for x, _ in found["at_site"]]
        out += [x for x, _ in found["look_alike"] if x not in out]
        return out
