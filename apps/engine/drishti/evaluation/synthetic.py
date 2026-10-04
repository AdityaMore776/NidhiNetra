"""A synthetic eSAKSHI export with planted, labelled problems (stdlib only, seeded).

Why: the real export holds no labels, and the engines must be tested on works they have never
seen, in districts they have never seen. This generator builds a fresh country for every seed:
states, districts, villages, offices and MPs with made-up names, and works whose shape follows
what the team measured on the 2,09,993 real works (docs/trial/FINDINGS.md):

  types and prices   per-type log-normal amounts; CC roads priced by the fitted length curve
                     (log10 Rs = 4.5381 + 0.6309 log10 m, residual sd 0.2772)
  round sums         about a third of amounts are whole lakh; amounts pile up just under Rs 5
                     and Rs 10 lakh (12.1x and 11.5x more just under than just over)
  places             about 19% of descriptions name no place; landmarks ("near Shiv Mandir"),
                     schools named "Shishu Mandir", "X ke ghar se Y tak", Hinglish and English
  bundles            "25 nos LED street lights in various villages", high-mast lights, goods
  life cycle         the share still waiting for sanction follows the measured wait curve
                     (reference/rules.json wait_curves.r01); completion often not entered
  bulk entry         2023-Q3 offices that back-filled finished works (completed before
                     recommended), the pattern R06 must NOT queue
  batches            one MP, one day, one template, many villages: ordinary, not a split

Planted problems (positive=True) each name the engine meant to catch them and the finding codes
that count as caught. T099 + T100 (3 Oct 2026): a price raised on a record, a repeat or a repair
judged from words alone are no longer checked (measured not certain enough,
data/trial/simple_certain_trial.py); they stay planted as positives that no engine is meant for,
so the report says plainly what the product leaves to the cost estimate form. Splits are
planted at 92-100% of the limit: only those whose every piece is 96%+ are asked about. The
form's own cases are planted too: a map pin at a sanctioned work of the same kind
(PIN_REPEAT), a declared rebuild soon after completion (REBUILT_SOON), and their look-alikes.
Look-alikes (positive=False, kind "HN_*") are what the engines must leave
alone. Every other work is "BACKGROUND". Labels live beside the works, never inside them, so
no engine can read the answer.

Names are generated from syllables; no real person, village or official appears.
"""

from __future__ import annotations

import random
import zlib
from dataclasses import dataclass, field
from datetime import date, timedelta

AS_OF = date(2026, 5, 26)
START = date(2023, 4, 1)
TERM_17_END = date(2024, 6, 5)
LAKH = 100_000.0

# ---------------------------------------------------------------- names (all made up)
_A = ["Ram", "Shiv", "Kher", "Bhit", "Son", "Chak", "Mal", "Nand", "Har", "Dev", "Kal", "Bar",
      "Pip", "Sar", "Gan", "Mah", "Raj", "Kish", "Dhan", "Bel", "Gop", "Lakh", "Mot", "Sant",
      "Bhag", "Kan", "Jag", "Ach", "Bir", "Dul", "Ghur", "Kor", "Pan", "Sem", "Tal", "Udai"]
_B = ["pur", "pura", "ganj", "gaon", "wa", "ari", "oli", "khera", "nagar", "patti", "garh",
      "ahi", "ipur", "dih", "auli", "sar", "wada", "kot", "bari", "hat"]
_PEOPLE = ["Ramesh", "Suresh", "Mahesh", "Rajkumar", "Shyam Lal", "Gopal", "Mohan", "Kailash",
           "Ramdin", "Babulal", "Harinarayan", "Sitaram"]
_LANDMARKS = ["Panchayat Bhawan", "Primary School", "Bus Stand", "Main Road", "Harijan Basti",
              "Anganwadi Kendra", "Pokhar", "Chauraha", "Railway Crossing", "Patel Chowk",
              "Kabristan", "Shamshan Ghat", "Govt Hospital", "Ambedkar Park", "Nahar Pul"]
_TEMPLES = ["Shiv Mandir", "Hanuman Mandir", "Durga Mandir", "Jama Masjid", "Kali Mandir",
            "Ram Janaki Mandir", "Sai Mandir"]
_DEITIES = ["Shiv", "Hanuman", "Durga", "Kali", "Ram Janaki", "Sai Baba"]
_STATES = ["Uttar Rajya", "Dakshin Pradesh", "Purvanchal", "Paschim Desh", "Madhya Bhoomi",
           "Himal Kshetra"]


def _title(s: str) -> str:
    return " ".join(w[:1].upper() + w[1:] for w in s.split())


# A transliteration of the same village name: how one place is spelt by two clerks.
def spelling_variant(name: str, rng: random.Random) -> str:
    low = name.lower()
    moves = []
    if "a" in low[1:]:
        i = low.index("a", 1)
        moves.append(low[:i] + "aa" + low[i + 1:])
    if "aa" in low:
        moves.append(low.replace("aa", "a", 1))
    if "w" in low:
        moves.append(low.replace("w", "v", 1))
    if "v" in low:
        moves.append(low.replace("v", "w", 1))
    if "ee" in low:
        moves.append(low.replace("ee", "i", 1))
    if low.endswith("pur"):
        moves.append(low + "a")
    if low.endswith("pura"):
        moves.append(low[:-1])
    for h in ("bh", "kh", "dh", "gh", "th"):
        if h in low:
            moves.append(low.replace(h, h[0], 1))
            break
    if not moves:
        moves.append(low + "a")
    return _title(rng.choice(moves))


# ---------------------------------------------------------------- types and prices
# code: (share of works, median Rs of one job at one site, sd of log10 Rs)
TYPES: dict[str, tuple[float, float, float]] = {
    "ROAD_CC": (0.21, 5.0 * LAKH, 0.28), "COMMUNITY_HALL": (0.10, 6.0 * LAKH, 0.22),
    "STREET_LIGHT": (0.10, 0.9 * LAKH, 0.30), "BOREWELL": (0.07, 0.9 * LAKH, 0.20),
    "SCHOOL_BUILDING": (0.07, 9.0 * LAKH, 0.25), "BOUNDARY_WALL": (0.06, 4.5 * LAKH, 0.28),
    "DRAIN": (0.06, 4.0 * LAKH, 0.30), "PLAYGROUND": (0.04, 5.0 * LAKH, 0.30),
    "WATER_TANK": (0.03, 3.0 * LAKH, 0.30), "TOILET_BLOCK": (0.03, 3.5 * LAKH, 0.20),
    "BUS_SHELTER": (0.03, 2.5 * LAKH, 0.20), "HEALTH_BUILDING": (0.02, 15.0 * LAKH, 0.25),
    "LIBRARY": (0.03, 1.0 * LAKH, 0.25), "COMPUTER": (0.03, 3.0 * LAKH, 0.30),
    "FURNITURE": (0.02, 1.5 * LAKH, 0.25), "AMBULANCE": (0.01, 18.0 * LAKH, 0.08),
    "POND": (0.02, 6.0 * LAKH, 0.30), "CULVERT": (0.02, 3.0 * LAKH, 0.25),
    "CREMATORIUM": (0.02, 5.0 * LAKH, 0.25), "FOOTPATH": (0.03, 3.0 * LAKH, 0.30),
}
# works the cost estimate form takes both ends for (reference/cost_form.yaml families)
LINEAR = {"ROAD_CC", "BOUNDARY_WALL", "DRAIN", "FOOTPATH"}
CONSTRUCTION = {"ROAD_CC", "COMMUNITY_HALL", "SCHOOL_BUILDING", "BOUNDARY_WALL", "DRAIN",
                "TOILET_BLOCK", "BUS_SHELTER", "HEALTH_BUILDING", "CULVERT", "FOOTPATH",
                "CREMATORIUM", "PLAYGROUND", "POND"}
ROAD_INTERCEPT, ROAD_SLOPE, ROAD_SD = 4.5381, 0.6309, 0.2772


def road_price(length_m: float, rng: random.Random) -> float:
    import math

    return 10 ** (ROAD_INTERCEPT + ROAD_SLOPE * math.log10(length_m) + rng.gauss(0, ROAD_SD))


# templates: (text, reading). Readings: site, noplace, landmark (a temple only as a landmark),
# institution (a school named "... Mandir"), bulk (many units or sites), mast, goods, length
TEMPLATES: dict[str, list[tuple[str, str]]] = {
    "ROAD_CC": [
        ("Construction of CC road from {lm} to {lm2} in village {v}", "site"),
        ("CC road {len} mtr at {v} ward no {wn}", "length"),
        ("Construction of CC Road {len} Mtr from {person} ke ghar se {lm} tak gram {v}", "length"),
        ("{v} gram me {lm} se {lm2} tak CC sadak nirman", "site"),
        ("Construction of cement concrete road near {tm} at {v}", "landmark"),
        ("{tm} ke pas CC road nirman gram {v}", "landmark"),
        ("Construction of CC Road.", "noplace"),
    ],
    "COMMUNITY_HALL": [
        ("Construction of community hall at {v}", "site"),
        ("{v} me samudayik bhawan nirman", "site"),
        ("Construction of community hall near {tm} at village {v}", "landmark"),
        ("Construction of barat ghar at {v} {lm}", "site"),
        ("Construction of Community Hall.", "noplace"),
    ],
    "STREET_LIGHT": [
        ("Installation of solar street light at {v}", "site"),
        ("Installation of high mast light at {lm} {v}", "mast"),
        ("Supply and installation of {n} nos LED street lights in various villages", "bulk"),
        ("Solar light {n} nos at {v}", "bulk"),
        ("Installation of solar light near {tm} {v}", "landmark"),
        ("Installation of Solar Street Light.", "noplace"),
    ],
    "BOREWELL": [
        ("Installation of hand pump at {v} ward no {wn}", "site"),
        ("Boring of tube well at {lm} {v}", "site"),
        ("{v} me hand pump adhishthapan {lm} ke pas", "site"),
        ("Installation of {n} handpumps at various places", "bulk"),
    ],
    "SCHOOL_BUILDING": [
        ("Construction of additional classroom at Govt Primary School {v}", "site"),
        ("Construction of 2 rooms at Saraswati Shishu Mandir {v}", "institution"),
        ("Construction of school building at {v}", "site"),
        ("Construction of Additional Class Room.", "noplace"),
    ],
    "BOUNDARY_WALL": [
        ("Construction of boundary wall of {inst} at {v}", "site"),
        ("{v} me {inst} ki chahardiwari nirman", "site"),
    ],
    "DRAIN": [
        ("Construction of drain from {lm} to {lm2} at {v}", "site"),
        ("{v} me nali nirman {lm} se {lm2} tak", "site"),
        ("Construction of RCC drain {len} mtr at {v}", "length"),
    ],
    "PLAYGROUND": [("Installation of open gym at {lm} {v}", "site"),
                   ("Development of playground at {v}", "site")],
    "WATER_TANK": [("Installation of RO water plant at {lm} {v}", "site"),
                   ("Construction of water tank at {v}", "site")],
    "TOILET_BLOCK": [("Construction of public toilet at {lm} {v}", "site")],
    "BUS_SHELTER": [("Construction of bus shelter at {v} chowk", "site")],
    "HEALTH_BUILDING": [("Construction of health sub centre building at {v}", "site")],
    "LIBRARY": [("Purchase of books for library at Govt High School {v}", "goods"),
                ("Construction of library building at {v}", "site")],
    "COMPUTER": [("Purchase of computers for smart class at Govt High School {v}", "goods")],
    "FURNITURE": [("Supply of furniture (benches and desks) for Govt School {v}", "goods")],
    "AMBULANCE": [("Purchase of ambulance for CHC {v}", "goods")],
    "POND": [("Beautification of pond (talab) at {v}", "site"),
             ("{v} gram me pokhar ka saundaryikaran", "site")],
    "CULVERT": [("Construction of culvert on {lm} road at {v}", "site")],
    "CREMATORIUM": [("Development of shamshan ghat at {v}", "site"),
                    ("Construction of tin shed at kabristan {v}", "site")],
    "FOOTPATH": [("Paver block work in {lm} gali at {v}", "site"),
                 ("Interlocking road at {v} ward no {wn}", "site")],
}
_INSTITUTIONS = ["Govt High School", "Panchayat Bhawan", "kabristan", "shamshan ghat",
                 "Primary Health Centre", "Anganwadi Kendra"]
# readings whose price is not one job at one site
_PRICE_OF = {"goods": {"LIBRARY": 1.0 * LAKH, "COMPUTER": 3.0 * LAKH, "FURNITURE": 1.5 * LAKH,
                       "AMBULANCE": 18.0 * LAKH}}
_LIBRARY_BUILDING = 7.0 * LAKH


@dataclass(frozen=True)
class Label:
    kind: str
    positive: bool = False
    meant: str | None = None                  # engine id meant to catch it
    codes: tuple[str, ...] = ()               # finding codes that count as caught
    group: str | None = None                  # planted group / office


BACKGROUND = Label("BACKGROUND")


@dataclass
class Corpus:
    seed: int
    as_of: date
    works: list[dict]
    labels: dict[str, Label] = field(default_factory=dict)

    def label(self, work_id: str) -> Label:
        return self.labels.get(work_id, BACKGROUND)


@dataclass
class District:
    code: str
    name: str
    state_lgd: str
    state_name: str
    villages: list[str]
    offices: list[str]
    office_weights: list[float]
    mp17: str
    mp18: str
    blocks: list[str]
    bulk_office: str


class Generator:
    """`Generator(seed).build()` -> Corpus. Sizes are small enough for a laptop run in about a
    minute per seed; `small=True` gives a corpus for unit tests."""

    def __init__(self, seed: int = 1, states: int = 5, districts_per_state: int = 10,
                 works_per_district: int = 380, plant: int = 12, small: bool = False):
        if small:
            states, districts_per_state, works_per_district, plant = 2, 4, 160, 4
        self.rng = random.Random(seed)
        self.seed = seed
        self.n_states, self.n_dist = states, districts_per_state
        self.per_district = works_per_district
        self.plant_n = plant
        self.works: list[dict] = []
        self.labels: dict[str, Label] = {}
        self.districts: list[District] = []
        self.rs_mps: dict[str, list[str]] = {}
        self._seq = 0
        self._used_names: set[str] = set()
        self._village_weights: dict[int, list[float]] = {}

    # ------------------------------------------------------------ geography
    def _name(self) -> str:
        for _ in range(200):
            n = self.rng.choice(_A) + self.rng.choice(_B)
            if n not in self._used_names or self.rng.random() < 0.08:
                self._used_names.add(n)
                return n
        return self.rng.choice(_A) + self.rng.choice(_B) + "a"

    def _geography(self) -> None:
        code = 100
        for s in range(self.n_states):
            state_lgd = f"{10 + s}"
            state_name = _STATES[s % len(_STATES)]
            self.rs_mps[state_lgd] = [f"RS Member {state_lgd}-{i}" for i in range(3)]
            for d in range(self.n_dist):
                code += 1
                name = self._name() + (" Nagar" if d % 4 == 0 else "")
                blocks = [self._name() for _ in range(4)]
                offices = ([f"Block Development Officer {b}" for b in blocks]
                           + [f"Executive Engineer RES {name}", f"PWD Division {name}",
                              f"Zilla Parishad {name}", f"Nagar Palika {name}"])
                weights = [1.0 / (i + 1) ** 0.7 for i in range(len(offices))]
                self.rng.shuffle(weights)
                villages = sorted({self._name() + self.rng.choice(("", "", "", " Kalan",
                                                                    " Khurd", " Bujurg"))
                                   for _ in range(240)})
                self.districts.append(District(
                    code=str(code), name=name, state_lgd=state_lgd, state_name=state_name,
                    villages=villages, offices=offices, office_weights=weights,
                    mp17=f"LS Member {code}-17", mp18=f"LS Member {code}-18", blocks=blocks,
                    bulk_office=self.rng.choice(offices)))

    # ------------------------------------------------------------ one work
    def _id(self, mp: str, rec: date) -> str:
        self._seq += 1
        if self.rng.random() < 0.15:
            return f"NOREF-{self.seed:02d}{self._seq:010x}"
        fy = rec.year if rec.month >= 4 else rec.year - 1
        mp_no = zlib.crc32(mp.encode()) % 900 + 100
        return f"WS/SYN{mp_no}/{fy}-{fy + 1}/{self.seed:02d}{self._seq:06d}"

    def _rec_date(self) -> date:
        r = self.rng.random()
        if r < 0.18:                                   # the pre-election rush, Jan-Mar 2024
            return date(2024, 1, 1) + timedelta(days=self.rng.randrange(0, 90))
        span = (AS_OF - START).days
        return START + timedelta(days=self.rng.randrange(0, span))

    @staticmethod
    def _wait_share(age: int) -> float:
        pts = [(0, 1.0), (75, 0.63), (90, 0.585), (120, 0.53), (150, 0.309), (180, 0.251),
               (240, 0.204), (300, 0.148), (365, 0.127), (450, 0.103), (540, 0.042),
               (730, 0.037), (2000, 0.037)]
        for (d0, s0), (d1, s1) in zip(pts, pts[1:], strict=False):
            if age <= d1:
                return s0 + (s1 - s0) * (age - d0) / (d1 - d0)
        return pts[-1][1]

    def _lifecycle(self, rec: date) -> tuple[str, date | None]:
        age = (AS_OF - rec).days
        if self.rng.random() < self._wait_share(age):
            return "RECOMMENDED", None
        days = int(self.rng.lognormvariate(5.8, 0.45))          # median about 330 days
        done = rec + timedelta(days=max(20, days))
        if done > AS_OF or self.rng.random() < 0.28:            # not finished, or not entered
            return "SANCTIONED", None
        return "COMPLETED", done

    def _village(self, d: District) -> str:
        # a few bigger villages carry more works, most carry one or two (as on the portal): the
        # top village holds about 2% of a district's works
        weights = self._village_weights.setdefault(
            len(d.villages), [1.0 / (k + 20) for k in range(len(d.villages))])
        i = self.rng.choices(range(len(d.villages)), weights=weights)[0]
        return d.villages[(i * 7919 + int(d.code)) % len(d.villages)]

    def _fill(self, text: str, d: District, v: str | None = None) -> tuple[str, dict]:
        rng = self.rng
        lm, lm2 = rng.sample(_LANDMARKS, 2)
        slots = {"v": v or self._village(d), "lm": lm, "lm2": lm2,
                 "tm": rng.choice(_TEMPLES), "person": rng.choice(_PEOPLE),
                 "wn": str(rng.randint(1, 18)), "inst": rng.choice(_INSTITUTIONS),
                 "len": str(int(round(rng.lognormvariate(4.5, 0.6) / 10) * 10) or 50),
                 "n": str(rng.choice([5, 8, 10, 12, 15, 20, 25, 30, 40, 50]))}
        out = text
        for k, val in slots.items():
            out = out.replace("{" + k + "}", val)
        return out, slots

    def _price(self, wtype: str, reading: str, slots: dict) -> float:
        rng = self.rng
        share, median, sd = TYPES[wtype]
        import math

        if reading == "length" and wtype == "ROAD_CC":
            return road_price(float(slots["len"]), rng)
        if reading == "length":
            return 10 ** (4.15 + 0.6 * math.log10(float(slots["len"])) + rng.gauss(0, 0.25))
        if reading == "bulk":
            unit = {"STREET_LIGHT": 25_000.0, "BOREWELL": 80_000.0}.get(wtype, 50_000.0)
            return int(slots["n"]) * unit * 10 ** rng.gauss(0, 0.08)
        if reading == "mast":
            return 5.5 * LAKH * 10 ** rng.gauss(0, 0.07)
        if reading == "goods":
            return _PRICE_OF["goods"].get(wtype, median) * 10 ** rng.gauss(0, sd)
        if wtype == "LIBRARY":
            return _LIBRARY_BUILDING * 10 ** rng.gauss(0, 0.25)
        return median * 10 ** rng.gauss(0, sd)

    def _round(self, amount: float, office_bunch: float = 1.0) -> float:
        rng = self.rng
        # amounts pile up just under the Rs 5 and 10 lakh limits (12.1x / 11.5x nationally)
        # calibrated so about 9.5% of all works sit 96-100% under a limit, as on the dashboard
        # tables of 2 Oct 2026 (9.5%; 42.6x more just under Rs 5 lakh than just over)
        if 5.0 * LAKH < amount <= 6.3 * LAKH and rng.random() < min(0.95, 0.45 * office_bunch):
            amount = rng.uniform(4.80, 4.995) * LAKH
        elif 10.0 * LAKH < amount <= 12.5 * LAKH and rng.random() < min(0.95, 0.45 * office_bunch):
            amount = rng.uniform(9.60, 9.99) * LAKH
        r = rng.random()
        if r < 0.33 and amount >= 1.5 * LAKH and not (4.75 * LAKH < amount < 5.0 * LAKH
                                                      or 9.5 * LAKH < amount < 10 * LAKH):
            return float(round(amount / LAKH) * LAKH)
        if r < 0.75:
            return float(round(amount, -3))
        return float(round(amount, -2))

    def _case(self, text: str) -> str:
        r = self.rng.random()
        if r < 0.15:
            return text.upper()
        if r < 0.25:
            return text.lower()
        return text

    def make(self, d: District, wtype: str | None = None, *, template: tuple[str, str] | None
             = None, village: str | None = None, rec: date | None = None, mp: str | None = None,
             office: str | None = None, amount: float | None = None,
             status: tuple[str, date | None] | None = None, label: Label = BACKGROUND,
             case: bool = True) -> dict:
        rng = self.rng
        if wtype is None:
            types = list(TYPES)
            wtype = rng.choices(types, weights=[TYPES[t][0] for t in types])[0]
        tpl = template or rng.choice(TEMPLATES[wtype])
        text, slots = self._fill(tpl[0], d, village)
        rec = rec or self._rec_date()
        if mp is None:
            rs = rng.random() < 0.10
            mp = (rng.choice(self.rs_mps[d.state_lgd]) if rs
                  else (d.mp17 if rec < TERM_17_END else d.mp18))
        office = office or rng.choices(d.offices, weights=d.office_weights)[0]
        if amount is None:
            bunch = self._office_bunch.get(office, 1.0)
            amount = self._round(self._price(wtype, tpl[1], slots), bunch)
        st, done = status or self._lifecycle(rec)
        house = "Rajya Sabha" if mp.startswith("RS ") else "Lok Sabha"
        term = (None if house == "Rajya Sabha"
                else ("17th Lok Sabha" if rec < TERM_17_END else "18th Lok Sabha"))
        fy = rec.year if rec.month >= 4 else rec.year - 1
        w = {"work_id": self._id(mp, rec), "source": "SYNTH", "house": house, "term": term,
             "state_lgd": d.state_lgd, "state_name": d.state_name, "district_lgd": d.code,
             "district_name": d.name, "constituency": f"PC {d.name}", "mp_name": mp,
             "agency_name": office, "fy": f"{fy}-{fy + 1}", "work_type_code": wtype,
             "category": None, "description": self._case(text) if case else text,
             "amount": float(amount), "recommended_date": rec, "completed_date": done,
             "status": st, "quantity": None, "quantity_unit": None,
             "is_outside_constituency": False}
        self.works.append(w)
        if label is not BACKGROUND:
            self.labels[w["work_id"]] = label
        elif tpl[1] == "landmark":
            self.labels[w["work_id"]] = Label("HN_LANDMARK_TEMPLE")
        elif tpl[1] == "institution":
            self.labels[w["work_id"]] = Label("HN_SCHOOL_NAMED_MANDIR")
        elif tpl[1] == "bulk":
            self.labels[w["work_id"]] = Label("HN_BULK_UNITS", meant="statistical",
                                              codes=("COST_ABOVE_PEERS",))
        elif tpl[1] == "noplace" and float(amount) >= 10 * LAKH:
            # a big sum that names no place or size: R12 asks about exactly these, and the team
            # read 28 of 30 such real flags as worth a look. The generator cannot say whether
            # one is a real problem, so it is left out of every count (UNSCORED_*)
            self.labels[w["work_id"]] = Label("UNSCORED_BIG_VAGUE")
        return w

    # ------------------------------------------------------------ background
    def _background(self) -> None:
        rng = self.rng
        for d in self.districts:
            n = max(40, int(rng.gauss(self.per_district, self.per_district * 0.25)))
            for _ in range(n):
                self.make(d)
            # ordinary batches: one MP, one day, one template, several villages
            for _ in range(rng.randint(1, 3)):
                rec = self._rec_date()
                wtype = rng.choice(["STREET_LIGHT", "BOREWELL", "ROAD_CC", "COMMUNITY_HALL"])
                tpl = next(t for t in TEMPLATES[wtype] if t[1] == "site")
                mp = d.mp17 if rec < TERM_17_END else d.mp18
                office = rng.choice(d.offices)
                base = self._price(wtype, "site", {})
                st = self._lifecycle(rec)
                for v in rng.sample(d.villages, rng.randint(3, 6)):
                    self.make(d, wtype, template=tpl, village=v, rec=rec, mp=mp, office=office,
                              amount=self._round(base * rng.uniform(0.97, 1.03)), status=st,
                              label=Label("HN_BATCH_DIFFERENT_VILLAGES", meant="dup_split",
                                          codes=("SPLIT_AT_ONE_SITE",
                                                 "FUNDED_AGAIN_AFTER_COMPLETION",
                                                 "REPEATED_WHILE_OPEN")))
            # bulk entry when the portal opened: the office back-filled finished works
            q3 = [w for w in self.works if w["district_lgd"] == d.code
                  and w["agency_name"] == d.bulk_office
                  and date(2023, 7, 1) <= w["recommended_date"] <= date(2023, 9, 30)]
            for w in q3:
                if rng.random() < 0.45:
                    w["status"] = "COMPLETED"
                    w["completed_date"] = w["recommended_date"] - timedelta(
                        days=rng.randint(20, 500))
                    self.labels[w["work_id"]] = Label("HN_BULK_ENTRY_BACKFILL",
                                                      meant="time_rules",
                                                      codes=("IMPOSSIBLE_TIMELINE",))
            # opposite sides of one road: two works, not a repeat
            v = rng.choice(d.villages)
            rec = self._rec_date()
            for side in ("north", "south"):
                self.make(d, "ROAD_CC", template=(
                    f"Construction of CC road {side} side of {{lm}} at village {v}", "site"),
                    village=v, rec=rec + timedelta(days=rng.randint(0, 200)),
                    label=Label("HN_OPPOSITE_SIDES", meant="dup_split",
                                codes=("REPEATED_WHILE_OPEN", "FUNDED_AGAIN_AFTER_COMPLETION")))

    # ------------------------------------------------------------ planting
    def _pick(self, cond, n: int) -> list[dict]:
        pool = [w for w in self.works if w["work_id"] not in self.labels and cond(w)]
        return self.rng.sample(pool, min(n, len(pool)))

    def _district(self, w: dict) -> District:
        return next(d for d in self.districts if d.code == w["district_lgd"])

    def _reword(self, text: str, village: str | None) -> str:
        rng = self.rng
        swaps = [("Construction of ", rng.choice(["Constructing ", "Nirman of ", "Constn. of "])),
                 ("construction of ", "constructing "), ("CC road", "cement concrete road"),
                 ("CC Road", "C.C. Road"), ("community hall", "samudayik bhawan"),
                 ("samudayik bhawan", "community hall"), ("Installation of ", "Installing "),
                 (" at ", rng.choice([" in ", " at village ", " gram "])),
                 (" nirman", " ka nirman karya"), ("hand pump", "handpump"),
                 ("boundary wall", "chahardiwari"), ("drain", "nala")]
        out = text
        for a, b in rng.sample(swaps, len(swaps)):
            if a in out and rng.random() < 0.7:
                out = out.replace(a, b, 1)
        if village and village in out and rng.random() < 0.5:
            out = out.replace(village, spelling_variant(village, rng))
        if out == text:
            out = text + " work"
        return out

    def _plant(self) -> None:
        rng, n = self.rng, self.plant_n

        def site_work(w):
            return (w["work_type_code"] in CONSTRUCTION and any(
                v in w["description"] for v in self._district(w).villages))

        # COST: one job at one site, its amount raised 3x, 5x or 10x
        for times in (3, 5, 10):
            for w in self._pick(lambda w: site_work(w) and 1.5 * LAKH <= w["amount"] <= 8 * LAKH
                                and not any(c.isdigit() for c in w["description"]), n):
                w["amount"] = float(round(w["amount"] * times, -2))
                self.labels[w["work_id"]] = Label(f"COST_X{times}", True)   # record only
        # COST with a small stated scope: "one high mast light" at ten times its price
        for _ in range(n):
            d = rng.choice(self.districts)
            v = rng.choice(d.villages)
            tpl = rng.choice([
                ("Installation of one high mast light at {lm} {v}", "mast", 5.5 * LAKH),
                ("Installation of 1 no. solar street light at {v}", "site", 0.9 * LAKH),
                ("Construction of single room at Govt Primary School {v}", "site", 4.0 * LAKH),
                ("Installation of one hand pump at {v} ward no {wn}", "site", 0.9 * LAKH)])
            wtype = {"mast": "STREET_LIGHT"}.get(tpl[1]) or (
                "STREET_LIGHT" if "light" in tpl[0] else
                "SCHOOL_BUILDING" if "room" in tpl[0] else "BOREWELL")
            self.make(d, wtype, template=(tpl[0], tpl[1]), village=v,
                      amount=float(round(tpl[2] * rng.uniform(9, 12), -3)),
                      label=Label("COST_SMALL_SCOPE_X10", True))          # record only

        # REPEATS: the same work filed again, reworded, often with the village spelt otherwise
        for kind, cond in (("REPEAT_AFTER_DONE", lambda w: w["status"] == "COMPLETED"
                            and w["completed_date"] and w["completed_date"] < AS_OF
                            - timedelta(days=70)),
                           ("REPEAT_WHILE_OPEN", lambda w: w["status"] == "SANCTIONED"
                            and w["recommended_date"] < AS_OF - timedelta(days=120))):
            for w in self._pick(lambda w, c=cond: site_work(w) and c(w), n):
                d = self._district(w)
                village = next((v for v in d.villages if v in w["description"]), None)
                start = w["completed_date"] if kind == "REPEAT_AFTER_DONE" else \
                    w["recommended_date"]
                rec = min(AS_OF - timedelta(days=5),
                          start + timedelta(days=rng.randint(60, 360)))
                mp = rng.choice(self.rs_mps[d.state_lgd]) if rng.random() < 0.3 else None
                self.labels[w["work_id"]] = Label("REPEAT_ORIGINAL", group=w["work_id"])
                self.make(d, w["work_type_code"],
                          template=(self._reword(w["description"], village), "site"),
                          rec=rec, mp=mp, amount=float(round(w["amount"] * rng.uniform(0.9,
                                                                                         1.1), -2)),
                          label=Label(kind, True, group=w["work_id"]), case=False)  # words

        # SPLITS at one site: one Rs 12-20 lakh job filed as 3-4 pieces just under Rs 5 lakh
        for g in range(max(2, n // 2)):
            d = rng.choice(self.districts)
            v = rng.choice(d.villages)
            wtype = rng.choice(["ROAD_CC", "COMMUNITY_HALL", "DRAIN", "BOUNDARY_WALL"])
            tpl = next(t for t in TEMPLATES[wtype] if t[1] == "site")
            text, _ = self._fill(tpl[0], d, v)
            rec, office = self._rec_date(), rng.choice(d.offices)
            mp = d.mp17 if rec < TERM_17_END else d.mp18
            st = self._lifecycle(rec)
            for _ in range(rng.choice((3, 3, 4))):
                self.make(d, wtype, template=(text, "site"), rec=rec, mp=mp, office=office,
                          amount=float(round(rng.uniform(4.6, 4.99) * LAKH, -2)), status=st,
                          label=Label("SPLIT_SAME_SITE", True, "dup_split",
                                      ("SPLIT_JUST_UNDER_LIMIT",), group=f"S{g}"), case=False)

        # SPLITS into stretches: one road cut into numbered parts, each just under Rs 5 lakh
        for g in range(max(2, n // 2)):
            d = rng.choice(self.districts)
            v = rng.choice(d.villages)
            lm, lm2 = rng.sample(_LANDMARKS, 2)
            rec, office = self._rec_date(), rng.choice(d.offices)
            mp = d.mp17 if rec < TERM_17_END else d.mp18
            st = self._lifecycle(rec)
            parts = rng.choice((3, 3, 4))
            style = rng.choice(("part", "phase", "chainage"))
            step = rng.choice((150, 200, 250))
            for i in range(parts):
                if style == "part":
                    text = f"Construction of CC road from {lm} to {lm2} at {v} part-{i + 1}"
                elif style == "phase":
                    roman = ("I", "II", "III", "IV")[i]
                    text = f"CC road from {lm} to {lm2} in village {v} phase {roman}"
                else:
                    text = (f"Construction of CC road at {v} from {lm} to {lm2} "
                            f"chainage {i * step} to {(i + 1) * step} m")
                self.make(d, "ROAD_CC", template=(text, "site"),
                          rec=rec + timedelta(days=rng.randint(0, 20)), mp=mp, office=office,
                          amount=float(round(rng.uniform(4.6, 4.99) * LAKH, -2)), status=st,
                          label=Label("SPLIT_STRETCHES", True, "dup_split",
                                      ("SPLIT_JUST_UNDER_LIMIT",), group=f"T{g}"), case=False)

        # REPAIR SOON AFTER BUILT: a new asset "repaired" within months of completion
        for w in self._pick(lambda w: site_work(w) and w["status"] == "COMPLETED"
                            and w["completed_date"] and w["completed_date"]
                            < AS_OF - timedelta(days=60), n):
            d = self._district(w)
            text = w["description"]
            low = text.lower()
            if low.startswith("construction of "):
                text = rng.choice(["Repair of ", "Renovation of ", "Marammat of "]) + \
                    text[len("construction of "):]
            elif " nirman" in low:
                text = text.replace(" nirman", " marammat").replace(" NIRMAN", " MARAMMAT")
            else:
                text = "Repair of " + text
            self.labels[w["work_id"]] = Label("REPAIR_ORIGINAL", group=w["work_id"])
            rec = min(AS_OF - timedelta(days=3),
                      w["completed_date"] + timedelta(days=rng.randint(30, 300)))
            self.make(d, w["work_type_code"], template=(text, "site"), rec=rec,
                      amount=float(round(w["amount"] * rng.uniform(0.3, 0.8), -3)),
                      label=Label("REPAIR_SOON_AFTER_BUILT", True, group=w["work_id"]),
                      case=False)        # words alone; a declared rebuild is REBUILT_SOON below
        # ... and its look-alike: a repair of a different asset, or years later
        for w in self._pick(lambda w: site_work(w) and w["status"] == "COMPLETED", n // 2):
            d = self._district(w)
            other = rng.choice([v for v in d.villages if v not in w["description"]])
            self.make(d, w["work_type_code"],
                      template=(f"Repair of community hall at {other}", "site"),
                      label=Label("HN_REPAIR_ELSEWHERE", meant="dup_split",
                                  codes=("REPAIR_SOON_AFTER_BUILT",)))

        # GUIDELINE breaches. T125 (four agents): prohibited works, the outside-area ceiling
        # and a big sum that names nothing are no longer checked (planted, meant for no
        # engine); the dates stay Time & Rules' (R13 built in days, R06 impossible dates)
        for _ in range(n):
            d = rng.choice(self.districts)
            tpl = rng.choice(["Construction of {deity} mandir at {v}",
                              "{v} me {deity} mandir nirman",
                              "Construction of shed in {deity} mandir premises at {v}",
                              "Construction of boundary wall of jama masjid at {v}"])
            text = tpl.replace("{deity}", rng.choice(_DEITIES))
            self.make(d, rng.choice(["COMMUNITY_HALL", "BOUNDARY_WALL"]),
                      template=(text, "site"),
                      label=Label("RULE_TEMPLE", True))          # not checked (T125)
        for w in self._pick(lambda w: w["work_type_code"] in CONSTRUCTION, max(3, n // 2)):
            w["is_outside_constituency"] = True
            w["amount"] = float(rng.choice((30, 40, 50)) * LAKH)
            self.labels[w["work_id"]] = Label("RULE_OUTSIDE_CEILING", True)  # not checked
        for _ in range(max(3, n // 2)):
            d = rng.choice(self.districts)
            wtype = rng.choice(["COMMUNITY_HALL", "SCHOOL_BUILDING", "ROAD_CC"])
            text = {"COMMUNITY_HALL": "Construction of community hall",
                    "SCHOOL_BUILDING": "Construction of school building",
                    "ROAD_CC": "Construction of road"}[wtype]
            self.make(d, wtype, template=(text, "noplace"),
                      amount=float(rng.choice((30, 40, 60)) * LAKH),
                      label=Label("RULE_BIG_VAGUE", True))       # not checked (T125)
        for w in self._pick(lambda w: w["work_type_code"] in CONSTRUCTION
                            and w["status"] == "COMPLETED" and 5 * LAKH <= w["amount"] <= 15 * LAKH
                            and w["recommended_date"] >= date(2024, 7, 1), max(3, n // 2)):
            w["completed_date"] = w["recommended_date"] + timedelta(days=rng.randint(1, 10))
            self.labels[w["work_id"]] = Label("RULE_BUILT_IN_DAYS", True, "time_rules",
                                              ("BUILT_IN_DAYS",))
        for w in self._pick(lambda w: w["status"] == "COMPLETED"
                            and w["recommended_date"] >= date(2024, 10, 1), max(3, n // 2)):
            w["completed_date"] = w["recommended_date"] - timedelta(days=rng.randint(30, 200))
            self.labels[w["work_id"]] = Label("RULE_DATES_IMPOSSIBLE", True, "time_rules",
                                              ("IMPOSSIBLE_TIMELINE",))

        # OFFICES: one that prices most works just under Rs 5 lakh; one that closes works in days
        offices = [(d, o) for d in self.districts for o in d.offices]
        rng.shuffle(offices)
        hug = 0
        for d, o in offices:
            if hug >= max(2, n // 4):
                break
            # as the real extremes on the dashboard tables (one office priced 130 of its 141
            # works just under Rs 5 lakh, another 60 of 60): most of the office's works
            everything = [w for w in self.works if w["agency_name"] == o
                          and w["district_lgd"] == d.code]
            mine = [w for w in everything if w["work_id"] not in self.labels
                    and 2.0 * LAKH <= w["amount"] <= 12 * LAKH]
            if len(mine) < 25 or len(mine) < 0.6 * len(everything):
                continue
            hug += 1
            for w in mine:
                if rng.random() < 0.85:
                    w["amount"] = float(round(rng.uniform(4.80, 4.995) * LAKH, -2))
                    self.labels[w["work_id"]] = Label("OFFICE_PRICES_AT_LIMIT", True,
                                                      group=f"{d.code}|{o}")  # not checked
        fast = 0
        for d, o in reversed(offices):
            if fast >= max(2, n // 4):
                break
            mine = [w for w in self.works if w["agency_name"] == o and w["district_lgd"] == d.code
                    and w["work_id"] not in self.labels
                    and w["work_type_code"] in CONSTRUCTION and w["status"] == "COMPLETED"
                    and w["recommended_date"] >= date(2023, 10, 1)]
            if len(mine) < 12:
                continue
            fast += 1
            for w in mine:
                if rng.random() < 0.6:
                    w["completed_date"] = w["recommended_date"] + timedelta(
                        days=rng.randint(2, 20))
                    # each work is Time & Rules' to find (R13, built in days; synthetic works
                    # carry no sanction date, so R14 cannot fire here)
                    self.labels[w["work_id"]] = Label("OFFICE_CLOSES_IN_DAYS", True,
                                                      "time_rules", ("BUILT_IN_DAYS",),
                                                      group=f"{d.code}|{o}")

        # a big project that says how big it is: not a mark-up
        for _ in range(n):
            d = rng.choice(self.districts)
            v = rng.choice(d.villages)
            self.make(d, "COMMUNITY_HALL", template=(
                f"Construction of two storey community hall with 12 rooms, kitchen and toilet "
                f"block at {v}", "site"), amount=float(rng.choice((35, 45, 60)) * LAKH),
                label=Label("HN_BIG_STATED_SCOPE", meant="statistical",
                            codes=("COST_ABOVE_PEERS", "SMALL_SCOPE_FAR_ABOVE")))

        # T100: MAP PINS on the cost estimate form (planted last, so the office habits above
        # draw the same works as before). An original sanctioned work of a point asset
        # gets a form with its pin; a later work with its own form is planted beside it.
        def pin(d: District, key: str) -> tuple[float, float]:
            h = zlib.crc32(f"{d.code}:{key}".encode())
            return 21.0 + (h % 600) / 100, 76.0 + (h // 600 % 800) / 100

        def form(wtype: str, lat: float, lon: float, nature: str = "new",
                 earlier: str | None = None) -> dict:
            work = {"work_type": wtype, "nature": nature}
            if earlier:
                work["earlier_work_id"] = earlier
            return {"work": work, "sites": [{"location": {"lat": lat, "lon": lon}}]}

        def pinned(w):
            return (site_work(w) and w["work_type_code"] not in LINEAR and "cost_form" not in w
                    and w["status"] in ("SANCTIONED", "COMPLETED"))

        def done_lately(w):
            return (pinned(w) and w["status"] == "COMPLETED" and w["completed_date"]
                    and w["completed_date"] < AS_OF - timedelta(days=60))

        for kind, cond, k in (("PIN_REPEAT", pinned, n), ("REBUILT_SOON", done_lately, n),
                              ("HN_PIN_OTHER_ASSET", pinned, n // 2),
                              ("HN_PIN_NEXT_DOOR", pinned, n // 2),
                              ("HN_DECLARED_CONTINUATION", pinned, n // 2)):
            for w in self._pick(cond, k):
                d = self._district(w)
                lat, lon = pin(d, w["work_id"])
                w["cost_form"] = form(w["work_type_code"], lat, lon)
                self.labels[w["work_id"]] = Label("PIN_ORIGINAL", group=w["work_id"])
                start = w["completed_date"] or w["recommended_date"]
                rec = min(AS_OF - timedelta(days=3), start + timedelta(days=rng.randint(30, 300)))
                wtype, metres = w["work_type_code"], rng.uniform(0, 45)
                nature, earlier = "new", None
                text = self._reword(w["description"], None)
                if kind == "HN_PIN_OTHER_ASSET":        # a borewell beside the hall
                    wtype, text = "BOREWELL", rng.choice(TEMPLATES["BOREWELL"])[0]
                elif kind == "HN_PIN_NEXT_DOOR":        # the same kind, 80-300 m away
                    metres = rng.uniform(80, 300)
                elif kind == "HN_DECLARED_CONTINUATION":
                    nature, earlier = "continuation", w["work_id"]
                elif kind == "REBUILT_SOON":
                    nature, earlier = "reconstruction", w["work_id"]
                code = ("REBUILT_SOON_AFTER_COMPLETION" if kind == "REBUILT_SOON"
                        else "SANCTIONED_WORK_AT_THIS_SITE")
                label = (Label(kind, True, "dup_split", (code,), group=w["work_id"])
                         if not kind.startswith("HN_") else
                         Label(kind, meant="dup_split", codes=("SANCTIONED_WORK_AT_THIS_SITE",
                                                               "REBUILT_SOON_AFTER_COMPLETION")))
                new = self.make(d, wtype, template=(text, "site"), rec=rec, label=label,
                                case=False)
                new["cost_form"] = form(wtype, lat + metres / 111_195, lon, nature, earlier)

    # ------------------------------------------------------------ build
    def build(self) -> Corpus:
        self._office_bunch: dict[str, float] = {}
        self._geography()
        for d in self.districts:
            for o in d.offices:
                self._office_bunch[o] = self.rng.lognormvariate(0, 0.25)
        self._background()
        self._plant()
        self.rng.shuffle(self.works)
        return Corpus(seed=self.seed, as_of=AS_OF, works=self.works, labels=self.labels)
