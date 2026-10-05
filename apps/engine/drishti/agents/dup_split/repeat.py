"""The Duplicate check's evidence (T100, 3 Oct 2026): is this work already sanctioned here, or
one job cut to stay under a limit?

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
  near        (T136) a sanctioned building or place of the same family whose pin is just past the
              one-site line (PIN_METRES to NEAR_METRES): a note naming it, never counted; the
              first site video (Site Progress: the asset already standing) settles it
  look_alike  sanctioned works of the same work type whose description names the same place in
              the same words (the strictest text rule: 90%+ alike, every place word shared, no
              plot / ward number, side, floor, gender or community apart, no continuation word,
              not several sites, not a series of 3+ copies). A note: the form asks the agency.
  split       one job cut into pieces to stay under a sanction limit, in its strictest form:
              2-5 alike works at one place (or numbered parts of one job: reach-1, Bit2, Sy.No
              488-A), one MP, one work type, recommended within 30 days (match.groups_in_block),
              EVERY piece between 96% and 100% of the Rs 5 or 10 lakh limit and the total above
              it. On the dashboard's 40,935 works: 14 groups, read 12 one job cut into pieces,
              2 grey, 0 not (data/trial/simple_certain_trial.py); v2's looser splits (pieces
              anywhere at one site) read right 18 of 32.

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
    SPLIT_GAP_DAYS,
    STAGED,
    _count_copies,
    _key,
    _localise,
    genders,
    groups_in_block,
    place_agreement,
    place_words,
    segment,
    sides,
    site_numbers,
    split_limits,
    text_sim,
)
from drishti.agents.statistical.scope import many_sites, undescribed
from drishti.cost_form import catalog

PIN_METRES = 50.0                 # two pins this close are one site
NEAR_METRES = 150.0               # a same-kind building this close, just past the line: a note
OVERLAP_METRES = 25.0             # a point of a road this close to another road's line lies on it
OVERLAP_SHARE = 0.80              # this share of a road on another's line: the same ground (T135)
MIN_ROAD_METRES = 50.0            # shorter alignments are compared by their pins only
SIZE_ALIKE = 0.25                 # two forms' sizes this close: the same asset again
INDIA = (6.0, 37.6, 68.0, 97.5)   # lat min, lat max, lon min, lon max: a pin outside is a typo
TEXT_MIN = 0.90                   # look-alike wording (the trial's strictest rule)
PLACE_MIN = 100.0                 # every place word shared
SPLIT_SHARE = 0.96                # every piece at least this share of the limit it sits under
SPLIT_MAX = 5                     # 6+ alike pieces read as a series of purchases, not one job
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


def in_india(lat: float, lon: float) -> bool:
    return INDIA[0] <= lat <= INDIA[1] and INDIA[2] <= lon <= INDIA[3]


def pins(form) -> list[tuple[tuple[float, float], tuple[float, float] | None]]:
    """Each site's map pin and, for a linear work, its other end; sites without a pin, or with a
    pin outside India (0, 0; latitude and longitude swapped), left out (T135)."""
    out = []
    sites = form.get("sites") if isinstance(form, dict) else None
    for s in sites if isinstance(sites, list) else []:
        loc = s.get("location") if isinstance(s, dict) else None
        if not isinstance(loc, dict):
            continue
        lat, lon = _num(loc.get("lat")), _num(loc.get("lon"))
        if lat is None or lon is None or not in_india(lat, lon):
            continue
        elat, elon = _num(loc.get("end_lat")), _num(loc.get("end_lon"))
        end = (elat, elon) if elat is not None and elon is not None else None
        out.append(((lat, lon), end if end and in_india(*end) else None))
    return out


def pin_problems(form, linear: bool) -> list[str]:
    """What is wrong with the form's map pins, in words (the check says it could not use them)."""
    out = []
    sites = form.get("sites") if isinstance(form, dict) else None
    for i, s in enumerate(sites if isinstance(sites, list) else []):
        loc = s.get("location") if isinstance(s, dict) else None
        if not isinstance(loc, dict):
            continue
        where = f"site {i + 1}'s" if len(sites) > 1 else "the"
        lat, lon = _num(loc.get("lat")), _num(loc.get("lon"))
        if lat is not None and lon is not None and not in_india(lat, lon):
            out.append(f"{where.capitalize()} map pin ({lat:g}, {lon:g}) is not in India "
                       "(0, 0, or latitude and longitude swapped), so it was not compared: "
                       "ask for the right pin.")
            continue
        elat, elon = _num(loc.get("end_lat")), _num(loc.get("end_lon"))
        if linear and lat is not None and (elat is None or elon is None):
            out.append(f"The form gives one end of the {'site' if where != 'the' else 'work'}'s "
                       "alignment only, so it could not be compared end to end: ask for its "
                       "other end.")
        elif linear and elat is not None and elon is not None and not in_india(elat, elon):
            out.append(f"{where.capitalize()} far-end pin ({elat:g}, {elon:g}) is not in India, "
                       "so the alignment could not be compared: ask for the right pin.")
    return out


def _xy(p: tuple[float, float], origin: tuple[float, float]) -> tuple[float, float]:
    """Metres east and north of `origin` (flat near a site)."""
    return ((p[1] - origin[1]) * 111_320 * math.cos(math.radians(origin[0])),
            (p[0] - origin[0]) * 110_574)


def _off_line(p, a, b) -> float:
    """Metres from point p to the segment ab (all in metres)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy)
                                                / (dx * dx + dy * dy)))
    return math.hypot(p[0] - a[0] - t * dx, p[1] - a[1] - t * dy)


def on_line(a, b) -> float | None:
    """The share of linear site a's length lying within OVERLAP_METRES of site b's line (each a
    (start, end) pair), or None when either lacks an end or a is too short to say."""
    (sa, ea), (sb, eb) = a, b
    if ea is None or eb is None or metres(sa, ea) < MIN_ROAD_METRES:
        return None
    # far apart: no point of one is near the other (cheap, so a district of thousands of roads
    # stays fast: each road is sampled only against the few near it)
    pad = (OVERLAP_METRES + 10) / 110_574
    if (max(sa[0], ea[0]) + pad < min(sb[0], eb[0]) or max(sb[0], eb[0]) + pad < min(sa[0], ea[0])
            or max(sa[1], ea[1]) + 2 * pad < min(sb[1], eb[1])
            or max(sb[1], eb[1]) + 2 * pad < min(sa[1], ea[1])):
        return 0.0
    n = max(2, min(200, int(metres(sa, ea) // 10) + 1))
    A, B = _xy(sb, sa), _xy(eb, sa)
    near = sum(1 for k in range(n)
               if _off_line(_xy((sa[0] + (ea[0] - sa[0]) * k / (n - 1),
                                 sa[1] + (ea[1] - sa[1]) * k / (n - 1)), sa), A, B)
               <= OVERLAP_METRES)
    return near / n


def size_alike(a: dict | None, b: dict | None) -> bool:
    """The two forms give the first site the same size (every size both give within
    SIZE_ALIKE): the same asset filed again."""
    def size(f):
        sites = f.get("sites") if isinstance(f, dict) else None
        s0 = sites[0] if isinstance(sites, list) and sites and isinstance(sites[0], dict) else {}
        sz = s0.get("size") if isinstance(s0.get("size"), dict) else {}
        return {k: v for k, v in ((k, _num(v)) for k, v in sz.items()) if v and v > 0}
    x, y = size(a), size(b)
    shared = set(x) & set(y)
    return bool(shared) and all(abs(x[k] - y[k]) <= SIZE_ALIKE * max(x[k], y[k])
                                for k in shared)


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
    nums: str = ""             # plot / ward / survey numbers (match.site_numbers)
    segment: str | None = None  # the numbered piece it names (match.segment)

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
        """A linear family, or an OTHER work whose form gives its two ends (a gravel road)."""
        wt = _work_type(self)
        return catalog.is_linear(wt) or (wt == "OTHER" and any(e for _s, e in self.sites))

    @property
    def lane(self) -> str | None:
        """The family for splits by map pins: a road, a paved path or an OTHER alignment laid end
        to end are one lane (T136: one piece filed as a paver-block road escaped)."""
        fam = self.family
        return "lane" if fam in ("road", "path") or (fam == "other" and self.linear) else fam

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
                sites=pins(form), nums=site_numbers(desc), segment=segment(desc))
        if not r.work_id or r.first is None or (undescribed(desc) and not r.sites):
            return None
        return r


def same_ground(me: Rec, x: Rec) -> bool:
    """A work declared to continue, extend or upgrade x that covers x's own ground instead: a
    road lying mostly on x's line, or a building at x's pin with x's size (T135: declaring a
    re-filed work a "continuation" kept it from being asked about)."""
    if not me.sites or not x.sites or x.family != me.family:
        return False
    if me.linear:            # either lies mostly on the other: the old road is built again
        return any((v := on_line(p, q)) is not None and v >= OVERLAP_SHARE
                   for a in me.sites for b in x.sites for p, q in ((a, b), (b, a)))
    near = any(metres(a[0], b[0]) <= PIN_METRES for a in me.sites for b in x.sites)
    return near and size_alike(me.form, x.form)


def _together_key(r: Rec) -> tuple:
    return (r.district, r.mp, _key(r.description), r.rec)


def _near_limit(amount: float) -> bool:
    return any(SPLIT_SHARE * lim <= amount <= lim for lim in split_limits())


def _touch(a: Rec, b: Rec) -> bool:
    """Two works' sites meet: pins within PIN_METRES, or for linear works an end of one within
    PIN_METRES of an end of the other (pieces laid end to end) or one lying on the other."""
    for sa, ea in a.sites:
        for sb, eb in b.sites:
            ends_a, ends_b = [p for p in (sa, ea) if p], [p for p in (sb, eb) if p]
            if any(metres(p, q) <= PIN_METRES for p in ends_a for q in ends_b):
                return True
            if a.linear and (on_line((sa, ea), (sb, eb)) or 0) > 0:
                return True
    return False


def pin_split_groups(recs: list[Rec]) -> list[dict]:
    """The strictest split found by the forms' map pins (T136: the same split with one piece
    called another kind of road, or described in other words, escaped the wording rule): 2 to
    SPLIT_MAX works of one family (a lane: Rec.lane) whose sites meet end to end or at one pin,
    recommended within
    SPLIT_GAP_DAYS, EVERY piece 96-100% of one limit and the total above it."""
    cand = sorted((r for r in recs if r.sites and r.rec is not None and r.lane
                   and _near_limit(r.amount)), key=lambda r: r.rec)
    parent = list(range(len(cand)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, a in enumerate(cand):
        for j in range(i + 1, len(cand)):
            b = cand[j]
            if (b.rec - a.rec).days > SPLIT_GAP_DAYS:
                break
            if a.mp == b.mp and a.lane == b.lane and _touch(a, b):
                parent[find(i)] = find(j)
    chains: dict[int, list[Rec]] = defaultdict(list)
    for i, r in enumerate(cand):
        chains[find(i)].append(r)
    out = []
    for sub in chains.values():
        amounts = [r.amount for r in sub]
        lim = next((x for x in split_limits() if all(SPLIT_SHARE * x <= a <= x for a in amounts)
                    and sum(amounts) > x), None)
        if not 2 <= len(sub) <= SPLIT_MAX or lim is None:
            continue
        members = sorted(r.work_id for r in sub)
        out.append({"group_id": "P-" + members[0], "kind": "pins_split", "size": len(sub),
                    "total": float(sum(amounts)), "limit": lim, "members": members,
                    "amounts": amounts, "days": (sub[-1].rec - sub[0].rec).days,
                    "segments": [], "shared_place": ""})
    return out


def split_groups(recs: list[Rec]) -> dict[str, dict]:
    """{work id: group} for the strictest splits among these works of one district (module
    note): only works priced within 4% under a limit can be pieces, so the blocks stay small."""
    blocks: dict[tuple, list[Rec]] = defaultdict(list)
    for r in recs:
        if r.rec is not None and _near_limit(r.amount):
            blocks[(r.mp, r.work_type)].append(r)
    out: dict[str, dict] = {}
    for g in pin_split_groups(recs):
        for wid in g["members"]:
            out[wid] = g                     # the wording's group, if any, is set below
    for block in blocks.values():
        if len(block) < 2:
            continue
        for g in groups_in_block(block):
            lim = g.get("limit")
            if (g["kind"] in ("same_site_split", "stretches") and lim and g["size"] <= SPLIT_MAX
                    and all(SPLIT_SHARE * lim <= a <= lim for a in g["amounts"])):
                for wid in g["members"]:
                    out[wid] = g
    return out


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
    # works filed together: the same wording, MP and recommendation day in one district. Not a
    # finding (a purchase filed as several works is not a repeat); the review queue shows them
    # as one case (migration 012), so 11 rows of one street-light purchase read as one.
    _together: dict[tuple, list[str]] = field(default_factory=dict)
    _splits: dict[str, dict] = field(default_factory=dict)

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
            for r in recs:
                if r.rec is not None and _key(r.description):
                    idx._together.setdefault(_together_key(r), []).append(r.work_id)
            idx._splits.update(split_groups(recs))
        return idx

    def filed_together(self, work_id: str | None) -> tuple[str, int] | None:
        """(case id, works in it) for a work filed with identical others, else None."""
        r = self._ids.get(work_id or "")
        ids = self._together.get(_together_key(r)) if r is not None and r.rec else None
        return (f"G-{min(ids)}", len(ids)) if ids and len(ids) >= 2 else None

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

        at_site, overlap = [], {}
        for x in earlier:
            if not x.sites or not me.sites or x.family is None or x.family != fam:
                continue
            best = min((d for a in me.sites for b in x.sites
                        if (d := same_site(a, b, me.linear)) is not None), default=None)
            if best is None and me.linear:
                # a road filed again a little longer, or a part of it inside a longer road: most
                # of either lies on the other's line (T135)
                share = max((v for a in me.sites for b in x.sites
                             for v in (on_line(b, a), on_line(a, b)) if v is not None),
                            default=0.0)
                if share >= OVERLAP_SHARE:
                    best = min(metres(p, q) for a in me.sites for b in x.sites
                               for p in (a[0], a[1]) if p for q in (b[0], b[1]) if q)
                    overlap[x.work_id] = round(share, 3)
            if best is not None:
                at_site.append((x, best))

        # just past the one-site line (T136: a "new" hall pinned 60 m from a hall finished 16
        # months earlier): a same-kind building or place within NEAR_METRES, for a note
        near = []
        if me.sites and not me.linear:
            seen = {x.work_id for x, _ in at_site}
            for x in earlier:
                if x.work_id in seen or not x.sites or x.family != fam or x.linear:
                    continue
                d = min(metres(a[0], b[0]) for a in me.sites for b in x.sites)
                if PIN_METRES < d <= NEAR_METRES:
                    near.append((x, d))
            near.sort(key=lambda p: (p[1], p[0].work_id))

        nature, wid = declared(me.form)
        link = None
        if wid:
            x = self._ids.get(wid)
            x = x if x and x.district == me.district else None
            link = {"nature": nature, "work_id": wid, "rec": x,
                    "same_ground": bool(x) and same_ground(me, x)}

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
        if known is not None and known.description == me.description:
            split = self._splits.get(me.work_id)
        else:                                 # a new work: its pieces are looked for on the spot
            split = split_groups(others + [me]).get(me.work_id)
            _localise(others)                 # leave the index as it was
            _count_copies(others)
        alike.sort(key=lambda p: (-p[1], p[0].work_id))
        at_site.sort(key=lambda p: (p[1], p[0].work_id))
        return {"me": me, "at_site": at_site, "overlap": overlap, "declared": link,
                "look_alike": alike[:5], "near": near[:3],
                "answers": answers(me.form), "compared": len(others), "split": split,
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
