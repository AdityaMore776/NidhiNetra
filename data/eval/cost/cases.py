r"""The Cost agent's eval cases (T167): honest estimates, honest edge cases and frauds, labelled.

Plan: docs/plans/T167-cost-eval.md. Every case is a filing of the website's work intelligence form
(PSWIF v1.1) by a made-up agency in the real district of Jaunpur, judged by the real Cost agent
against a district of honest filings by other agencies (the world). Nothing here is a real agency,
person or work.

A case carries its truth and the levels its label allows:

  truth    honest  an ordinary honest estimate
           edge    honest, but unusual: it looks like a problem on some measure
           fraud   a padding scheme an agency could try
  ideal    the level the label wants (levels.py: fits, edge, check, ask)
  allowed  the levels that pass. A fraud never allows fits or edge (that is a fraud excused);
           an honest case never allows ask
  pair     look-alike pairs: the same surface numbers, one honest and one a fraud
  scope    "cost", or "other" for a fraud the estimate cannot show (another agent's job: listed,
           never counted as coverage)

Each case runs in two worlds (WORLDS): the other agencies' honest rates a tight +-4% apart, and a
wide +-10%. The thresholds rest on the CPWD Works Manual, para 20.4.3.2: up to 5% over the
justified rates may be ignored, up to 10% allowed with recorded reasons, beyond that a tender
should not be accepted.
"""

from __future__ import annotations

import copy
import random
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(ROOT / "data" / "trial"))
sys.path.insert(0, str(ROOT / "apps" / "engine"))
import work_form_examples as wf  # noqa: E402

from drishti import records  # noqa: E402
from drishti.agents.contract import AgentResult  # noqa: E402
from drishti.agents.cost_estimate import agent as cost  # noqa: E402
from drishti.agents.cost_estimate import rates  # noqa: E402
from drishti.agents.cost_estimate.rates import RateIndex  # noqa: E402
from drishti.cost_form import pswif  # noqa: E402
from drishti.pipeline.orchestrator import Context  # noqa: E402

AS_OF = date(2026, 10, 2)
PLACE = {"district_lgd": "194", "state_lgd": "09", "state_name": "Uttar Pradesh",
         "district_name": "Jaunpur"}
# other districts of the state, for the state's own rates (made-up codes, never joined to maps)
OTHER_DISTRICTS = [("9101", "District A"), ("9102", "District B"), ("9103", "District C"),
                   ("9104", "District D"), ("9105", "District E")]
LEVELS = ("fits", "edge", "check", "ask")
STATE_AGENCIES = ["Awadh Path Nirman", "Purvanchal Sadak Sewa", "Doaba Infra Cell",
                  "Rohilkhand Works", "Bundelkhand Nirman", "Tarai Rural Engineering"]
AGENCY = "Nirman Seva Agency"          # the filing agency of every case (not in the background)


# ---- the world ------------------------------------------------------------------------------------

@dataclass
class World:
    name: str
    spread: float                    # the honest agencies' own rates: +- this around the fair rate
    background: list[dict]           # other agencies' filings: Jaunpur's and the state's
    as_of: date = AS_OF
    centre: dict = field(default_factory=dict)   # material -> fair rate / generator's rate


# the generator's rates (work_form_examples.road / hall), by the line's opening words
PREFIX = {"Cement": "cement", "Coarse sand": "sand", "Stone aggregate": "aggregate",
          "WBM": "granular_base", "TMT steel": "steel_rebar", "Bricks": "brick",
          "Vitrified": "tiles"}
TEMPLATE = {"cement": 380.0, "sand": 1800.0, "aggregate": 2100.0, "granular_base": 1450.0,
            "steel_rebar": 68.0, "brick": 8.0, "tiles": 650.0, "labour_mason": 750.0,
            "labour_beldar": 420.0}


def _centre(bg: list[dict]) -> dict:
    index = RateIndex.build([records.work(w) for w in bg])
    out = {}
    for mid, base in TEMPLATE.items():
        found, _gap = index.price(PLACE["district_lgd"], "uttar pradesh", mid,
                                  rates.agency_key(AGENCY), "EV-CASE", AS_OF)
        if found:
            out[mid] = found[0] / base
    return out


def _m(days: int) -> date:
    return AS_OF - timedelta(days=days)


QTY_NOISE = 0.04       # honest agencies' quantities differ a few % (their own analysis of rates)
DAYS_NOISE = 0.15      # and their crews' person-days more (productivity, the season)


def _noisy(p: dict, rng: random.Random, line_sd: float) -> dict:
    """An honest agency's own small differences, line by line: rates, quantities, crew days."""
    for k in list(p):
        if k.startswith("boq_rate_"):
            p[k] = f"{float(p[k]) * (1 + rng.gauss(0, line_sd)):.0f}"
        elif k.startswith("boq_qty_"):
            p[k] = f"{float(p[k]) * rng.uniform(1 - QTY_NOISE, 1 + QTY_NOISE):.2f}"
        elif k.startswith("lab_days_"):
            p[k] = f"{max(0.5, float(p[k]) * rng.uniform(1 - DAYS_NOISE, 1 + DAYS_NOISE)):.1f}"
    return finish(p)


def build_world(name: str, spread: float, seed: int = 7) -> World:
    """Honest roads and halls by five other agencies in Jaunpur, and honest roads by five agencies
    in other districts of the state (the state's rates)."""
    rng = random.Random(seed)
    bg: list[dict] = []
    agencies = wf.AG[5:10]
    for i in range(10):                                   # Jaunpur roads, last five months
        ag = agencies[i % 5]
        bias = (-spread, -spread / 2, 0.0, spread / 2, spread)[i % 5]
        p = wf.road(f"EV-BG-R{i}", ag, wf.BG_VILLAGES[i % 7], 20 + i, _m(150 - 12 * i),
                    _m(110 - 12 * i), length=220 + 35 * i, jitter=bias)
        bg.append(_work(_noisy(p, rng, spread / 4)))
    for i in range(6):                                    # Jaunpur halls
        ag = agencies[i % 5]
        bias = (-spread, -spread / 2, 0.0, spread / 2, spread)[i % 5]    # each agency's own
        p = wf.hall(f"EV-BG-H{i}", ag, wf.BG_VILLAGES[i % 7], 40 + i, _m(140 - 15 * i),
                    _m(100 - 15 * i), area=140 + 20 * i)
        scale(p, 1 + bias)
        bg.append(_work(_noisy(p, rng, spread / 4)))
    for i in range(15):                                   # the state: other districts' roads
        code, dname = OTHER_DISTRICTS[i % 5]
        ag = STATE_AGENCIES[i % 6]
        bias = rng.uniform(-spread, spread)
        p = wf.road(f"EV-ST-R{i}", ag, f"Gaon {i}", 60 + i, _m(160 - 9 * i), _m(120 - 9 * i),
                    length=250 + 20 * i, jitter=bias, district=dname)
        w = _work(_noisy(p, rng, spread / 4))
        w.update(district_lgd=code, district_name=dname)
        bg.append(w)
    return World(name, spread, bg, centre=_centre(bg))


WORLDS = {"tight": (0.04, 7), "wide": (0.10, 11)}


# ---- editing a filing -----------------------------------------------------------------------------

def _work(p: dict) -> dict:
    w = pswif.to_work(p, today=AS_OF, status="RECOMMENDED")
    w.update(PLACE)
    if p.get("district") and p["district"] != PLACE["district_name"]:
        w["district_name"] = p["district"]
    return w


def rows(p: dict) -> list[int]:
    return sorted(int(k.removeprefix("boq_desc_")) for k in p if k.startswith("boq_desc_"))


def find(p: dict, start: str) -> int:
    return next(n for n in rows(p) if p[f"boq_desc_{n}"].startswith(start))


def scale(p: dict, f: float, only: tuple[str, ...] | None = None) -> dict:
    """Every BOQ line's rate (or those whose description starts with one of `only`) times f."""
    for n in rows(p):
        if only is None or p[f"boq_desc_{n}"].startswith(only):
            p[f"boq_rate_{n}"] = f"{float(p[f'boq_rate_{n}']) * f:.2f}"
    return p


def add_line(p: dict, desc: str, unit: str, qty: float, rate: float, source: str,
             just: str = "") -> dict:
    n = max(rows(p)) + 1
    p.update({f"boq_code_{n}": "", f"boq_desc_{n}": desc, f"boq_unit_{n}": unit,
              f"boq_qty_{n}": f"{qty:g}", f"boq_rate_{n}": f"{rate:g}",
              f"boq_source_{n}": source, f"boq_measure_ref_{n}": f"MB p.{n}",
              f"boq_just_{n}": just})
    return p


def lab(p: dict, trade: str, f: float, days_f: float = 1.0) -> dict:
    for k in [k for k in p if k.startswith("lab_trade_") and p[k] == trade]:
        n = k.removeprefix("lab_trade_")
        p[f"lab_rate_{n}"] = f"{float(p[f'lab_rate_{n}']) * f:.0f}"
        p[f"lab_days_{n}"] = f"{float(p[f'lab_days_{n}']) * days_f:g}"
    return p


def lines_total(p: dict) -> float:
    return wf.estimate_total(p)


def finish(p: dict, mp_x: float | None = 1.0, mp: float | None = None) -> dict:
    """The form's totals from its lines, the MP's amount `mp_x` times the estimate (or `mp`)."""
    total = lines_total(p) + float(p.get("lumpsum_components") or 0) \
        + float(p.get("other_charges") or 0)
    p["technical_estimate"] = f"{total:.2f}"
    p["mplads_share"] = f"{total:.0f}"
    if mp is not None:
        p["mp_recommended_amount"] = f"{mp:.0f}"
    elif mp_x is not None:
        p["mp_recommended_amount"] = f"{round(total * mp_x, -3):.0f}"
    return p


# ---- running the agent ----------------------------------------------------------------------------

def assess(world: World, p: dict, background: list[dict] | None = None) -> AgentResult:
    """The Cost agent on filing `p`, the rate index holding the world's filings and this one,
    exactly as the live check builds it (POST /work-form/check)."""
    work = records.work(_work(p))
    bg = world.background if background is None else background
    index = RateIndex.build([records.work(w) for w in bg if w["work_id"] != work["work_id"]]
                            + [work])
    ctx = Context(stats=None, as_of=world.as_of, data={"rates": index})
    return cost.assess(work, ctx)


# ---- the cases ------------------------------------------------------------------------------------

@dataclass
class Case:
    id: str
    family: str
    truth: str                      # honest | edge | fraud
    ideal: str
    allowed: tuple[str, ...]
    story: str
    why: str
    build: Callable[[World], dict]
    background: Callable[[World], list[dict]] | None = None
    pair: str | None = None
    scope: str = "cost"
    tags: list[str] = field(default_factory=list)

    def run(self, world: World) -> AgentResult:
        p = self.build(world)
        bg = self.background(world) if self.background else None
        return assess(world, p, bg)


def road(w: World, ref: str = "EV-CASE", length: float = 300, width: float = 3.5, **kw) -> dict:
    """An honest road at the world's own fair rates (rate_up / cement_x / labour_x pad it)."""
    p = wf.road(ref, AGENCY, "Bhawanipur", 0, _m(30), None, length=length, width=width, **kw)
    n = find(p, "Concrete mixer")                 # plant hire scales with the work
    p[f"boq_qty_{n}"] = f"{max(3, round(30 * length * width / 1050))}"
    return finish(centre(p, w))


def hall(w: World, ref: str = "EV-CASE", area: float = 180, **kw) -> dict:
    p = wf.hall(ref, AGENCY, "Kusumi", 1, _m(30), None, area=area, **kw)
    return finish(centre(p, w))


def centre(p: dict, w: World) -> dict:
    """Every line moved from the generator's template rate to the fair rate the agent measures in
    this world, so "+12%" in a case is 12% above the world's own fair rate."""
    for n in rows(p):
        for start, mid in PREFIX.items():
            if p[f"boq_desc_{n}"].startswith(start) and mid in w.centre:
                p[f"boq_rate_{n}"] = f"{float(p[f'boq_rate_{n}']) * w.centre[mid]:.2f}"
    for k in [k for k in p if k.startswith("lab_trade_")]:
        f = w.centre.get(f"labour_{p[k]}")
        if f:
            n = k.removeprefix("lab_trade_")
            p[f"lab_rate_{n}"] = f"{float(p[f'lab_rate_{n}']) * f:.0f}"
    return p


def lights(each: float, mp: float | None = None, spec: str | None = None, **kw) -> dict:
    p = wf.lights("EV-CASE", AGENCY, "Nayagaon", 2, _m(30), each,
                  mp if mp is not None else each * 10, **kw)
    if spec:
        p["boq_desc_1"] = spec
    return finish(p, mp_x=None)


HONEST, EDGE, FRAUD = "honest", "edge", "fraud"
OK = ("fits", "edge")                 # what an honest case may get
OK_SOFT = ("fits", "edge", "check")   # an honest case resting on a claim nobody has verified
FLAG = ("check", "ask")               # what a fraud must get


def _honest_population() -> list[Case]:
    out = []
    for s in range(12):
        def build(w: World, s=s) -> dict:
            rng = random.Random(1000 + s)
            p = road(w, length=rng.choice((180, 240, 300, 420, 560)),
                     width=rng.choice((3.0, 3.5, 3.75)),
                     jitter=rng.uniform(-w.spread / 2, w.spread / 2))
            return finish(_noisy(p, rng, 0.03))
        out.append(Case(f"honest_road_{s:02d}", "honest population", HONEST, "fits", OK,
                        "An honest CC road: size, quantities and rates as other agencies file.",
                        "Its own rates within half the honest spread of the district's, line "
                        "noise 3%.", build))
    for s in range(4):
        def build(w: World, s=s) -> dict:
            rng = random.Random(2000 + s)
            p = hall(w, area=rng.choice((120, 160, 200, 260)))
            scale(p, 1 + rng.uniform(-w.spread / 2, w.spread / 2))
            return finish(_noisy(p, rng, 0.03))
        out.append(Case(f"honest_hall_{s:02d}", "honest population", HONEST, "fits", OK,
                        "An honest community hall.", "Rates within the district's honest "
                        "spread.", build))
    return out


def cases() -> list[Case]:
    c: list[Case] = _honest_population()

    def add(*a, **k):
        c.append(Case(*a, **k))

    # ---- honest noise: how honest forms differ in writing -------------------------------------
    def hindi(w):
        p = road(w)
        for start, txt in (("Cement", "सीमेंट (ओपीसी 43)"), ("Coarse sand", "मौरंग / बालू"),
                           ("Stone aggregate", "गिट्टी 20 मिमी")):
            p[f"boq_desc_{find(p, start)}"] = txt
        return finish(p)
    add("noise_hindi", "honest noise", HONEST, "fits", OK, "Items written in Hindi.",
        "The same road; the words differ.", hindi)

    def kg(w):
        p = road(w)
        n = find(p, "Cement")
        p[f"boq_qty_{n}"] = f"{float(p[f'boq_qty_{n}']) * 50:g}"
        p[f"boq_rate_{n}"] = f"{float(p[f'boq_rate_{n}']) / 50:.2f}"
        p[f"boq_unit_{n}"] = "kg"
        return finish(p)
    add("noise_cement_kg", "honest noise", HONEST, "fits", OK, "Cement in kg, not bags.",
        "Same quantity, another unit.", kg)

    def split(w):
        p = road(w)
        n = find(p, "Stone aggregate")
        q = float(p[f"boq_qty_{n}"])
        p[f"boq_qty_{n}"] = f"{q / 2:g}"
        add_line(p, "Stone aggregate 20 mm (second lot)", "cum", q / 2,
                 float(p[f"boq_rate_{n}"]), "District recent rates")
        return finish(p)
    add("noise_split_line", "honest noise", HONEST, "fits", OK, "One line split in two lots.",
        "Same quantity and rate in two lines.", split)

    def gst(w):
        p = road(w)
        p["tax_treatment"] = "Added separately"
        p["other_charges"] = f"{lines_total(p) * 0.18:.0f}"
        return finish(p)
    add("noise_gst_18", "honest noise", HONEST, "fits", OK, "GST 18% added separately as "
        "other charges.", "The tax the rates leave out.", gst)

    def sundries(w):
        p = road(w)
        p["lumpsum_components"] = f"{lines_total(p) * 0.02:.0f}"
        return finish(p)
    add("noise_sundries_2pc", "honest noise", HONEST, "fits", OK, "A 2% lump sum for sundries.",
        "CPWD estimates carry small lump sums.", sundries)

    def rounded(w):
        p = road(w)
        for n in rows(p):
            r = float(p[f"boq_rate_{n}"])
            p[f"boq_rate_{n}"] = f"{(int(r / 50) + 1) * 50:g}"
        return finish(p)
    add("noise_rounded_up", "honest noise", HONEST, "fits", OK, "Every rate rounded up to the "
        "next Rs 50.", "Rounding, a few % at most.", rounded)

    def cheap(w):
        return finish(scale(road(w), 0.85))
    add("honest_cheap", "honest noise", HONEST, "fits", OK, "Rates 15% below the district's.",
        "A low estimate is no price question (it may run short: a note).", cheap)

    def two_sites(w):
        p = road(w, length=180)
        return finish(p)
    add("honest_short_road", "honest noise", HONEST, "fits", OK, "A short honest road (180 m).",
        "Small, honest.", two_sites)

    # ---- edge cases: honest, but unusual ---------------------------------------------------------
    add("edge_top_of_range", "edge: rates", EDGE, "edge", OK,
        "Every material priced 7% above the district's middle rate.",
        "Within CPWD's 10% for justified rates with reasons; agencies here charge up to +4-10%.",
        lambda w: finish(road(w, rate_up=1.07)), pair="pad_7_vs_12")
    add("edge_price_rise", "edge: rates", EDGE, "edge", OK,
        "Filed after a price rise: materials 9% above the others' forms of 3-5 months ago.",
        "Prices move; within CPWD's 10%.", lambda w: finish(road(w, rate_up=1.09)))
    add("edge_small_road_12pc", "edge: small work", EDGE, "edge", OK_SOFT,
        "A 40 m road with every material 12% above the district: small orders cost more.",
        "The same +12% as the fraud below, on Rs 1.6 lakh: the extra is about Rs 15,000.",
        lambda w: finish(road(w, length=40, rate_up=1.12)), pair="small_vs_big_12")

    def hilly(w):
        p = road(w, rate_up=1.18, terrain="Hilly / steep", site_access="Foot / manual carry required",
                 motorable_access_distance_m="800")
        return finish(p)
    add("edge_hilly_remote", "edge: site", EDGE, "check", OK_SOFT,
        "A hilly site 800 m from the motorable road: materials carried by head-load, 18% above "
        "the district's plains rates.",
        "Carriage is real cost (CPWD adds cost indices for hill areas), but the terrain is the "
        "agency's word until the site video shows it: at most 'check this'.", hilly,
        pair="hilly_vs_claimed")

    def mp_low(w):
        p = road(w)
        p["rate_deviation_notes"] = "The MP's amount was an early figure, before the survey."
        return finish(p, mp_x=0.7)
    add("edge_mp_low", "edge: MP amount", EDGE, "fits", OK,
        "Honest rates; the estimate is 43% above the MP's amount (the MP's first guess).",
        "An MP's figure is a guess, not a price.", mp_low)
    add("edge_lights_bigger_spec", "edge: specification", EDGE, "check", OK_SOFT,
        "Solar lights with a 30 W LED, 100 Wp panel and 9 m pole at Rs 29,000 each (the "
        "district's usual 12 W light costs about Rs 20,900); the MP agreed the amount.",
        "A bigger light costs more, but the specification is the agency's word: at most "
        "'check this'.",
        lambda w: lights(29_000, spec="Solar street light set: 30 W LED, 100 Wp panel, LiFePO4 "
                         "battery, 9 m GI pole, installed", watt_per_unit="30", solar_wp="100",
                         pole_height_m="9"), pair="spec_vs_mp")
    add("edge_lights_usual", "edge: specification", HONEST, "fits", OK,
        "Solar lights at the district's usual price.", "In line.",
        lambda w: lights(20_900))

    def typo_low(w):
        p = road(w)
        n = find(p, "Cement")
        p[f"boq_rate_{n}"] = "38"             # a zero dropped, not answered
        return finish(p)
    add("edge_typo_dropped_zero", "edge: typing mistake", EDGE, "edge", OK,
        "Cement typed at Rs 38 a bag (a zero dropped), the warning not answered yet.",
        "A typing mistake that lowers the estimate is caught on the agency's screen; no price "
        "question.", typo_low)

    def typo_big(w):
        p = road(w)
        n = find(p, "Cement")
        p[f"boq_rate_{n}"] = "3800"           # an honest extra zero, not answered
        return finish(p)
    add("edge_typo_extra_zero", "edge: typing mistake", EDGE, "ask", ("check", "ask"),
        "An honest agency typed cement at Rs 3,800 a bag (an extra zero) and has not answered the "
        "form's warning.",
        "Identical on paper to the fraud that dresses padding as a typo: the rate must be "
        "corrected before sanction either way. Asking is not an accusation here.", typo_big,
        pair="typo_vs_padding")

    def m25(w):
        p = road(w, concrete_grade="M25", road_material_grade="M25",
                 road_layer_spec="M25 PCC 150 mm over WBM base 100 mm")
        n = find(p, "Cement")
        p[f"boq_qty_{n}"] = f"{round(float(p[f'boq_qty_{n}']) * 1.08)}"
        return finish(p)
    add("edge_m25_design_mix", "edge: specification", EDGE, "fits", OK,
        "An M25 road: a design mix takes about 8% more cement than M20.",
        "A higher grade, honestly more cement (IS 456 caps cement at 450 kg per m3).", m25,
        pair="m25_vs_padded")

    def big_crew(w):
        p = road(w)
        for k in [k for k in p if k.startswith("lab_workers_")]:
            n = k.removeprefix("lab_workers_")
            wk, dy = float(p[k]), float(p[f"lab_days_{n}"])
            p[k] = f"{wk * 2:g}"
            p[f"lab_days_{n}"] = f"{max(0.5, round(dy / 2 * 2) / 2):g}"
        return finish(p)
    add("edge_bigger_crew", "edge: labour", EDGE, "fits", OK,
        "Twice the workers for half the days: the same person-days.", "The agency's call.",
        big_crew)
    add("edge_skilled_premium", "edge: labour", EDGE, "edge", OK,
        "Masons paid 1.3 times the district's rate (a skilled team).",
        "Within the honest band for a trade.",
        lambda w: finish(lab(road(w), "mason", 1.3)))

    def specialised(w):
        p = road(w)
        add_line(p, "Kerb stone, precast, both edges", "m", 600, 210, "Approved quotation")
        return finish(p)
    add("edge_specialised_item", "edge: items", EDGE, "fits", OK,
        "A road with precast kerbs (an item no reader prices), 9% of the lines.",
        "Honest specialised items under the unread share.", specialised)

    def state_only(w):
        return finish(road(w, rate_up=1.08))
    add("edge_state_prices", "edge: scarce data", EDGE, "fits", OK,
        "Only the state's forms can price this district; materials 8% above them.",
        "Local prices differ; the state rate carries 10% for that.", state_only,
        background=lambda w: [x for x in w.background if x["district_lgd"] != "194"],
        pair="state_8_vs_22")

    # ---- frauds ----------------------------------------------------------------------------------
    for pc in (20, 25, 40):
        add(f"fraud_pad_{pc}", "fraud: uniform padding", FRAUD, "ask", FLAG,
            f"Every material {pc}% above the district's rates.",
            "Beyond CPWD's 10% limit; a whole-estimate pattern.",
            lambda w, pc=pc: finish(road(w, rate_up=1 + pc / 100)))
    for pc in (11, 12, 14):
        add(f"fraud_pad_{pc}", "fraud: salami padding", FRAUD, "check", FLAG,
            f"Every material {pc}% above the district's rates on a 300 m road: just under the "
            "15% question line.",
            "Above CPWD's 10% limit for justified rates; tens of thousands of rupees.",
            lambda w, pc=pc: finish(road(w, rate_up=1 + pc / 100)),
            pair="small_vs_big_12" if pc == 12 else "pad_7_vs_12" if pc == 11 else None)

    def one_line(w):
        return finish(scale(road(w), 2.0, only=("Cement",)))
    add("fraud_one_line_2x", "fraud: one line", FRAUD, "ask", FLAG,
        "Cement at twice the district's rate; everything else fair.", "Rs 5 lakh in one line.",
        one_line)

    def cement_x(f):
        return lambda w: finish(road(w, cement_x=f, just="Extra cement for kerbs and approaches"))
    add("fraud_qty_cement_150", "fraud: quantity", FRAUD, "ask", FLAG,
        "1.5 times the cement the road's size takes, 'justified'.", "Material that is never used.",
        cement_x(1.5))
    add("fraud_qty_cement_120", "fraud: quantity", FRAUD, "check", FLAG,
        "1.2 times the cement the size takes, justified as kerbs and approaches.",
        "About Rs 1 lakh of cement nobody needs; under the 25% quantity line.",
        cement_x(1.2))

    def m25_padded(w):
        p = road(w, concrete_grade="M25", road_material_grade="M25", cement_x=1.6,
                 road_layer_spec="M25 PCC 150 mm over WBM base 100 mm")
        return finish(p)
    add("fraud_m25_cement", "fraud: quantity", FRAUD, "ask", FLAG,
        "Declared M25 so no nominal mix applies; cement 1.6 times what M20 takes.",
        "IS 456 caps cement at 450 kg per m3 (9 bags): 1.6 x 8.06 bags is beyond it.",
        m25_padded, pair="m25_vs_padded")

    def dup_line(w):
        p = road(w)
        n = find(p, "Cement")
        add_line(p, "Cement PPC (for curing and finishing)", "bag", float(p[f"boq_qty_{n}"]),
                 float(p[f"boq_rate_{n}"]), "District recent rates")
        return finish(p)
    add("fraud_duplicate_line", "fraud: quantity", FRAUD, "ask", FLAG,
        "The cement line entered twice under two names.", "Twice the cement the size takes.",
        dup_line)

    def into_lump(w):
        p = road(w)
        p["lumpsum_components"] = f"{lines_total(p) * 0.18:.0f}"
        return finish(p)
    add("fraud_lump_sum_18", "fraud: hidden", FRAUD, "ask", FLAG,
        "18% of the estimate added as a lump sum.", "Unitemised money in a construction estimate.",
        into_lump)

    def into_other(w):
        p = road(w)
        p["other_charges"] = f"{lines_total(p) * 0.20:.0f}"      # tax included in rates
        return finish(p)
    add("fraud_other_charges_20", "fraud: hidden", FRAUD, "ask", FLAG,
        "20% 'other charges' while the rates already include tax.", "Nothing to show for it.",
        into_other)

    def other_9(w):
        p = road(w)
        p["other_charges"] = f"{lines_total(p) * 0.12:.0f}"
        return finish(p)
    add("fraud_other_charges_12", "fraud: hidden", FRAUD, "check", FLAG,
        "12% 'other charges' while the rates already include tax (CPWD contingency is 3%).",
        "Above any honest contingency; over a lakh unexplained.", other_9)

    def unread(w):
        p = road(w, rate_up=1.25)
        for start, txt in (("Cement", "Binding material, grey, 43"), ("Coarse sand",
                           "Fine filler material"), ("Stone aggregate", "Kapchi 20"),
                           ("WBM", "Lower layer material")):
            p[f"boq_desc_{find(p, start)}"] = txt
        return finish(p)
    add("fraud_unreadable_names", "fraud: hidden", FRAUD, "ask", FLAG,
        "25% padding, every item given a name no reader knows.", "Nothing can be priced.",
        unread)

    def odd_units(w):
        p = road(w, rate_up=1.25)
        n = find(p, "Coarse sand")
        p[f"boq_qty_{n}"] = f"{float(p[f'boq_qty_{n}']) / 2.832:.2f}"
        p[f"boq_rate_{n}"] = f"{float(p[f'boq_rate_{n}']) * 2.832:.0f}"
        p[f"boq_unit_{n}"] = "brass"
        n = find(p, "Cement")
        p[f"boq_qty_{n}"] = f"{float(p[f'boq_qty_{n}']) / 2:.1f}"
        p[f"boq_rate_{n}"] = f"{float(p[f'boq_rate_{n}']) * 2:.0f}"
        p[f"boq_unit_{n}"] = "quintal"
        return finish(p)
    add("fraud_odd_units", "fraud: hidden", FRAUD, "ask", FLAG,
        "25% padding with sand in brass and cement in quintals.", "Units chosen to avoid "
        "comparison.", odd_units)

    def dilute(w):
        p = road(w, rate_up=1.20)
        add_line(p, "Site development and dressing works", "sqm", 1050, 130,
                 "Approved quotation")
        return finish(p)
    add("fraud_diluted", "fraud: hidden", FRAUD, "ask", FLAG,
        "20% padding plus a large vague 'site development' line to water the share down.",
        "The vague line hides nothing: the priced lines are still 20% up.", dilute)

    def typo_padding(w):
        p = road(w)
        n = find(p, "Cement")
        p[f"boq_rate_{n}"] = "3800"
        return finish(p)
    add("fraud_typo_cover", "fraud: typing mistake", FRAUD, "ask", FLAG,
        "Cement at Rs 3,800 a bag, the 'typing mistake' warning never answered.",
        "Rs 45 lakh more in the total; padding dressed as a typo.", typo_padding,
        pair="typo_vs_padding")

    def typo_answered(w):
        p = road(w)
        n = find(p, "Cement")
        p[f"boq_rate_{n}"] = "1200"
        p[f"boq_just_{n}"] = "Special cement as per site needs"
        return finish(p)
    add("fraud_rate_answered", "fraud: one line", FRAUD, "ask", FLAG,
        "Cement at Rs 1,200 a bag, the warning answered with a vague reason.",
        "An answered warning puts the line back in the price check.", typo_answered)

    def mp_collusion(w):
        return lights(42_000)
    add("fraud_lights_mp_agrees", "fraud: price per unit", FRAUD, "check", FLAG,
        "Standard 12 W solar lights at Rs 42,000 each (twice the district's), the MP's amount "
        "just as high.",
        "The MP agreeing does not make a price fair: twice what 98 in 100 similar lights cost.",
        mp_collusion, pair="spec_vs_mp")

    def mp_just_under(w):
        return lights(32_000, mp=300_000)
    add("fraud_lights_mp_gap_7", "fraud: price per unit", FRAUD, "check", FLAG,
        "Standard solar lights at Rs 32,000 each; the estimate 7% above the MP's amount (just "
        "under the 10% line).",
        "1.5 times the district's usual light.", mp_just_under)
    add("fraud_lights_2x", "fraud: price per unit", FRAUD, "ask", FLAG,
        "Standard lights at Rs 48,000 each, twice the MP's amount.", "The example filing.",
        lambda w: lights(48_000, mp=240_000))

    def hilly_claim(w):
        p = road(w, rate_up=1.18, terrain="Hilly / steep", site_access="Foot / manual carry required",
                 motorable_access_distance_m="800")
        return finish(p)
    add("fraud_claimed_hilly", "fraud: claimed reason", FRAUD, "check", FLAG,
        "Jaunpur is plains; the form claims a hilly head-load site to carry 18% padding.",
        "The same form as the honest hilly site: a claim can soften a question, never clear it.",
        hilly_claim, pair="hilly_vs_claimed")
    add("fraud_plain_18", "fraud: uniform padding", FRAUD, "ask", FLAG,
        "Every material 18% above the district's rates, no reason given.",
        "Beyond 15%: a question.", lambda w: finish(road(w, rate_up=1.18)))

    add("fraud_labour_24x", "fraud: labour", FRAUD, "ask", FLAG,
        "Masons at 2.4 times the district's day rate.", "A blatant wage.",
        lambda w: finish(lab(road(w), "mason", 2.4)))

    def labour_17(w):
        p = road(w)
        lab(p, "mason", 1.7)
        lab(p, "beldar", 1.7)
        return finish(p)
    add("fraud_labour_17x_all", "fraud: labour", FRAUD, "check", FLAG,
        "Every trade paid 1.7 times the district's rate: Rs 2.3 lakh more in wages.",
        "No crew earns 1.7 times the going wage on a village road.", labour_17)

    def ghost(w):
        p = road(w)
        lab(p, "beldar", 1.0, days_f=3.0)
        return finish(p)
    def ghost_workers(w):
        p = road(w)
        for k in [k for k in p if k.startswith("lab_trade_") and p[k] == "beldar"]:
            n = k.removeprefix("lab_trade_")
            p[f"lab_workers_{n}"] = f"{float(p[f'lab_workers_{n}']) * 3:g}"
        return finish(p)
    add("fraud_ghost_workers", "fraud: labour", FRAUD, "check", FLAG,
        "Three times the labourers on the muster roll for the same days (ghost workers), wages "
        "fair.",
        "Person-days three times what other agencies' roads of this size take.", ghost_workers)
    add("fraud_ghost_labour", "fraud: labour", FRAUD, "check", FLAG,
        "Three times the labourer-days the road needs (inflated muster roll), wages fair.",
        "Ghost workers: the most common works fraud in India's rural schemes.", ghost)

    def cartel(w):
        out = []
        for x in w.background:
            x = copy.deepcopy(x)
            if x["district_lgd"] == "194":
                for site in x["cost_form"]["sites"]:
                    for ln in site["lines"]:
                        if ln.get("group") != "labour" and isinstance(ln.get("rate"), (int,
                                                                                         float)):
                            ln["rate"] = round(ln["rate"] * 1.22, 2)
            out.append(x)
        return out
    add("fraud_cartel_22", "fraud: collusion", FRAUD, "check", FLAG,
        "Every agency in the district pads 22% together; this filing too.",
        "The district's own rates are no fair rate when all of them are padded; the state's "
        "forms show it.", lambda w: finish(road(w, rate_up=1.22)), background=cartel)
    add("fraud_state_22", "fraud: scarce data", FRAUD, "check", FLAG,
        "Only the state's forms can price this district; materials 22% above them.",
        "12% above even the state rate plus its 10% local allowance.",
        lambda w: finish(road(w, rate_up=1.22)),
        background=lambda w: [x for x in w.background if x["district_lgd"] != "194"],
        pair="state_8_vs_22")

    def big_size(w):
        p = road(w, length=600, width=7.0)
        return finish(p)
    add("fraud_size_everywhere", "fraud: size", FRAUD, "check", FLAG,
        "The road is 300 m x 3.5 m on the ground; the form says 600 m x 7 m everywhere.",
        "The estimate is consistent with its claimed size: only the site (videos, the "
        "officer's visit) can show it. Site Progress's job.", big_size, scope="other")
    return c


def by_id() -> dict[str, Case]:
    return {x.id: x for x in cases()}
