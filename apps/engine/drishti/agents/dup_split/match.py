"""Duplicate & Split rules: one code path for every work, seen before or not (T051).

T030 compared descriptions with a meaning model offline and stored the answer per work, so a
work filed after that run was never compared, yet read "compared with every work in its
district: no repeat found". The rules now live here, use only the standard library, and run
wherever the engine runs: over the whole corpus in the batch, over one district for a new
work from the API.

WORDS
  place words  every word NOT in reference/generic_words.txt (words found in at least 5% of
               districts, data/build_generic_words.py): a village the engine has never seen
               is a place word without any corpus count
  text         letter-trigram Dice of the description's words (Hindi/English work words
               mapped together: sadak = road, nirman = construction). Calibrated on the 130
               pairs read by eye for T030: at 0.62 it keeps every pair read as "same".
  numbers      survey no., property no., chainage: different numbers = different sites
  sides        "north side" / "east side", "western flank" / "eastern flank" = two works
  local words  a word in many works of one district (its name, the agency, a typo one office
               repeats) is that district's boilerplate, not a place (counted live)

DUPLICATES (pairs)
  same district, recommended within 24 months; text >= 0.62; place words agree as whole lists
  (Indel similarity of the sorted lists >= 85); a pair with no place words cannot confirm a
  site; different numbers = different sites; wording filed 3+ times by one MP in a district
  = a series. Score 0.50 text + 0.20 place + 0.15 time + 0.15 amount, flagged at 0.75.
  Same MP within 60 days = a batch (the group rules look at it). Repair / phase / balance
  words in the later work = staged, not flagged. The first COMPLETED before the second was
  recommended = after_completed, otherwise while_open.
  repair_after_built (2 Oct 2026, playbook B4/C19): the later work REPAIRS what the first built
  at the same place, within three years of its completion; judged on the asset (verbs left
  out, >= 0.75) and how soon, not the amount (a repair costs less).
  A completed work with no recommendation date (the dashboard's Completed table) can be the
  first of a pair, dated by its completion; it cannot be the later one.

SPLITS AND BULK ORDERS (groups)
  same district, work type and MP; each recommended within 30 days of the previous; text
  >= 0.80; cut by place words and numbers; amounts alike (coefficient of variation < 0.15).
  same_site_split  2+ pieces naming the same place
  stretches        ... whose pieces carry different part / phase / chainage labels ("part-1",
                   "Bit-III", "chainage 0 to 250 m"): one job cut into numbered pieces
  bulk_order       3+ pieces naming no place (or goods, or "different places")
  under_limit      every piece within 80-100% of a limit (reference/rules.json) and the total
                   above it: amounts pile up just under Rs 5 and Rs 10 lakh nationally.
"""

from __future__ import annotations

import json
import re
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date
from functools import cache, lru_cache
from pathlib import Path

from drishti import reference
from drishti.agents.statistical.scope import GOODS, many_sites, scope, undescribed

TEXT_MIN = 0.62
PLACE_MIN = 85.0
DUP_DAYS = int(24 * 30.4)
AMOUNT_TOL = 0.25
FLAG = 0.75
BATCH_DAYS = 60
SPLIT_TEXT, SPLIT_GAP_DAYS, SPLIT_MIN, SPLIT_CV = 0.80, 30, 3, 0.15
SITE_TEXT = 0.90
REPAIR_ASSET_MIN = 0.75
SERIES_COPIES = 3

REF = Path(reference.__file__).resolve().parent
SYNONYMS = {"sadak": "road", "sadk": "road", "sarak": "road", "marg": "road", "rasta": "road",
            "nirman": "construction", "nirmaan": "construction", "karya": "work",
            "nali": "drain", "naali": "drain", "bhawan": "building", "bhavan": "building",
            "kaksha": "classroom", "kharanja": "khadanja", "khadanza": "khadanja",
            "pakka": "pucca", "pakki": "pucca", "handpump": "handpump", "nalkoop": "borewell",
            "सड़क": "road", "मार्ग": "road", "निर्माण": "construction", "कार्य": "work",
            "नाली": "drain", "भवन": "building", "कक्ष": "classroom", "खड़ंजा": "khadanja",
            # 2 Oct 2026: the same work refiled in the other language ("samudayik bhawan nirman"
            # / "community hall ka nirman karya") or abbreviated ("Constn. of")
            "samudayik": "community", "samuhik": "community", "sarvajanik": "public",
            "hall": "building", "vidyalay": "school", "vidyalaya": "school",
            "pathshala": "school", "shauchalay": "toilet", "shauchalaya": "toilet",
            "talab": "pond", "pokhar": "pond", "pokhara": "pond", "puliya": "culvert",
            "pulia": "culvert", "chahardiwari": "boundarywall", "chardiwari": "boundarywall",
            "constn": "construction", "const": "construction", "constructing": "construction",
            "installing": "installation", "adhishthapan": "installation",
            "adhisthapan": "installation", "sthapna": "installation", "marammat": "repair",
            "maramat": "repair"}
FILLER = set("of the and at in on to for from near with ka ki ke me mein se tak par wa va evam "
             "का की के में से तक पर व एवं हेतु".split())
# Hindi words that never name a place (the corpus has no Devanagari to learn them from).
HI_GENERIC = set("ग्राम गांव गाँव पंचायत वार्ड मोहल्ला नगर क्षेत्र विकास खंड ब्लॉक जिला स्थित पास सामने "
                 "निर्माण कार्य सड़क मार्ग भवन नाली खड़ंजा इंटरलॉकिंग सीसी रोड स्कूल विद्यालय "
                 "सामुदायिक शौचालय हैंडपंप सोलर लाइट स्ट्रीट".split())
STAGED = re.compile(r"\b(repair|renovation|marammat|maramat|extension|additional|phase|second|"
                    r"2nd|3rd|remaining|balance|continuation|continued|upgradation|widening|"
                    r"instal+ment|stage)\b", re.I)
TOKEN = re.compile(r"[a-z]+|[ऀ-ॣ०-෿]+|[^\W\d_]+")
NUMBER = re.compile(r"\d+")
# Opposite sides of one road are two works ("Western Flank" / "Eastern Flank", "North Side" /
# "East Side": read by eye, DEV1 and DEV2, 1 Oct 2026).
SIDES = {"north": "N", "northern": "N", "uttar": "N", "उत्तर": "N",
         "south": "S", "southern": "S", "dakshin": "S", "दक्षिण": "S",
         "east": "E", "eastern": "E", "purab": "E", "purv": "E", "purva": "E", "पूर्व": "E",
         "west": "W", "western": "W", "paschim": "W", "pashchim": "W", "पश्चिम": "W",
         "left": "L", "right": "R"}


def sides(text: str | None) -> frozenset[str]:
    return frozenset(SIDES[x] for x in TOKEN.findall((text or "").lower()) if x in SIDES)


# A men's and a women's building are two works ("Resting Barracks ... for Men" / "... for
# Women", "Vishranthi Dhamam (Male block)" / "(Female block)": read by eye on the dashboard's
# split flags, 2 Oct 2026). Only a DIFFERENCE counts: two girls' toilets are still alike.
GENDERS = {"men": "M", "male": "M", "gents": "M", "boys": "M", "boy": "M", "purush": "M",
           "balak": "M", "पुरुष": "M", "बालक": "M",
           "women": "F", "female": "F", "ladies": "F", "girls": "F", "girl": "F",
           "mahila": "F", "balika": "F", "महिला": "F", "बालिका": "F"}


def genders(text: str | None) -> frozenset[str]:
    return frozenset(GENDERS[x] for x in TOKEN.findall((text or "").lower()) if x in GENDERS)


@cache
def generic_words() -> frozenset[str]:
    lines = (REF / "generic_words.txt").read_text(encoding="utf-8").splitlines()
    return frozenset(x.strip() for x in lines if x.strip() and not x.startswith("#"))


@cache
def split_limits() -> tuple[float, ...]:
    data = json.loads((REF / "rules.json").read_text(encoding="utf-8"))
    return tuple(float(x) for x in data["split_limits"]["rupees"])


def words(text: str | None) -> list[str]:
    return [SYNONYMS.get(x, x) for x in TOKEN.findall((text or "").lower())]


@cache
def _generic_buckets() -> dict[tuple[str, int], tuple[str, ...]]:
    out: dict[tuple[str, int], list[str]] = defaultdict(list)
    for g in generic_words():
        out[(g[0], len(g))].append(g)
    return {k: tuple(v) for k, v in out.items()}


TYPO_MIN = 85.0
# a long word can carry two slips ("antergart" for "antargat", 82% alike): on the team's 159
# pairs read by eye this kept one more real repeat and added no false one (80% added one)
TYPO_MIN_LONG, LONG_WORD = 82.0, 8


@lru_cache(maxsize=300_000)
def misspelt_generic(x: str) -> bool:
    """A misspelling of a generic word ("providign", "constrution", "witg") is not a place.
    Read by eye (TEST groups, 1 Oct 2026): identical works naming no place were grouped as
    "one site" because a typo was their only uncommon word."""
    if len(x) < 4:
        return False
    buckets = _generic_buckets()
    bar = TYPO_MIN_LONG if len(x) >= LONG_WORD else TYPO_MIN
    for n in range(len(x) - 2, len(x) + 3):
        for g in buckets.get((x[0], n), ()):
            if indel_ratio(x, g) >= bar:
                return True
    return False


def place_words(text: str | None) -> str:
    """Words that are not generic anywhere (nor a misspelling of one): candidate place names."""
    gen = generic_words()
    out = set()
    for x in TOKEN.findall((text or "").lower()):
        if x.isascii():
            if len(x) >= 4 and x not in gen and not misspelt_generic(x):
                out.add(x)
        elif len(x) >= 2 and x not in HI_GENERIC and x not in FILLER:
            out.add(x)
    return " ".join(sorted(out))


# A word in many works of ONE district is that district's boilerplate (its own name, the
# constituency, the agency, a typo one office repeats: "implemneting agency pccd bijnore"),
# not a site. Read by eye on 1 Oct 2026: with only the national generic list, 38 of the 40
# fresh pairs were two different villages sharing such words. Counted live per district, so
# no corpus constant is needed.
LOCAL_MAX_WORKS = 8
LOCAL_MAX_SHARE = 0.01


def local_limit(n_works: int) -> int:
    return max(LOCAL_MAX_WORKS, int(LOCAL_MAX_SHARE * n_works))


# One village, two clerks: "Chakwa" / "Chakva", "Ghurpur" / "Gurpur", "Belauli" / "Belaauli".
# Two spellings are compared by their sound as well as their letters: w = v, long vowels short,
# aspirates plain (bh = b, kh = k), z = j, ph = f, doubled letters single. Short names differ
# by one letter (chakwa / chakva is 83% alike, under the 85% bar), so the sound key catches
# what the letter match cannot.
_SOUND = ((re.compile(r"w"), "v"), (re.compile(r"z"), "j"), (re.compile(r"ph"), "f"),
          (re.compile(r"([kgcjtdpb])h"), r"\1"), (re.compile(r"aa+"), "a"),
          (re.compile(r"ee+|ii+"), "i"), (re.compile(r"oo+|uu+"), "u"),
          (re.compile(r"(.)\1+"), r"\1"))


@lru_cache(maxsize=200_000)
def sound_key(word: str) -> str:
    k = word.lower()
    for rx, sub in _SOUND:
        k = rx.sub(sub, k)
    return k


def _same_word(x: str, y: str) -> bool:
    return indel_ratio(x, y) >= PLACE_MIN or (
        len(x) >= 5 and len(y) >= 5 and sound_key(x) == sound_key(y))


def place_agreement(a: str, b: str) -> float:
    """Share (0-100) of the place words of both works that the other work also names
    (a word matches when it is at least 85% alike, so "podumbu" = "podhumbu", or sounds the
    same, so "chakwa" = "chakva")."""
    wa, wb = a.split(), b.split()
    if not wa or not wb:
        return 0.0
    hits = sum(any(_same_word(x, y) for y in wb) for x in wa)
    hits += sum(any(_same_word(y, x) for x in wa) for y in wb)
    return 100.0 * hits / (len(wa) + len(wb))


# One job cut into numbered parts: "part-1", "Part II", "phase 2", "Bit-III", "stretch 1",
# "package 3", "chainage 0 to 250 m", "km 1.2 to 1.8". The number names the PIECE, not the site,
# so it is kept out of the site numbers; pieces at one site with different labels recommended
# together are a split into stretches (read by eye on the dashboard, 2 Oct 2026: a police
# station repair "Part-I" / "Part-II" at Rs 5.01 lakh each; a road "Bit-I/II/III").
SEGMENT = re.compile(r"\b(part|phase|bit|stretch|reach|section|package|pkg|lot|khand)\s*[-:.#]?\s*"
                     r"(?:no\.?\s*)?(\d{1,2}|[ivx]{1,4})(?![\w.])", re.I)
CHAINAGE = re.compile(r"\b(?:ch(?:ainage)?|km)\.?\s*(\d+(?:[.+]\d+)?)\s*(?:m|mtrs?|km)?\s*"
                      r"(?:to|-)\s*(\d+(?:[.+]\d+)?)", re.I)
ROMAN = {"i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5, "vi": 6, "vii": 7, "viii": 8, "ix": 9,
         "x": 10}


def segment(text: str | None) -> str | None:
    """The piece a description names ("part:2", "ch:250-500"), or None."""
    t = text or ""
    m = SEGMENT.search(t)
    if m:
        n = m.group(2).lower()
        n = str(ROMAN.get(n, n)) if not n.isdigit() else str(int(n))
        return f"{m.group(1).lower()}:{n}"
    c = CHAINAGE.search(t)
    if c:
        return f"ch:{c.group(1)}-{c.group(2)}"
    return None


def site_numbers(text: str | None) -> str:
    """Numbers that can tell two sites apart (plot, ward, house), not those naming a piece."""
    t = SEGMENT.sub(" ", text or "")
    t = CHAINAGE.sub(" ", t)
    return " ".join(sorted(set(NUMBER.findall(t))))


# Repair of an asset (playbook B4 / C19): a new road or hall repaired within three years of being
# built under the scheme reads as the first work not done, or done badly. The verbs are dropped
# when the two descriptions are compared, so "Repair of community hall at X" meets
# "Construction of community hall at X".
REPAIR = re.compile(r"\b(repairs?|repairing|renovation|renovat\w*|marammat|maramat|mrammat|"
                    r"jirnoddhar|jirnodhar|jeernoddhar|resurfacing|restoration|re-?carpeting)\b",
                    re.I)
REPAIR_DAYS = 3 * 365
VERBS = re.compile(r"\b(construction|constructing|construct|const|constn|c/o|nirman|nirmaan|"
                   r"karya|work|works|providing|provision|installation|installing|laying|"
                   r"development|new|of|ka|ki|ke|repairs?|repairing|renovation|renovat\w*|"
                   r"marammat|maramat|mrammat|jirnoddhar|jirnodhar|jeernoddhar|resurfacing|"
                   r"restoration|re-?carpeting)\b", re.I)


def asset_sim(a: str | None, b: str | None) -> float:
    """Text similarity of what is built where, the verbs ("construction", "repair") left out."""
    return text_sim(VERBS.sub(" ", a or ""), VERBS.sub(" ", b or ""))


@lru_cache(maxsize=100_000)
def trigrams(text: str) -> frozenset[str]:
    s = " ".join(x for x in words(text) if x not in FILLER)
    return frozenset(s[i:i + 3] for i in range(len(s) - 2))


def text_sim(a: str | None, b: str | None) -> float:
    ta, tb = trigrams(a or ""), trigrams(b or "")
    if not ta or not tb:
        return 0.0
    return 2 * len(ta & tb) / (len(ta) + len(tb))


def indel_ratio(a: str, b: str) -> float:
    """Normalised Indel similarity x100 (what rapidfuzz.fuzz.ratio computes)."""
    if not a and not b:
        return 100.0
    if not a or not b:
        return 0.0
    prev = [0] * (len(b) + 1)
    for ca in a:
        cur = [0]
        for j, cb in enumerate(b):
            cur.append(prev[j] + 1 if ca == cb else max(prev[j + 1], cur[j]))
        prev = cur
    return 200.0 * prev[-1] / (len(a) + len(b))


def _key(text: str | None) -> str:
    return re.sub(r"[^a-z0-9ऀ-෿]+", "", (text or "").lower())


@dataclass
class Rec:
    work_id: str
    district: str
    work_type: str
    mp: str
    rec: date | None               # None: a completed work whose recommendation date is
    done: date | None              # not in the record (the dashboard's Completed table)
    status: str | None
    amount: float
    description: str
    raw_place: str = ""            # not generic anywhere
    place: str = ""                # ... and not boilerplate of its own district
    nums: str = ""
    copies: int = 1
    segment: str | None = None     # the numbered piece the description names, if any

    @property
    def when(self) -> date:
        """The work's date for ordering: recommended, else completed (it existed by then)."""
        return self.rec or self.done  # type: ignore[return-value]

    @classmethod
    def of(cls, w: dict) -> Rec | None:
        amount = float(w.get("amount") or 0)
        rec, done = w.get("recommended_date"), w.get("completed_date")
        desc = w.get("description")
        if amount <= 0 or (rec is None and done is None) or undescribed(desc):
            return None
        return cls(work_id=w["work_id"], district=str(w.get("district_lgd") or "NA"),
                   work_type=str(w.get("work_type_code") or "NA"),
                   mp=str(w.get("mp_name") or "NA"), rec=rec, done=done,
                   status=w.get("status"), amount=amount, description=str(desc),
                   raw_place=place_words(desc), nums=site_numbers(desc),
                   segment=segment(desc))


def _pair(ra: Rec, rb: Rec) -> dict | None:
    """The rules for one candidate pair; None when it is not a duplicate."""
    if rb.when < ra.when:
        ra, rb = rb, ra
    if rb.rec is None:
        return None                                   # the later work's date is unknown
    gap = (rb.rec - ra.when).days
    if ra.mp == rb.mp and gap <= BATCH_DAYS:
        return None                                   # a batch: the group rules' business
    if not ra.place or not rb.place:
        return None                                   # no site named, cannot confirm
    if ra.copies >= SERIES_COPIES or rb.copies >= SERIES_COPIES:
        return None                                   # a series of identical works
    if ra.nums and rb.nums and ra.nums != rb.nums:
        return None                                   # different plot / ward / house numbers
    if ra.segment and rb.segment and ra.segment != rb.segment:
        return None                                   # two numbered pieces: the group rules'
    sa, sb = sides(ra.description), sides(rb.description)
    if sa and sb and sa != sb:
        return None                                   # opposite sides of one road
    ga, gb = genders(ra.description), genders(rb.description)
    if ga and gb and ga != gb:
        return None                                   # a men's and a women's building
    place = place_agreement(ra.place, rb.place)
    if place < PLACE_MIN:
        return None
    amt_diff = abs(ra.amount - rb.amount) / max(ra.amount, rb.amount, 1.0)
    built = ra.done is not None and ra.done < rb.rec
    if (built and REPAIR.search(rb.description) and not REPAIR.search(ra.description)
            and (rb.rec - ra.done).days <= REPAIR_DAYS):
        # a repair of what the first work built: judged on the asset, not the amount (a repair
        # costs less), and on how soon after completion it comes
        asset = asset_sim(ra.description, rb.description)
        soon = (rb.rec - ra.done).days
        score = 0.60 * asset + 0.25 * place / 100 + 0.15 * max(0.0, 1 - soon / REPAIR_DAYS)
        if asset < REPAIR_ASSET_MIN or score < FLAG:
            return None
        return {"a": ra.work_id, "b": rb.work_id, "kind": "repair_after_built",
                "score": round(score, 4), "text": round(asset, 4), "place": round(place, 1),
                "gap_days": gap, "days_after_completion": soon, "amount_a": ra.amount,
                "amount_b": rb.amount, "amount_diff": round(amt_diff, 4)}
    # the clock of a repeat starts when the first work was finished, if it was: a work filed
    # again soon after completion is the question, and building it took months (2 Oct 2026)
    clock = (rb.rec - ra.done).days if built else gap
    if clock > DUP_DAYS:
        return None
    text = text_sim(ra.description, rb.description)
    if text < TEXT_MIN:
        return None
    score = (0.50 * text + 0.20 * place / 100 + 0.15 * max(0.0, 1 - clock / 730)
             + 0.15 * max(0.0, 1 - amt_diff / AMOUNT_TOL))
    if score < FLAG:
        return None
    staged = bool(STAGED.search(rb.description))
    kind = "staged" if staged else ("after_completed" if built else "while_open")
    return {"a": ra.work_id, "b": rb.work_id, "kind": kind, "score": round(score, 4),
            "text": round(text, 4), "place": round(place, 1), "gap_days": gap,
            "days_after_completion": clock if built else None,
            "amount_a": ra.amount, "amount_b": rb.amount, "amount_diff": round(amt_diff, 4)}


def _under_limit(amounts: list[float]) -> float | None:
    """The limit every piece sits just under while the total passes it, else None."""
    total = sum(amounts)
    for lim in split_limits():
        if all(0.8 * lim <= a <= lim for a in amounts) and total > lim:
            return lim
    return None


def _cv(amounts: list[float]) -> float:
    m = sum(amounts) / len(amounts)
    if m <= 0:
        return 1.0
    var = sum((a - m) ** 2 for a in amounts) / len(amounts)
    return var ** 0.5 / m


def groups_in_block(recs: list[Rec], gap: int = SPLIT_GAP_DAYS) -> list[dict]:
    """Chains of alike works of one district, type and MP, recommended within `gap` days of the
    next, then cut by place words."""
    recs = sorted((r for r in recs if r.rec is not None), key=lambda r: r.rec)
    parent = list(range(len(recs)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i in range(len(recs)):
        for j in range(i + 1, len(recs)):
            if (recs[j].rec - recs[i].rec).days > gap:
                break
            if text_sim(recs[i].description, recs[j].description) >= SPLIT_TEXT:
                parent[find(i)] = find(j)
    chains: dict[int, list[Rec]] = defaultdict(list)
    for i, r in enumerate(recs):
        chains[find(i)].append(r)
    out = []
    for chain in chains.values():
        if len(chain) < 2:
            continue
        parts: dict[tuple[str, str, frozenset, frozenset], list[Rec]] = defaultdict(list)
        for r in chain:
            parts[(r.place, r.nums, sides(r.description), genders(r.description))].append(r)
        for (place, _nums, _sides, _genders), sub in parts.items():
            first = sub[0].description
            # one site = a place is named AND the pieces are near word for word the same: the
            # splits read by eye were (min alike 0.74-1.0, most 1.0); pieces that differ in a
            # name or landmark ("near X's house" / "near Y's house") were different spots
            alike = min((text_sim(a.description, b.description)
                         for i, a in enumerate(sub) for b in sub[i + 1:]), default=1.0)
            goods = scope(first) == GOODS or many_sites(first)
            if place and not goods and alike < SITE_TEXT:
                continue                     # a batch for different spots: ordinary
            one_site = bool(place) and not goods
            kind = "same_site_split" if one_site else "bulk_order"
            labels = {r.segment for r in sub if r.segment}
            if one_site and len(labels) >= 2:
                kind = "stretches"           # one job at one site in numbered pieces
            if len(sub) < (2 if one_site else SPLIT_MIN):
                continue
            amounts = [r.amount for r in sub]
            cv = _cv(amounts)
            if cv >= SPLIT_CV:
                continue
            members = sorted(r.work_id for r in sub)
            out.append({"group_id": "G-" + members[0], "kind": kind, "size": len(sub),
                        "total": float(sum(amounts)), "cv": round(cv, 4),
                        "under_limit": _under_limit(amounts) is not None,
                        "limit": _under_limit(amounts), "shared_place": place if one_site else "",
                        "days": (max(r.rec for r in sub) - min(r.rec for r in sub)).days,
                        "members": members, "amounts": amounts,
                        "segments": sorted(labels)})
    return out


@dataclass
class DupIndex:
    """Every comparable work, by district, with its pairs and groups worked out on demand."""
    by_district: dict[str, list[Rec]] = field(default_factory=dict)
    _ids: dict[str, Rec] = field(default_factory=dict)
    _pairs: dict[str, list[dict]] = field(default_factory=dict)
    _groups: dict[str, dict] = field(default_factory=dict)
    _done_districts: set[str] = field(default_factory=set)

    @classmethod
    def build(cls, works) -> DupIndex:
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

    def _solve_district(self, district: str) -> None:
        if district in self._done_districts:
            return
        recs = self.by_district.get(district, [])
        postings: dict[str, list[int]] = defaultdict(list)
        for i, r in enumerate(recs):
            for p in set(r.place.split()):
                postings[p].append(i)
        for i, r in enumerate(recs):
            cands = {j for p in set(r.place.split()) for j in postings[p] if j > i}
            for j in sorted(cands):
                p = _pair(r, recs[j])
                if p and p["kind"] != "staged":
                    self._pairs.setdefault(p["a"], []).append(_side(p, p["a"]))
                    self._pairs.setdefault(p["b"], []).append(_side(p, p["b"]))
        blocks: dict[tuple[str, str], list[Rec]] = defaultdict(list)
        for r in recs:
            blocks[(r.work_type, r.mp)].append(r)
        for block in blocks.values():
            if len(block) >= 2:
                for g in groups_in_block(block):
                    for wid in g["members"]:
                        self._groups[wid] = g
        self._done_districts.add(district)

    def check(self, work: dict) -> dict | None:
        """{"pairs": [...], "group": {...} | None} for a work, or None if it can't be compared.

        A work the index holds is answered from its district's solved pairs and groups; a work
        it does not hold (a new recommendation) is compared with its district on the spot."""
        r = Rec.of(work)
        if r is None:
            return None
        known = self._ids.get(r.work_id)
        if known is not None and known.description == r.description and known.rec == r.rec:
            self._solve_district(r.district)
            return {"pairs": _top(self._pairs.get(r.work_id, [])),
                    "group": _public(self._groups.get(r.work_id), r.work_id),
                    "compared": len(self.by_district.get(r.district, [])) - 1,
                    "place_named": bool(known.place)}
        recs = [x for x in self.by_district.get(r.district, []) if x.work_id != r.work_id]
        _localise(recs + [r])
        _count_copies(recs + [r])
        pairs = [p for x in recs if (p := _pair(r, x)) and p["kind"] != "staged"]
        block = [x for x in recs if x.work_type == r.work_type and x.mp == r.mp] + [r]
        group = next((g for g in groups_in_block(block) if r.work_id in g["members"]), None)
        place_named = bool(r.place)
        _localise(recs)                              # leave the index as it was
        _count_copies(recs)
        return {"pairs": _top([_side(p, r.work_id) for p in pairs]),
                "group": _public(group, r.work_id), "compared": len(recs),
                "place_named": place_named}


def _localise(recs: list[Rec]) -> None:
    """Drop each district's boilerplate words from its works' place words."""
    df: dict[str, int] = defaultdict(int)
    for r in recs:
        for x in set(r.raw_place.split()):
            df[x] += 1
    limit = local_limit(len(recs))
    for r in recs:
        r.place = " ".join(x for x in r.raw_place.split() if df[x] <= limit)


def _count_copies(recs: list[Rec]) -> None:
    counts: dict[tuple[str, str], int] = defaultdict(int)
    for r in recs:
        counts[(r.mp, _key(r.description))] += 1
    for r in recs:
        r.copies = counts[(r.mp, _key(r.description))]


def _side(p: dict, me: str) -> dict:
    """The pair as seen from one of its two works."""
    first_is_me = p["a"] == me
    return {"other": p["b"] if first_is_me else p["a"], "kind": p["kind"], "score": p["score"],
            "text": p["text"], "place": p["place"], "gap_days": p["gap_days"],
            "other_amount": p["amount_b"] if first_is_me else p["amount_a"],
            "amount_diff": p["amount_diff"], "this_is_later": not first_is_me,
            "days_after_completion": p.get("days_after_completion")}


def _top(pairs: list[dict]) -> list[dict]:
    return sorted(pairs, key=lambda x: -x["score"])[:5]


def _public(g: dict | None, me: str) -> dict | None:
    if g is None:
        return None
    return {k: g[k] for k in ("group_id", "kind", "size", "total", "under_limit", "limit",
                              "shared_place", "days", "cv")} | {
        "others": [x for x in g["members"] if x != me][:5], "segments": g.get("segments", [])}
