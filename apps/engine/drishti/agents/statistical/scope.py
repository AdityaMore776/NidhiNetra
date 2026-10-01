"""What does the money buy? Read from the description before comparing a cost.

A work type is coarse. Measured on the real corpus (30 Sept 2026): LIBRARY holds book
purchases (median Rs 1 lakh) and library buildings (median Rs 7 lakh); COMPUTER holds
laptops and crore-rupee incubation labs; WATER_TANK holds water-cooler supplies and
tanks. Comparing a building with book orders called it 1,000x "typical". So a work is
compared only with works that buy the same kind of thing:

  GOODS      purchase / supply / distribution of books, equipment, furniture, vehicles
  WORKS      construction, repair, installation (anything built on site)

Two readings take a work out of the price comparison altogether:

  UNDESCRIBED  the description does not say what is built or bought ("Letter as per
               attached", "NA", an empty field): a cost cannot be judged against nothing
  MANY_SITES   the amount covers a whole constituency, block, ward list or "various
               villages": the number of sites is unknown, so it is a bundle, not a mark-up
"""

from __future__ import annotations

import re
from dataclasses import dataclass

GOODS, WORKS = "GOODS", "WORKS"

_GOODS_VERB = re.compile(
    r"\b(?:purchas\w*|procure\w*|(?<!water\s)supply(?!\s+(?:line|scheme|system|pipe))|supplies|"
    r"supplying|distribut\w*|kharid\w*|apurti|aapurti|kray|providing\s+of\s+books)\b", re.I)
_GOODS_NOUN = re.compile(
    r"\b(?:books?|pustak\w*|periodicals|equipments?|machines?|mechine|laptops?|computers?|"
    r"tablets?|desks?|benches|furniture|almirah\w*|chairs?|vehicles?|ambulances?|tankers?|"
    r"x-?ray|mri|ct\s*scan|ultrasound|ventilators?|projectors?|printers?)\b", re.I)
_BUILD = re.compile(
    r"\b(?:construct\w*|const|c/o|nirman|erection|building|renovat\w*|repair\w*|extension|"
    r"additional\s+rooms?|civil\s+works?|laying|roads?|streets?|drains?|drainage|paver\w*|"
    r"pathway|drilling|installation\s+of\s+(?:high|solar|street))\b",
    re.I)

# Descriptions that name no object. Matched against the whole (normalised) text.
_UNDESCRIBED = re.compile(
    r"^(?:|na|n/?a|nil|none|no\s+description|\(no\s+description\)|-+|\.+|\?[\s?/().-]*|"
    r"mplads[\s\-:]*\d*|as\s+per\s+\w+|see\s+mp\s+letter\b.*|"
    r"(?:the\s+)?(?:letter|list|details?|works?|proposal)?\s*(?:is\s+)?(?:as\s+per|as\s+par|"
    r"see|please\s+see|refer(?:\s+to)?|vide)\s+(?:the\s+)?(?:attached|attachment|attechment|"
    r"atech|enclosed|annexure|list|letter)"
    # "Please see the attached documents." (read by eye, dup/split TEST, 1 Oct 2026)
    r"(?:\s+(?:list|letter|annexure|sheet|documents?|files?|pdf))?)$",
    re.I)

_MANY_SITES = re.compile(
    r"\b(?:various|many|multiple|several)\s+(?:villages?|places?|locations?|wards?|blocks?|"
    r"panchayats?|sites?|schools?|"
    r"public\s+places?|areas?|cd\s+blocks?)"
    r"|\bvar[io]+us\s+(?:cd\s+)?blocks?"
    r"|\b(?:diff?e?rent|deferent|diffrent|vibhinn)\s+(?:villages|gram\s+panchayats|panchayats|"
    r"wards|blocks|schools|places|locations?|sites|sthalon?)"
    r"|\bvarious\s+(?:\w+\s+){0,2}(?:streets?|roads|lanes|drains|wards|buildings)\b"
    r"|\b(?:[2-9]|\d{2,4})\s+(?:public\s+|govt\.?\s+|government\s+|different\s+|"
    r"sarvajanik\s+|(?!(?:rooms?|class\w*|storey\w*|floors?|bed\w*|seater|km|kms|mtrs?)\b)"
    r"[a-z]+\s+)?"
    r"(?:villages|gram\s+panchayats|panchayats|sthano|sthanon|sthalo|sthalon|schools?|"
    r"colleges?|locations|places|sites)\b"
    r"|\bcd\s+blocks\b"
    r"|\bward\s*nos?\.?\s*\d+(?:\s*[,&]\s*\d+){2,}"
    r"|\bletter\s+(?:no\.?|number)\s*\d+\s+for\s+\w+\s+block"
    r"|\blocations?\s+will\s+be"
    r"|\b(?:at\s+|in\s+)?the\s+following\s+(?:places|villages|locations|sites|schools|gram|"
    r"wards|panchayats|cities)"
    r"|\bas\s+pe[rs]\s+(?:the\s+)?(?:enclosed|endosed|attached|atteched)\s+list",
    re.I)

# "at 1 Dilawal Patti 2 Akhtiyarpur 3 Nakhatpur", "1. Buniadanga 2. Abadanga 3. ...":
# a numbered list of three or more places in the description.
_LIST_ITEM = re.compile(r"(?<![\d.,/-])\b(\d{1,2})\s*[.)\-:]?\s+[A-Za-z]")


# "Installation of Handpumps at Raki, Mustafabad, Narwal, Usmanpur, Rampur Kasiha": four or
# more comma-separated names after "at" / "in" read as a list of sites.
_COMMA_LIST = re.compile(r"\b(?:at|in)\s+(?:[A-Z][\w.'-]*(?:\s+[A-Z][\w.'-]*)?\s*,\s*){3,}[A-Z]")


def numbered_list(text: str | None) -> bool:
    seen = [int(m.group(1)) for m in _LIST_ITEM.finditer(text or "")]
    want = 1
    for n in seen:
        if n == want:
            want += 1
            if want > 3:
                return True
    return False

# "Solar light in Allahabad lok sabha chhetra": the whole constituency, when the text is
# short. A long description that names a village or a building is one site, even if it
# also mentions the constituency ("... in Block Barpur of my parliamentary constituency").
_WIDE_AREA = re.compile(
    r"\blok\s*sabha\b|\bloksabha\b|\bparliamentary\s+constituency\b|\bconstituency\b|"
    r"\bkshetra\b|\bchhetra\b|\bvidhansabha\b", re.I)
WIDE_AREA_MAX_WORDS = 10


# "50 Nos of Street Lights", "195 nos LED lights", "Installation of 38 LED Highmast Lights",
# "TOTAL 50 BENCH", "10 Handpumps": a count of identical units, so the work can be priced
# per unit. Only counts of units are read; "ward no 70" or "9 Mtr pole" are not counts.
_UNIT = (r"(?:solar\s+)?(?:street\s*)?(?:led\s+)?(?:semi\s*)?(?:high\s*mast\w*|mini\s*mast|"
         r"lights?|lamps?|poles?|hand\s*pumps?|handpumps?|bore\s*wells?|borewells?|benches|"
         r"bench|computers?|laptops?|cameras?|cctv\w*|desks?|chairs?|tankers?|toilets?|"
         r"sheds?|bus\s*(?:stops?|shelters?)|pyau|water\s*coolers?|coolers?|ro\s*plants?|"
         r"almirahs?|tables?|fans?|sets?)")
_COUNT = re.compile(
    r"(?<![.\d,\-/])\b(\d{1,4})\b(?![.\-)/]|\s*,\s*\d)"
    r"(?!\s*(?:m|mtrs?|meters?|metres?|ft|feet|watts?|w|mm|kw|kva|v|hp|stages?|ltrs?|litres?|"
    r"liters?|letres?|"
    r"lpd|lph|lakh|lakhs|lac|lacs|rs|km|kms|years?|days?|months?|way|arms?)\b)"
    r"\s*(?:\([^)]{0,30}\)\s*)?(?:nos?\.?|numbers?|pcs?\.?|units?|adad|nag)?\s*(?:of\s+)?"
    r"(?:(?!construct|install|work|nirman|karya|x\b|kv\b)[a-z0-9\-]+\s+){0,3}?" + _UNIT + r"\b"
    r"|\btotal\s+(?:nos?\.?\s*)?(\d{1,4})\s+" + _UNIT
    # "Street Light 35NOS", "Solar light - 16 nos": the count after the item
    + r"|" + _UNIT + r"\s*[-:(]?\s*(\d{1,4})\s*(?:nos?|numbers?|nag|pcs?|adad)\b\.?",
    re.I)
MAX_UNITS = 5000


_NOT_A_COUNT_BEFORE = re.compile(r"(?:\bno\.?|\bnos?\.|\bward|\bdivision|\bsl\.?|\bs\.?\s*no\.?"
                                 r"|\bcenter|\bcentre|\bzone|\bunit|\bplot|\bkhasra)\s*$", re.I)


# The unit a work type is counted in. A per-unit price is read only when the counted
# thing is the type's own unit: "bus shelter with 2 solar lights" is one shelter.
TYPE_UNITS = {
    "STREET_LIGHT": re.compile(r"lights?|lamps?|poles?", re.I),
    "BOREWELL": re.compile(r"pumps?|bore\s*wells?|borewells?", re.I),
    "FURNITURE": re.compile(r"bench|benches|desks?|chairs?|tables?|almirahs?|sets?", re.I),
    "COMPUTER": re.compile(r"computers?|laptops?|sets?", re.I),
    "CCTV": re.compile(r"cameras?|cctv", re.I),
    "BUS_SHELTER": re.compile(r"sheds?|shelters?|bus\s*stops?", re.I),
    "WATER_TANK": re.compile(r"tankers?|coolers?|ro\s*plants?|pyau", re.I),
    "TOILET_BLOCK": re.compile(r"toilets?", re.I),
}


def stated_count(text: str | None, work_type: str | None = None) -> int | None:
    """Number of identical units a description names, when it names one (2 or more).

    With `work_type`, only a count of that type's own unit (TYPE_UNITS) is returned.
    """
    t = text or ""
    if is_mast(t):                  # masts are counted by mast_count, never by lamps
        return None
    unit = TYPE_UNITS.get(work_type or "") if work_type else None
    if work_type and unit is None:
        return None
    best = None
    for m in _COUNT.finditer(t):
        if _NOT_A_COUNT_BEFORE.search(t[max(0, m.start() - 12):m.start()]):
            continue
        if unit is not None and not unit.search(m.group(0)):
            continue
        raw = m.group(1) or m.group(2) or m.group(3)
        try:
            n = int(raw)
        except (TypeError, ValueError):
            continue
        if 2 <= n <= MAX_UNITS:
            best = max(best or 0, n)
    return best


# Masts are counted only when the number is tied to the mast itself: "60 Highmast lights",
# "4 NO 9 MTR OCTAGONAL HIGH MAST", "Mini Mast Light 35NOS". A number tied to lamps
# ("with 8 LED lights", "6 x 200 watt", "8 way") is lamps per mast.
_MAST_WORD = r"(?:high|semi|mini)?[\s-]*(?:mast\w*|mask|mass)"
_MAST_COUNT = re.compile(
    r"(?<![.\d,\-/x*])\b(\d{1,4})\b(?![.\-)/]|\s*[x*])"
    r"(?!\s*(?:m|mr|mt|mtrs?|meters?|metres?|ft|watts?|w|mm|kw|way|arms?|leds?|lights?)\b)"
    r"\s*(?:\([^)]{0,20}\)\s*)?(?:nos?\.?|nag|units?|numbers?)?\s*(?:of\s+)?"
    r"(?:(?!with|x\b|having|wali|wale|wala|vali|vale)[a-z0-9\-.]+\s+){0,4}?" + _MAST_WORD + r"\b"
    r"|" + _MAST_WORD + r"(?:\s+lights?)?\s*[-:(]?\s*(\d{1,4})\s*(?:nos?|nag|numbers?)\b"
    # "... high mask light at DSA ground ... me 4 adad adhisthapit": a count of masts later
    # in the sentence, followed by a word for installing
    r"|" + _MAST_WORD + r"\b.{0,80}?(?<![\d.x*])\b(\d{1,4})\s*(?:adad|nag|nos?\.?|numbers?)\s+"
    r"(?:lights?\s+)?(?:\(|adhisthap|lagan|install|sthapit)",
    re.I)


def is_mast(text: str | None) -> bool:
    return bool(re.search(_MAST_WORD + r"\b|\btower\b", text or "", re.I))


def mast_count(text: str | None) -> int | None:
    best = None
    for m in _MAST_COUNT.finditer(text or ""):
        n = int(m.group(1) or m.group(2) or m.group(3))
        if 2 <= n <= MAX_UNITS:
            best = max(best or 0, n)
    return best


def _norm(text: str | None) -> str:
    t = (text or "").strip().lower()
    t = re.sub(r"[\s ]+", " ", t)
    return t.strip(" .,:;")


def undescribed(text: str | None) -> bool:
    t = _norm(text)
    if _UNDESCRIBED.match(t):
        return True
    # garbled text (a Hindi description lost to "????") names nothing readable
    letters = sum(ch.isalpha() for ch in t)
    return len(t) > 0 and letters < 3


def many_sites(text: str | None) -> bool:
    t = text or ""
    if _MANY_SITES.search(t) or numbered_list(t) or _COMMA_LIST.search(t):
        return True
    return bool(_WIDE_AREA.search(t)) and len(t.split()) <= WIDE_AREA_MAX_WORDS


def scope(text: str | None) -> str:
    """GOODS when the work buys things and builds nothing; WORKS otherwise."""
    t = text or ""
    if _BUILD.search(t):
        return WORKS
    if _GOODS_VERB.search(t) or _GOODS_NOUN.search(t):
        return GOODS
    return WORKS


MAST = "MAST"
# Types whose masts are a different job from the type's other works: a 12.5 m high mast
# costs Rs 5-7 lakh, a street light Rs 20,000-2.7 lakh (measured, 30 Sept 2026).
MAST_TYPES = {"STREET_LIGHT"}


@dataclass(frozen=True)
class Reading:
    """How the cost engine reads one description; the peer builder reads it the same way."""
    scope: str                 # GOODS / WORKS / MAST
    undescribed: bool
    many_sites: bool
    bundle: bool               # several sites or units: the total is not one price
    count: int | None          # units of the type's own kind, when stated

    @property
    def clean(self) -> bool:
        """One described job at one site: the only works that set a price for peers."""
        return not (self.undescribed or self.bundle or self.count)


def read(work_type: str | None, text: str | None) -> Reading:
    from drishti.agents.statistical.text import reads_as_bundle

    mast = (work_type in MAST_TYPES) and is_mast(text)
    sites = many_sites(text)
    if mast:
        n = mast_count(text)
        return Reading(MAST, undescribed(text), sites, sites or bool(n), None)
    n = stated_count(text, work_type)
    return Reading(scope(text), undescribed(text), sites,
                   sites or reads_as_bundle(text) or bool(stated_count(text)), n)
