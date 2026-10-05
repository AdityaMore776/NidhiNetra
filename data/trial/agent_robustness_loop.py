r"""The four agents' self-improvement loop (T135, T136): every way we could think of for them to go wrong.

The owner (5 Oct 2026): "take each agent and run them through samples, then try to find ways where
this agent can go wrong, give a wrong answer, or can be bypassed ... keep iterating until the agents
become robust enough ... if data isn't enough to make a reliable prediction of a price, turn off
the agent for this specific price, and learn about this data piece after".

The samples are the work form's example filings (data/trial/work_form_examples.py: made-up
agencies in the real district of Jaunpur, an honest road and one filing caught by each agent) on
top of the district's 1,038 real eSAKSHI works. Each probe changes a filing, or the data around it,
and runs the four agents exactly as production does (pipeline.assess_work, the district's index
rebuilt with the changed filing in it, as POST /work-form/check does). Four kinds of probe:

  damage   random junk in any field (types, NaN, huge, negative, empty, unicode, wrong shapes):
           no agent may crash (an ERROR result), break the contract, or answer differently twice
  noise    what an honest agency's form varies in (rates a few % apart, lines in another order or
           split in two, other words or units for the same item, GPS jitter): no answer may flip
  evasion  what a dishonest agency would try (hide padding in lump sums or charges, write items no
           reader knows, file a road a little longer than the old one, call a rebuild an upgrade,
           promise a start years away, alternate "can't tell" with "not shown", never film...):
           the agent must still ask, or say plainly what it could not check
  scarce   too little or untrustworthy data (few filings, prices all over the place, one agency
           filing most forms, stale prices): the agent must turn that check off for that item
           (never a wrong question) and record the gap so the data can be collected

Each probe ends PASS, FAIL (fix it: the loop's next round) or LIMIT (a known edge of a measured
rule, e.g. padding just under the 15% line; listed so nobody mistakes it for coverage).

Run:  apps\engine\.venv\Scripts\python.exe data\trial\agent_robustness_loop.py [--damage N]
Writes results/agent_robustness.txt and .json.
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import random
import sys
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(ROOT / "data" / "trial"))
sys.path.insert(0, str(ROOT / "apps" / "engine"))
import work_form_examples as wf  # noqa: E402

from drishti.agents.contract import Status  # noqa: E402
from drishti.batch import indexes  # noqa: E402
from drishti.cost_form import pswif  # noqa: E402
from drishti.evaluation.stats import build_store  # noqa: E402
from drishti.pipeline.orchestrator import Context, assess_work  # noqa: E402

OUT = ROOT / "data" / "trial" / "results" / "agent_robustness"
AGENTS = ("cost_estimate", "dup_split", "time_rules", "site_progress")
METRE = 1 / 111_195


# ---- the world ------------------------------------------------------------------------------------

@dataclass
class World:
    as_of: date
    place: dict
    stats: object
    district: list[dict]        # the district's real works
    background: list[dict]      # made-up filings around the examples
    examples: dict[str, dict]   # key -> {"form", "record", "codes"}
    records: dict[str, dict]    # key -> the example's work as the engine reads it


def build_world() -> World:
    works, info = wf.load()
    as_of = info["as_of"]
    dist = next(w for w in works if w.get("district_name") == wf.DISTRICT)
    place = {"district_lgd": dist["district_lgd"], "state_lgd": dist.get("state_lgd"),
             "state_name": dist.get("state_name"), "district_name": wf.DISTRICT}
    exs, background = wf.build(as_of)
    for w in background:
        w.update(place)
    examples = {e["key"]: {"form": e["form"], "record": e["record"], "codes": e["codes"]}
                for e in exs}
    records = {k: work_of(e["form"], e["record"], place, as_of) for k, e in examples.items()}
    return World(as_of, place, build_store(works), [w for w in works
                                                     if w.get("district_lgd") == place["district_lgd"]],
                 background, examples, records)


def work_of(form: dict, record: dict, place: dict, as_of: date) -> dict:
    w = pswif.to_work(form, today=as_of, **record)
    w.update(place)
    return w


def run(world: World, work: dict, *, drop: tuple[str, ...] = (), extra: list[dict] | None = None,
        background: list[dict] | None = None) -> dict:
    """The four agents on `work`, its district's index holding the background, the other
    examples, `extra`, and the work itself (never a stale copy of it)."""
    bg = world.background if background is None else background
    # `drop` takes works out of the world; `extra` (which may replace them) goes in after
    others = [w for w in bg + list(world.records.values())
              if w["work_id"] != work["work_id"] and w["work_id"] not in drop]
    others += [w for w in extra or [] if w["work_id"] != work["work_id"]]
    ctx = Context(stats=world.stats, as_of=world.as_of,
                  data=indexes(world.district + others + [work]))
    a = assess_work(work, ctx)
    return {r.agent: r for r in a.agents} | {"_score": a.fused.score}


def flags(res: dict, agent: str) -> list[str]:
    return sorted(f.code for f in res[agent].findings if f.risk > 0)


def form_of(world: World, key: str) -> dict:
    return copy.deepcopy(world.examples[key]["form"])


def record_of(world: World, key: str) -> dict:
    return copy.deepcopy(world.examples[key]["record"])


# ---- the form's BOQ ---------------------------------------------------------------------------------

FIELDS = ("code", "desc", "unit", "qty", "rate", "source", "measure_ref", "just")


def boq(p: dict) -> list[dict]:
    rows, n = [], 1
    while f"boq_desc_{n}" in p:
        rows.append({k: p.get(f"boq_{k}_{n}", "") for k in FIELDS})
        n += 1
    return rows


def set_boq(p: dict, rows: list[dict]) -> dict:
    for k in [k for k in p if k.startswith("boq_")]:
        del p[k]
    for n, r in enumerate(rows, start=1):
        for k in FIELDS:
            p[f"boq_{k}_{n}"] = r.get(k, "")
    return retotal(p)


def retotal(p: dict) -> dict:
    """The estimate's total as the agency's document would carry it (lines + lump sum + other)."""
    total = sum(float(r["qty"] or 0) * float(r["rate"] or 0) for r in boq(p))
    total += float(p.get("lumpsum_components") or 0) + float(p.get("other_charges") or 0)
    p["technical_estimate"] = f"{total:.2f}"
    p["mplads_share"] = f"{total:.0f}"
    return p


def honest_rate(desc: str) -> float | None:
    d = desc.lower()
    for word, m in (("cement", "cement"), ("sand", "sand"), ("aggregate", "aggregate"),
                    ("wbm", "granular_base"), ("mason", "labour_skilled"),
                    ("labourer", "labour_unskilled")):
        if word in d:
            return wf.RATE[m]
    return None


# ---- one probe --------------------------------------------------------------------------------------

@dataclass
class Probe:
    agent: str
    kind: str          # damage | noise | evasion | scarce
    name: str
    fn: Callable[[World], tuple[str, str]]   # -> (PASS | FAIL | LIMIT, detail)


PROBES: list[Probe] = []


def probe(agent: str, kind: str, name: str):
    def deco(fn):
        PROBES.append(Probe(agent, kind, name, fn))
        return fn
    return deco


def still(res: dict, agent: str, want: list[str] | str, what: str) -> tuple[str, str]:
    """PASS when the agent still raises `want` (every code), else FAIL."""
    want = [want] if isinstance(want, str) else want
    got = flags(res, agent)
    ok = all(c in got for c in want)
    return ("PASS" if ok else "FAIL",
            f"{what}: {', '.join(got) or 'nothing'} ({res[agent].status.value})")


def quiet(res: dict, agent: str, what: str) -> tuple[str, str]:
    got = flags(res, agent)
    return ("PASS" if not got else "FAIL",
            f"{what}: {', '.join(got) or 'nothing'} ({res[agent].status.value})")


def said(res: dict, agent: str) -> str:
    r = res[agent]
    return " ".join([r.headline, *r.limitations, *((r.evidence or {}).get("notes") or [])])


# ===================================================================================================
# Cost
# ===================================================================================================

@probe("cost_estimate", "noise", "honest rates a few % apart (seeded): no question")
def _(world):
    rng = random.Random(11)
    bad = []
    for _ in range(12):
        p = form_of(world, "clean")
        rows = boq(p)
        for r in rows:
            r["rate"] = f"{float(r['rate']) * rng.uniform(0.95, 1.05):.0f}"
        res = run(world, work_of(retotal(set_boq(p, rows)), record_of(world, "clean"),
                                 world.place, world.as_of))
        if flags(res, "cost_estimate"):
            bad.append(flags(res, "cost_estimate"))
    return ("PASS" if not bad else "FAIL", f"12 honest variants, {len(bad)} asked: {bad[:2]}")


@probe("cost_estimate", "noise", "lines in another order: same answer")
def _(world):
    out = []
    for key in ("clean", "cost_padded", "cost_quantity"):
        p = form_of(world, key)
        rows = boq(p)[::-1]
        res = run(world, work_of(set_boq(p, rows), record_of(world, key), world.place,
                                 world.as_of))
        out.append((key, flags(res, "cost_estimate") == sorted(
            world.examples[key]["codes"].get("cost_estimate", []))))
    bad = [k for k, ok in out if not ok]
    return ("PASS" if not bad else "FAIL", f"changed: {bad or 'none'}")


@probe("cost_estimate", "noise", "one line split in two (half each): same answer")
def _(world):
    bad = []
    for key in ("clean", "cost_padded", "cost_quantity"):
        p = form_of(world, key)
        rows = boq(p)
        a = dict(rows[0])
        q = float(a["qty"])
        rows[0]["qty"] = f"{math.floor(q / 2)}"
        a["qty"] = f"{q - math.floor(q / 2)}"
        rows.insert(1, a)
        res = run(world, work_of(set_boq(p, rows), record_of(world, key), world.place,
                                 world.as_of))
        if flags(res, "cost_estimate") != sorted(world.examples[key]["codes"].get(
                "cost_estimate", [])):
            bad.append((key, flags(res, "cost_estimate")))
    return ("PASS" if not bad else "FAIL", f"changed: {bad or 'none'}")


@probe("cost_estimate", "noise", "other words and units for the same items: same answer")
def _(world):
    words = {"Cement OPC 43 grade": ("Portland cement (OPC-43), 50 kg bags", "Bags"),
             "Coarse sand": ("River sand, coarse", "Cu.m"),
             "Stone aggregate 20 mm": ("20mm stone grit / aggregate", "CUM"),
             "Labourer (unskilled)": ("Unskilled labour (beldar)", "Mandays")}
    bad = []
    for key in ("clean", "cost_padded"):
        p = form_of(world, key)
        rows = boq(p)
        for r in rows:
            if r["desc"] in words:
                r["desc"], r["unit"] = words[r["desc"]]
        res = run(world, work_of(set_boq(p, rows), record_of(world, key), world.place,
                                 world.as_of))
        if flags(res, "cost_estimate") != sorted(world.examples[key]["codes"].get(
                "cost_estimate", [])):
            bad.append((key, flags(res, "cost_estimate"), res["cost_estimate"].status.value))
    return ("PASS" if not bad else "FAIL", f"changed: {bad or 'none'}")


@probe("cost_estimate", "noise", "cement written in kg instead of bags: same answer")
def _(world):
    bad = []
    for key in ("clean", "cost_quantity"):
        p = form_of(world, key)
        rows = boq(p)
        r = rows[0]
        r["qty"], r["rate"], r["unit"] = f"{float(r['qty']) * 50:g}", \
            f"{float(r['rate']) / 50:.2f}", "kg"
        res = run(world, work_of(set_boq(p, rows), record_of(world, key), world.place,
                                 world.as_of))
        if flags(res, "cost_estimate") != sorted(world.examples[key]["codes"].get(
                "cost_estimate", [])):
            bad.append((key, flags(res, "cost_estimate")))
    return ("PASS" if not bad else "FAIL", f"changed: {bad or 'none'}")


@probe("cost_estimate", "evasion", "padded items given names no reader knows")
def _(world):
    p = form_of(world, "cost_padded")
    rows = boq(p)
    new = {"Cement OPC 43 grade": "Binding material, grey, 43",
           "Coarse sand": "Fine filler material",
           "Stone aggregate 20 mm": "Kapchi 20",
           "WBM base, graded stone": "Base course material"}
    for r in rows:
        r["desc"] = new.get(r["desc"], r["desc"])
    res = run(world, work_of(set_boq(p, rows), record_of(world, "cost_padded"), world.place,
                             world.as_of))
    got = flags(res, "cost_estimate")
    told = "could not" in said(res, "cost_estimate").lower() or got
    return ("PASS" if got else "FAIL",
            f"{got or 'nothing'} ({res['cost_estimate'].status.value}); "
            f"says what it could not price: {bool(told)}")


@probe("cost_estimate", "evasion", "the padding moved into a lump-sum line")
def _(world):
    p = form_of(world, "cost_padded")
    rows = boq(p)
    extra = 0.0
    for r in rows:
        fair = honest_rate(r["desc"])
        if fair:
            extra += float(r["qty"]) * (float(r["rate"]) - fair)
            r["rate"] = f"{fair:g}"
    p["lumpsum_components"] = f"{extra:.0f}"
    res = run(world, work_of(set_boq(p, rows), record_of(world, "cost_padded"), world.place,
                             world.as_of))
    return still(res, "cost_estimate", "ESTIMATE_ABOVE_FAIR_PRICE",
                 f"Rs {extra:,.0f} as a lump sum")


@probe("cost_estimate", "evasion", "the padding moved into 'other charges'")
def _(world):
    p = form_of(world, "cost_padded")
    rows = boq(p)
    extra = 0.0
    for r in rows:
        fair = honest_rate(r["desc"])
        if fair:
            extra += float(r["qty"]) * (float(r["rate"]) - fair)
            r["rate"] = f"{fair:g}"
    p["other_charges"] = f"{extra:.0f}"
    res = run(world, work_of(set_boq(p, rows), record_of(world, "cost_padded"), world.place,
                             world.as_of))
    return still(res, "cost_estimate", "ESTIMATE_ABOVE_FAIR_PRICE",
                 f"Rs {extra:,.0f} as other charges")


@probe("cost_estimate", "evasion", "padded items priced in units nobody converts (brass, quintal)")
def _(world):
    p = form_of(world, "cost_padded")
    rows = boq(p)
    for r in rows:
        if r["desc"].startswith("Coarse sand"):          # 1 brass = 100 cft = 2.832 m3
            r["qty"], r["rate"], r["unit"] = f"{float(r['qty']) / 2.832:.2f}", \
                f"{float(r['rate']) * 2.832:.0f}", "brass"
        if r["desc"].startswith("Cement"):               # 1 quintal = 2 bags
            r["qty"], r["rate"], r["unit"] = f"{float(r['qty']) / 2:.1f}", \
                f"{float(r['rate']) * 2:.0f}", "quintal"
    res = run(world, work_of(set_boq(p, rows), record_of(world, "cost_padded"), world.place,
                             world.as_of))
    return still(res, "cost_estimate", "ESTIMATE_ABOVE_FAIR_PRICE", "sand in brass, cement in quintal")


@probe("cost_estimate", "evasion", "one agency files under name variants to lift the district price")
def _(world):
    base = world.examples["cost_padded"]
    extra = []
    for i, alias in enumerate(("Gramin Path Nigam, Div-1", "GRAMIN PATH NIGAM (Division 2)",
                               "Gramin Path Nigam Div. 3", "Gramin-Path-Nigam")):
        f = copy.deepcopy(base["form"])
        f["recommendation_ref"] = f"WF-ALIAS-{i}"
        f["implementing_agency"] = alias
        f["mp_recommendation_date"] = (world.as_of - timedelta(days=70 + i)).isoformat()
        extra.append(work_of(f, {}, world.place, world.as_of))
    res = run(world, world.records["cost_padded"], extra=extra)
    return still(res, "cost_estimate", "ESTIMATE_ABOVE_FAIR_PRICE",
                 "4 padded forms under name variants of the same agency")


@probe("cost_estimate", "evasion", "padding 14%: just under the 15% line")
def _(world):
    p = form_of(world, "clean")
    rows = boq(p)
    for r in rows:
        if honest_rate(r["desc"]):
            r["rate"] = f"{float(r['rate']) * 1.14:.0f}"
    res = run(world, work_of(retotal(set_boq(p, rows)), record_of(world, "clean"), world.place,
                             world.as_of))
    got = flags(res, "cost_estimate")
    return ("LIMIT" if not got else "PASS",
            f"{got or 'nothing'}: the line is 15% and Rs 50,000 (plan T120 §6.5, measured on "
            "planted forms); below it a gap is an honest spread")


@probe("cost_estimate", "scarce", "only 4 other filings in the district: prices off, gap recorded")
def _(world):
    keep = [w for w in world.background if not w["work_id"].startswith("WF-BG")][:2]
    bg = keep + [w for w in world.background if w["work_id"].startswith("WF-BG")][:1]
    res = run(world, world.records["cost_padded"], background=bg,
              drop=tuple(r["work_id"] for k, r in world.records.items() if k != "cost_padded"))
    r = res["cost_estimate"]
    gaps = (r.evidence or {}).get("data_gaps") or []
    got = flags(res, "cost_estimate")
    ok = not got and bool(gaps)
    return ("PASS" if ok else "FAIL",
            f"{got or 'no question'} ({r.status.value}); data gaps recorded: {len(gaps)}")


def _scatter(world, factor_of: Callable[[int], float]) -> list[dict]:
    """The background roads again, their rates scaled per filing."""
    out = []
    for i, w in enumerate(world.background):
        w = copy.deepcopy(w)
        if w["work_id"].startswith("WF-BG"):
            for site in w["cost_form"]["sites"]:
                for ln in site.get("lines") or []:
                    if isinstance(ln.get("rate"), (int, float)) and ln.get("unit") != "ls":
                        ln["rate"] = round(ln["rate"] * factor_of(i), 2)
        out.append(w)
    return out


@probe("cost_estimate", "scarce", "district prices all over the place: the honest road is not asked")
def _(world):
    bg = _scatter(world, lambda i: (0.55, 1.6, 0.6, 1.7, 0.5, 1.8, 0.65)[i % 7])
    res = run(world, world.records["clean"], background=bg,
              drop=tuple(r["work_id"] for k, r in world.records.items() if k != "clean"))
    r = res["cost_estimate"]
    gaps = (r.evidence or {}).get("data_gaps") or []
    got = flags(res, "cost_estimate")
    return ("PASS" if not got and gaps else "FAIL",
            f"{got or 'no question'} ({r.status.value}); unreliable prices recorded as gaps: "
            f"{len(gaps)}")


@probe("cost_estimate", "scarce", "one agency files most forms, 30% under: the honest road not asked")
def _(world):
    extra = []
    for i in range(10):
        f = form_of(world, "clean")
        f["recommendation_ref"] = f"WF-CHEAP-{i}"
        f["implementing_agency"] = "Sasta Nirman Agency"
        f["mp_recommendation_date"] = (world.as_of - timedelta(days=60 + 3 * i)).isoformat()
        rows = boq(f)
        for r in rows:
            if honest_rate(r["desc"]):
                r["rate"] = f"{float(r['rate']) * 0.7:.0f}"
        extra.append(work_of(set_boq(f, rows), {}, world.place, world.as_of))
    res = run(world, world.records["clean"], extra=extra)
    return quiet(res, "cost_estimate", "10 forms by one agency at 70% of the usual rates")


@probe("cost_estimate", "scarce", "every other filing older than 6 months: prices off, gap recorded")
def _(world):
    old = []
    for w in world.background:
        w = copy.deepcopy(w)
        cf = w.get("cost_form")
        if isinstance(cf, dict):
            cf["filed_on"] = "2025-01-15"
        old.append(w)
    res = run(world, world.records["cost_padded"], background=old,
              drop=tuple(r["work_id"] for k, r in world.records.items() if k != "cost_padded"))
    r = res["cost_estimate"]
    gaps = (r.evidence or {}).get("data_gaps") or []
    got = flags(res, "cost_estimate")
    return ("PASS" if not got and gaps else "FAIL",
            f"{got or 'no question'} ({r.status.value}); gaps recorded: {len(gaps)}")


@probe("cost_estimate", "scarce", "a typo'd price (Rs 38,000 a bag) among the filings: answers hold")
def _(world):
    bg = copy.deepcopy(world.background)
    for w in bg:
        if w["work_id"] == "WF-BG-1":
            w["cost_form"]["sites"][0]["lines"][0]["rate"] = 38_000
    bad = []
    for key in ("clean", "cost_padded"):
        res = run(world, world.records[key], background=bg)
        if flags(res, "cost_estimate") != sorted(world.examples[key]["codes"].get(
                "cost_estimate", [])):
            bad.append(key)
    return ("PASS" if not bad else "FAIL", f"changed: {bad or 'none'}")


@probe("cost_estimate", "scarce", "a work in a state with no reference prices: no question")
def _(world):
    p = form_of(world, "cost_lights")
    p["state"] = "Goa"
    w = work_of(p, {}, {**world.place, "state_name": "Goa", "state_lgd": "30"}, world.as_of)
    res = run(world, w)
    return quiet(res, "cost_estimate", "solar lights in a state without a reference")


# ===================================================================================================
# Duplicate Work
# ===================================================================================================

def _shift(p: dict, keys: tuple[str, ...], metres_north: float) -> dict:
    for k in keys:
        if p.get(k):
            p[k] = f"{float(p[k]) + metres_north * METRE:.6f}"
    return p


ROAD_PINS = ("latitude", "start_lat", "end_lat")


@probe("dup_split", "noise", "GPS jitter of 5 m: the repeat still asked, the honest road not")
def _(world):
    rng = random.Random(5)
    bad = []
    for key in ("dup_pin", "clean"):
        p = form_of(world, key)
        for k in ROAD_PINS + ("longitude", "start_lon", "end_lon"):
            if p.get(k):
                p[k] = f"{float(p[k]) + rng.uniform(-5, 5) * METRE:.6f}"
        res = run(world, work_of(p, record_of(world, key), world.place, world.as_of))
        if flags(res, "dup_split") != sorted(world.examples[key]["codes"].get("dup_split", [])):
            bad.append((key, flags(res, "dup_split")))
    return ("PASS" if not bad else "FAIL", f"changed: {bad or 'none'}")


@probe("dup_split", "noise", "the road's two ends swapped: still asked")
def _(world):
    p = form_of(world, "dup_pin")
    p["start_lat"], p["end_lat"] = p["end_lat"], p["start_lat"]
    p["start_lon"], p["end_lon"] = p["end_lon"], p["start_lon"]
    p["latitude"], p["longitude"] = p["start_lat"], p["start_lon"]
    res = run(world, work_of(p, {}, world.place, world.as_of))
    return still(res, "dup_split", "SANCTIONED_WORK_AT_THIS_SITE", "ends swapped")


@probe("dup_split", "noise", "the repeat described in other words: still asked")
def _(world):
    p = form_of(world, "dup_pin")
    p["work_title"] = "Interlocking/CC pavement on the school approach"
    p["scope_of_work"] = "Paving of the approach lane, 300 m."
    res = run(world, work_of(p, {}, world.place, world.as_of))
    return still(res, "dup_split", "SANCTIONED_WORK_AT_THIS_SITE", "new words")


@probe("dup_split", "evasion", "the old road re-filed 100 m longer at one end")
def _(world):
    p = form_of(world, "dup_pin")
    p["end_lat"] = f"{float(p['end_lat']) + 100 * METRE:.6f}"
    p["road_length_m"] = p["route_length_m"] = "400"
    res = run(world, work_of(p, {}, world.place, world.as_of))
    return still(res, "dup_split", "SANCTIONED_WORK_AT_THIS_SITE", "300 m of old road + 100 m")


@probe("dup_split", "evasion", "the same stretch declared a 'continuation' of the old road")
def _(world):
    p = form_of(world, "dup_pin")
    p.update(work_nature="Continuation / next phase", prior_work_id="WF-OLD-ROAD",
             known_nearby_work_ids="WF-OLD-ROAD",
             nearby_work_relationship="Same asset, separate phase")
    res = run(world, work_of(p, {}, world.place, world.as_of))
    got = flags(res, "dup_split")
    return ("PASS" if got else "FAIL", f"{got or 'nothing'} (old road completed 11 months ago, "
            "same 300 m)")


@probe("dup_split", "evasion", "the hall rebuild declared a 'repair / renovation' instead")
def _(world):
    p = form_of(world, "dup_rebuild")
    p["work_nature"] = "Repair / renovation"           # the form's own word for an upgrade
    res = run(world, work_of(p, {}, world.place, world.as_of))
    return still(res, "dup_split", ["REBUILT_SOON_AFTER_COMPLETION"], "renovation 16 months on")


@probe("dup_split", "evasion", "the rebuild with no nature declared, the old hall only named nearby")
def _(world):
    p = form_of(world, "dup_rebuild")
    p.update(work_nature="", prior_work_id="")       # named only among the nearby works
    res = run(world, work_of(p, {}, world.place, world.as_of))
    return still(res, "dup_split", ["REBUILT_SOON_AFTER_COMPLETION"], "named nearby only")


@probe("dup_split", "noise", "a real extension beside the old road (from its end onward): not asked")
def _(world):
    p = form_of(world, "dup_pin")
    old = next(w for w in world.background if w["work_id"] == "WF-OLD-ROAD")
    loc = old["cost_form"]["sites"][0]["location"]
    p.update(work_nature="Continuation / next phase", prior_work_id="WF-OLD-ROAD",
             known_nearby_work_ids="WF-OLD-ROAD",
             nearby_work_relationship="Same asset, separate phase",
             start_lat=f"{loc['end_lat']:.6f}", start_lon=f"{loc['end_lon']:.6f}",
             end_lat=f"{loc['end_lat'] + 290 * METRE:.6f}", end_lon=f"{loc['end_lon']:.6f}")
    p["latitude"], p["longitude"] = p["start_lat"], p["start_lon"]
    res = run(world, work_of(p, {}, world.place, world.as_of))
    return quiet(res, "dup_split", "the next 290 m from the old road's end")


@probe("dup_split", "noise", "a first floor on a finished hall (another size): not asked")
def _(world):
    p = form_of(world, "dup_rebuild")
    p.update(work_nature="Extension / additional component", builtup_area="90", floors="1",
             scope_of_work="First floor of 90 sq m on the community hall, with a staircase.")
    res = run(world, work_of(p, {}, world.place, world.as_of))
    got = flags(res, "dup_split")
    return ("PASS" if "REBUILT_SOON_AFTER_COMPLETION" not in got else "FAIL",
            f"{got or 'nothing'}: an extension of another size is not the same asset again")


@probe("dup_split", "evasion", "the old road re-filed 100 m longer and declared a 'continuation'")
def _(world):
    p = form_of(world, "dup_pin")
    p["end_lat"] = f"{float(p['end_lat']) + 100 * METRE:.6f}"
    p.update(work_nature="Continuation / next phase", prior_work_id="WF-OLD-ROAD",
             known_nearby_work_ids="WF-OLD-ROAD",
             nearby_work_relationship="Same asset, separate phase",
             road_length_m="400", route_length_m="400")
    res = run(world, work_of(p, {}, world.place, world.as_of))
    got = flags(res, "dup_split")
    return ("PASS" if got else "FAIL", f"{got or 'nothing'} (the old 300 m inside the new 400 m)")


@probe("dup_split", "evasion", "the hall rebuild declared 'new' (no link) at the same pin")
def _(world):
    p = form_of(world, "dup_rebuild")
    p.update(work_nature="New asset", prior_work_id="", prior_completion_date="",
             known_nearby_work_ids="", nearby_work_relationship="None known",
             existing_asset_same_site="No")
    old = next(w for w in world.background if w["work_id"] == "WF-OLD-HALL")
    loc = old["cost_form"]["sites"][0]["location"]
    p["latitude"], p["longitude"] = f"{loc['lat'] + 10 * METRE:.6f}", f"{loc['lon']:.6f}"
    res = run(world, work_of(p, {}, world.place, world.as_of))
    return still(res, "dup_split", "SANCTIONED_WORK_AT_THIS_SITE", "a 'new' hall 10 m from the old")


@probe("dup_split", "evasion", "the road's far end left out of the form")
def _(world):
    p = form_of(world, "dup_pin")
    p["end_lat"] = p["end_lon"] = ""
    res = run(world, work_of(p, {}, world.place, world.as_of))
    got = flags(res, "dup_split")
    r = res["dup_split"]
    told = "end" in said(res, "dup_split").lower()
    return ("PASS" if got or (told and r.status != Status.ASSESSED) or told else "FAIL",
            f"{got or 'nothing'} ({r.status.value}); says an end is missing: {told}")


@probe("dup_split", "evasion", "a map pin at (0, 0), or latitude and longitude swapped")
def _(world):
    out = []
    for name, lat, lon in (("zero", "0", "0"), ("swapped", None, None)):
        p = form_of(world, "dup_pin")
        if name == "zero":
            for k in ROAD_PINS:
                p[k] = lat
            for k in ("longitude", "start_lon", "end_lon"):
                p[k] = lon
        else:
            for a, b in (("latitude", "longitude"), ("start_lat", "start_lon"),
                         ("end_lat", "end_lon")):
                p[a], p[b] = p[b], p[a]
        res = run(world, work_of(p, {}, world.place, world.as_of))
        told = any(w in said(res, "dup_split").lower() for w in ("outside", "not in", "pin"))
        out.append((name, flags(res, "dup_split"), told))
    ok = all(got or told for _, got, told in out)
    return ("PASS" if ok else "FAIL", "; ".join(f"{n}: {g or 'nothing'}, says the pin is wrong: "
                                                f"{t}" for n, g, t in out))


@probe("dup_split", "evasion", "pins moved 60 m off the real site")
def _(world):
    p = _shift(form_of(world, "dup_pin"), ROAD_PINS, 60)
    res = run(world, work_of(p, {}, world.place, world.as_of))
    got = flags(res, "dup_split")
    return ("PASS" if got else "LIMIT",
            f"{got or 'nothing'}: two pins 50 m apart are one site by rule; a pin off the real "
            "site is for Site Progress to see (the videos are filmed where the work is)")


@probe("dup_split", "evasion", "split into pieces each 95% of the limit (under the 96% rule)")
def _(world):
    extra = []
    for k in ("WF-SPLIT-1", "WF-SPLIT-3"):
        w = copy.deepcopy(next(x for x in world.background if x["work_id"] == k))
        w["amount"] = 475_000.0
        extra.append(w)
    w = copy.deepcopy(world.records["dup_split"])
    w["amount"] = 475_000.0
    res = run(world, w, extra=extra, drop=("WF-SPLIT-1", "WF-SPLIT-3"))
    got = flags(res, "dup_split")
    return ("PASS" if got else "LIMIT",
            f"{got or 'nothing'}: the 96-100% rule read 12 of 14 right; looser splits read 18 of "
            "32 (T100), so they stay unasked")


@probe("dup_split", "noise", "split pieces filed by three differently-spelled agencies: still asked")
def _(world):
    extra = []
    for k, ag in (("WF-SPLIT-1", "Gramin Path Nigam Div-1"), ("WF-SPLIT-3", "G.P. Nigam")):
        w = copy.deepcopy(next(x for x in world.background if x["work_id"] == k))
        w["agency_name"] = ag
        extra.append(w)
    res = run(world, world.records["dup_split"], extra=extra, drop=("WF-SPLIT-1", "WF-SPLIT-3"))
    return still(res, "dup_split", "SPLIT_JUST_UNDER_LIMIT", "agency names differ")


# ===================================================================================================
# Time & Rules
# ===================================================================================================

@probe("time_rules", "evasion", "the late hall: start month declared two years after sanction")
def _(world):
    p = form_of(world, "time_late")
    p["expected_start_date"] = (date.fromisoformat(p["sanction_date"])
                                + timedelta(days=730)).isoformat()
    res = run(world, work_of(p, record_of(world, "time_late"), world.place, world.as_of))
    return still(res, "time_rules", "PAST_PROMISED_TIME", "start promised 2 years after sanction")


@probe("time_rules", "evasion", "the late hall: 10 years promised")
def _(world):
    p = form_of(world, "time_late")
    p["estimated_duration_days"] = "3650"
    res = run(world, work_of(p, record_of(world, "time_late"), world.place, world.as_of))
    return still(res, "time_rules", "PAST_PROMISED_TIME", "estimate 3,650 days")


@probe("time_rules", "evasion", "the late hall: 30 'lost months' declared on the native form")
def _(world):
    w = copy.deepcopy(world.records["time_late"])
    w["cost_form"]["sites"][0].setdefault("site_conditions", {})["lost_months"] = [
        f"{y}-{m:02d}" for y in (2025, 2026, 2027) for m in range(1, 11)]
    res = run(world, w)
    return still(res, "time_rules", "PAST_PROMISED_TIME", "30 lost months")


@probe("time_rules", "evasion", "the 6-day road: one reused video 'shows' work going on")
def _(world):
    w = copy.deepcopy(world.records["time_fast"])
    san = date.fromisoformat(world.examples["time_fast"]["form"]["sanction_date"])
    w["site_visits"] = [wf.visit(1, "baseline", san + timedelta(days=1)),
                        wf.visit(2, "monthly", san + timedelta(days=4), "changed",
                                 "concrete laid", "shown",
                                 reused_from=[{"work_id": "WF-CLEAN-1", "visit_id": "V3",
                                               "frames": 60}])]
    res = run(world, w)
    return still(res, "time_rules", "FINISHED_TOO_FAST", "a reused video before completion")


@probe("time_rules", "noise", "dates with times and status in lower case: same answer")
def _(world):
    bad = []
    for key in ("time_fast", "time_late", "clean"):
        w = copy.deepcopy(world.records[key])
        for k in ("recommended_date", "sanction_date", "completed_date"):
            if isinstance(w.get(k), str):
                w[k] = w[k] + "T10:30:00"
        w["status"] = str(w.get("status") or "").lower()
        res = run(world, w)
        if flags(res, "time_rules") != sorted(world.examples[key]["codes"].get("time_rules", [])):
            bad.append((key, flags(res, "time_rules")))
    return ("PASS" if not bad else "FAIL", f"changed: {bad or 'none'}")


@probe("time_rules", "scarce", "complete with no completion date: says so, asks nothing wrong")
def _(world):
    w = copy.deepcopy(world.records["time_fast"])
    w["completed_date"] = None
    res = run(world, w)
    told = "date" in " ".join(res["time_rules"].limitations).lower()
    got = flags(res, "time_rules")
    return ("PASS" if told and "PAST_PROMISED_TIME" not in got else "FAIL",
            f"{got or 'nothing'}; says the completion date is missing: {told}")


# ===================================================================================================
# Site Progress
# ===================================================================================================

def _site(world, key: str, visits: list[dict] | None, **record) -> dict:
    rec = record_of(world, key)
    rec.update(record)
    if visits is not None:
        rec["site_visits"] = visits
    else:
        rec.pop("site_visits", None)
    return work_of(form_of(world, key), rec, world.place, world.as_of)


@probe("site_progress", "evasion", "sanctioned months ago, never filmed")
def _(world):
    res = run(world, _site(world, "site_claim", None))
    got = flags(res, "site_progress")
    return ("PASS" if got else "FAIL",
            f"{got or 'nothing'} ({res['site_progress'].status.value}); sanctioned "
            f"{world.examples['site_claim']['form']['sanction_date']}, no video")


@probe("site_progress", "evasion", "every video uploaded unsealed (none accepted)")
def _(world):
    vs = copy.deepcopy(world.examples["site_claim"]["record"]["site_visits"])
    for v in vs:
        v["readings"]["sealed"] = False
    res = run(world, _site(world, "site_claim", vs))
    got = flags(res, "site_progress")
    return ("PASS" if got else "FAIL", f"{got or 'nothing'} ({res['site_progress'].status.value})")


@probe("site_progress", "evasion", "'can't tell' slipped between two 'not shown' claims")
def _(world):
    vs = copy.deepcopy(world.examples["site_claim"]["record"]["site_visits"])
    last = date.fromisoformat(vs[-1]["captured_at"])
    vs.insert(4, wf.visit(9, "monthly", last - timedelta(days=15), "cant_tell",
                          "roof slab cast", "cant_tell"))
    vs[-1]["captured_at"] = (last + timedelta(days=15)).isoformat()
    res = run(world, _site(world, "site_claim", vs))
    return still(res, "site_progress", "CLAIM_NOT_SHOWN", "not shown, can't tell, not shown")


@probe("site_progress", "evasion", "every claim vague ('work in progress')")
def _(world):
    vs = copy.deepcopy(world.examples["site_claim"]["record"]["site_visits"])
    for v in vs[1:]:
        v["claim"] = "Work in progress"
        v["readings"]["claim_verdict"] = "cant_tell"
    res = run(world, _site(world, "site_claim", vs))
    told = "vague" in said(res, "site_progress").lower() or "specific" in \
        said(res, "site_progress").lower()
    return ("PASS" if told else "FAIL", f"{flags(res, 'site_progress') or 'nothing'}; asks for a "
            f"specific claim: {told}")


@probe("site_progress", "evasion", "the form's pin is not where every video is filmed")
def _(world):
    vs = copy.deepcopy(world.examples["clean"]["record"]["site_visits"])
    for v in vs:
        v["readings"].update(gps_inside=False, gps_distance_m=320.0)
    res = run(world, _site(world, "clean", vs))
    got = flags(res, "site_progress")
    return ("PASS" if got else "FAIL", f"{got or 'nothing'}: three videos all 320 m from the pin, "
            "views matching each other")


@probe("site_progress", "evasion", "a video dated after today")
def _(world):
    vs = copy.deepcopy(world.examples["clean"]["record"]["site_visits"])
    vs.append(wf.visit(4, "monthly", world.as_of + timedelta(days=40), "changed",
                       "road complete", "shown"))
    res = run(world, _site(world, "clean", vs))
    told = "future" in said(res, "site_progress").lower() or "after today" in \
        said(res, "site_progress").lower()
    return ("PASS" if told else "FAIL", f"{flags(res, 'site_progress') or 'nothing'}; says the "
            f"date is wrong: {told}")


@probe("site_progress", "noise", "visits listed in another order, one listed twice: same answer")
def _(world):
    bad = []
    for key in ("clean", "site_claim", "site_elsewhere"):
        vs = copy.deepcopy(world.examples[key]["record"]["site_visits"])[::-1]
        vs.append(copy.deepcopy(vs[0]))
        res = run(world, _site(world, key, vs))
        if flags(res, "site_progress") != sorted(world.examples[key]["codes"].get(
                "site_progress", [])):
            bad.append((key, flags(res, "site_progress")))
    return ("PASS" if not bad else "FAIL", f"changed: {bad or 'none'}")


@probe("site_progress", "evasion", "GPS faked inside the site, views elsewhere")
def _(world):
    vs = copy.deepcopy(world.examples["site_elsewhere"]["record"]["site_visits"])
    vs[-1]["readings"].update(gps_inside=True, gps_distance_m=0)
    res = run(world, _site(world, "site_elsewhere", vs))
    got = flags(res, "site_progress")
    return ("PASS" if got else "LIMIT", f"{got or 'nothing'}: one video with one proof (the "
            "views) is a note by design; two such videos in a row are asked (SITE_VIDEOS_UNUSABLE, "
            "round 6)")


# ===================================================================================================
# round 4 (after the first fixes): honest cases the fixes must not catch, and harder evasions
# ===================================================================================================

def _lines_total(p: dict) -> float:
    return sum(float(r["qty"] or 0) * float(r["rate"] or 0) for r in boq(p))


@probe("cost_estimate", "noise", "GST 'added separately', 18% in other charges: honest, not asked")
def _(world):
    p = form_of(world, "clean")
    p["tax_treatment"] = "Added separately"
    p["other_charges"] = f"{0.18 * _lines_total(p):.0f}"
    res = run(world, work_of(retotal(p), record_of(world, "clean"), world.place, world.as_of))
    return quiet(res, "cost_estimate", "18% GST in other charges")


@probe("cost_estimate", "noise", "a 2% lump sum for sundries: honest, not asked")
def _(world):
    p = form_of(world, "clean")
    p["lumpsum_components"] = f"{0.02 * _lines_total(p):.0f}"
    res = run(world, work_of(retotal(p), record_of(world, "clean"), world.place, world.as_of))
    return quiet(res, "cost_estimate", "2% lump sum")


@probe("cost_estimate", "noise", "a typed extra zero (cement Rs 3,800 a bag), not explained")
def _(world):
    p = form_of(world, "clean")
    rows = boq(p)
    rows[0]["rate"] = "3800"
    p = retotal(set_boq(p, rows))
    p["mp_recommended_amount"] = p["mplads_share"]   # the MP's figure as on the estimate
    res = run(world, work_of(p, record_of(world, "clean"), world.place, world.as_of))
    told = "typing mistake" in said(res, "cost_estimate")
    got = flags(res, "cost_estimate")
    return ("PASS" if not got and told else "FAIL",
            f"{got or 'no question'}; says a line was held as a likely typing mistake: {told}")


@probe("cost_estimate", "evasion", "padded items given units that do not fit them")
def _(world):
    p = form_of(world, "cost_padded")
    rows = boq(p)
    rows[0]["unit"] = "nos"                         # cement in "numbers"
    res = run(world, work_of(set_boq(p, rows), record_of(world, "cost_padded"), world.place,
                             world.as_of))
    return still(res, "cost_estimate", "ESTIMATE_ABOVE_FAIR_PRICE", "cement in nos")


def _elsewhere(world, key: str, factor: float | None = None) -> dict:
    """The filing moved to another district of the state, where no form was ever filed (a late
    filing: only forms filed before it count)."""
    p = form_of(world, key)
    if factor is not None:
        rows = boq(p)
        for r in rows:
            fair = honest_rate(r["desc"])
            if fair:
                r["rate"] = f"{fair * factor:.0f}"
        p = retotal(set_boq(p, rows))
        p["mp_recommended_amount"] = p["mplads_share"]   # the MP's figure as on the estimate
    place = {**world.place, "district_lgd": "UTTAR PRADESH|NEWPUR", "district_name": "Newpur"}
    return work_of(p, record_of(world, key), place, world.as_of)


@probe("cost_estimate", "scarce", "a district with no forms: the state's forms stand in")
def _(world):
    honest = run(world, _elsewhere(world, "cost_padded", 1.0))
    far = run(world, _elsewhere(world, "cost_padded", 1.5))
    src = " ".join((honest["cost_estimate"].evidence or {}).get("whole", {}).get("sources") or [])
    ok = (not flags(honest, "cost_estimate") and "ESTIMATE_ABOVE_FAIR_PRICE"
          in flags(far, "cost_estimate") and "across the state" in src)
    return ("PASS" if ok else "FAIL", f"honest: {flags(honest, 'cost_estimate') or 'nothing'}; "
            f"+50%: {flags(far, 'cost_estimate') or 'nothing'}; priced from: {src[:90]}")


@probe("cost_estimate", "evasion", "22% padding where only the state's forms can price it")
def _(world):
    res = run(world, _elsewhere(world, "cost_padded", 1.22))
    got = flags(res, "cost_estimate")
    return ("PASS" if got else "LIMIT",
            f"{got or 'nothing'}: a state-wide rate carries 10% for local prices, so padding is "
            "asked from about 27% there; the district's own forms (or the SoR, T096) ask from 15%")


@probe("cost_estimate", "evasion", "every agency in the district pads 22% together")
def _(world):
    bg = _scatter(world, lambda i: 1.22)
    res = run(world, world.records["cost_padded"], background=bg,
              drop=tuple(r["work_id"] for k, r in world.records.items() if k != "cost_padded"))
    got = flags(res, "cost_estimate")
    return ("PASS" if got else "LIMIT",
            f"{got or 'nothing'}: when every agency raises its rates together, only the state's "
            "Schedule of Rates (T096, not loaded yet) can cap the district's own rate")


@probe("dup_split", "noise", "a hall at the old road's pin (another kind of work): not asked")
def _(world):
    p = form_of(world, "clean")
    old = next(w for w in world.background if w["work_id"] == "WF-OLD-ROAD")
    loc = old["cost_form"]["sites"][0]["location"]
    h = form_of(world, "time_late")
    h.update(recommendation_ref="WF-HALL-AT-ROAD", latitude=f"{loc['lat']:.6f}",
             longitude=f"{loc['lon']:.6f}", sanction_decision="", sanction_date="")
    res = run(world, work_of(h, {}, world.place, world.as_of))
    del p
    got = [c for c in flags(res, "dup_split") if c == "SANCTIONED_WORK_AT_THIS_SITE"]
    return ("PASS" if not got else "FAIL", f"{got or 'nothing'}")


@probe("dup_split", "noise", "pins rounded to 4 decimals (about 11 m): same answers")
def _(world):
    bad = []
    for key in ("dup_pin", "clean"):
        p = form_of(world, key)
        for k in ROAD_PINS + ("longitude", "start_lon", "end_lon"):
            if p.get(k):
                p[k] = f"{round(float(p[k]), 4):.4f}"
        res = run(world, work_of(p, record_of(world, key), world.place, world.as_of))
        if flags(res, "dup_split") != sorted(world.examples[key]["codes"].get("dup_split", [])):
            bad.append((key, flags(res, "dup_split")))
    return ("PASS" if not bad else "FAIL", f"changed: {bad or 'none'}")


@probe("time_rules", "scarce", "completion dated after today: no false question, says so")
def _(world):
    w = copy.deepcopy(world.records["time_fast"])
    w["completed_date"] = (world.as_of + timedelta(days=20)).isoformat()
    res = run(world, w)
    got = flags(res, "time_rules")
    told = any(w in said(res, "time_rules") for w in ("after today", "future",
                                                      "after the data was published"))
    return ("PASS" if "FINISHED_TOO_FAST" not in got and told else "FAIL",
            f"{got or 'nothing'}; says the date is after today: {told}")


@probe("time_rules", "scarce", "an estimate of 0 days: no false question, says so")
def _(world):
    p = form_of(world, "time_late")
    p["estimated_duration_days"] = "0"
    res = run(world, work_of(p, record_of(world, "time_late"), world.place, world.as_of))
    got = flags(res, "time_rules")
    told = "estimated time" in said(res, "time_rules")
    return ("PASS" if "FINISHED_TOO_FAST" not in got and told else "FAIL",
            f"{got or 'nothing'}; says the estimate is missing: {told}")


@probe("site_progress", "noise", "one video with a bad GPS fix (300 m off), views fine: not asked")
def _(world):
    vs = copy.deepcopy(world.examples["clean"]["record"]["site_visits"])
    vs[1]["readings"].update(gps_inside=False, gps_distance_m=300.0)
    res = run(world, _site(world, "clean", vs))
    return quiet(res, "site_progress", "one GPS-off video")


@probe("site_progress", "noise", "sanctioned 50 days ago, first video not yet due: not asked")
def _(world):
    p = form_of(world, "site_claim")
    san = world.as_of - timedelta(days=50)
    p.update(sanction_date=san.isoformat(), expected_start_date=san.isoformat())
    res = run(world, work_of(p, {"status": "SANCTIONED"}, world.place, world.as_of))
    return quiet(res, "site_progress", "50 days, no video")


# ===================================================================================================
# round 5: production scale, other languages, the edges of the time rules, the size claim
# ===================================================================================================

@probe("dup_split", "scale", "3,000 filed roads in one district: one check stays under 2 s")
def _(world):
    import time as clock
    rng = random.Random(3)
    base = world.background[0]
    many = []
    for i in range(3000):
        w = copy.deepcopy(base)
        w["work_id"] = f"WF-MANY-{i}"
        loc = w["cost_form"]["sites"][0]["location"]
        dlat, dlon = rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3)
        for k in ("lat", "end_lat"):
            loc[k] = loc[k] + dlat
        for k in ("lon", "end_lon"):
            loc[k] = loc[k] + dlon
        many.append(w)
    ctx = Context(stats=world.stats, as_of=world.as_of,
                  data=indexes(world.district + world.background + many
                               + list(world.records.values())))
    t0 = clock.perf_counter()
    a = assess_work(world.records["dup_pin"], ctx)
    took = clock.perf_counter() - t0
    got = sorted(f.code for r in a.agents if r.agent == "dup_split" for f in r.findings
                 if f.risk > 0)
    ok = took < 2.0 and "SANCTIONED_WORK_AT_THIS_SITE" in got
    return ("PASS" if ok else "FAIL", f"{took:.2f} s for the four agents; {got}")


@probe("cost_estimate", "noise", "items written in Hindi: same answers")
def _(world):
    hindi = {"Cement OPC 43 grade": "सीमेंट (ओपीसी 43)", "Coarse sand": "मौरंग / बालू",
             "Stone aggregate 20 mm": "गिट्टी 20 मिमी"}
    bad = []
    for key in ("clean", "cost_padded"):
        p = form_of(world, key)
        rows = boq(p)
        for r in rows:
            r["desc"] = hindi.get(r["desc"], r["desc"])
        res = run(world, work_of(set_boq(p, rows), record_of(world, key), world.place,
                                 world.as_of))
        if flags(res, "cost_estimate") != sorted(world.examples[key]["codes"].get(
                "cost_estimate", [])):
            bad.append((key, flags(res, "cost_estimate")))
    return ("PASS" if not bad else "FAIL", f"changed: {bad or 'none'}")


@probe("time_rules", "evasion", "'complete' just past the 30-day floor, never filmed")
def _(world):
    w = copy.deepcopy(world.records["time_fast"])
    san = date.fromisoformat(world.examples["time_fast"]["form"]["sanction_date"])
    w["completed_date"] = (san + timedelta(days=35)).isoformat()
    res = run(world, w)
    got = flags(res, "time_rules") + flags(res, "site_progress")
    return ("PASS" if got else "FAIL",
            f"{got or 'nothing'}: Time's floor is passed, but no site video was ever filmed")


@probe("cost_estimate", "evasion", "a bigger size claimed (7 m wide road) to justify the cement")
def _(world):
    p = form_of(world, "cost_quantity")
    p["road_width_m"] = "7"
    res = run(world, work_of(p, record_of(world, "cost_quantity"), world.place, world.as_of))
    got = flags(res, "cost_estimate")
    return ("PASS" if {"MATERIAL_QUANTITY_ABOVE_SIZE", "SIZE_NOT_AS_DESCRIBED"} & set(got)
            else "FAIL", f"{got or 'nothing'}: the form's own scope still says 3.5 m wide")


@probe("cost_estimate", "evasion", "a bigger size claimed everywhere (field and scope both 7 m)")
def _(world):
    p = form_of(world, "cost_quantity")
    p["road_width_m"] = "7"
    p["scope_of_work"] = p["scope_of_work"].replace("3.5 m wide", "7 m wide")
    res = run(world, work_of(p, record_of(world, "cost_quantity"), world.place, world.as_of))
    got = flags(res, "cost_estimate")
    return ("PASS" if got else "LIMIT",
            f"{got or 'nothing'}: a size claimed the same way everywhere is the agency's word; "
            "the site videos and the officer's visit check it, not the estimate")


# ===================================================================================================
# round 6 (T136): just past a line, lines nobody prices, renamed pieces, and room for error on site
# ===================================================================================================

def _honest(world, key: str, edit) -> dict:
    """The example's form with `edit(rows)` applied to its BOQ, the MP's figure moved with it."""
    p = form_of(world, key)
    rows = boq(p)
    edit(rows)
    set_boq(p, rows)
    p["mp_recommended_amount"] = f"{float(p['technical_estimate']):.0f}"
    return work_of(p, record_of(world, key), world.place, world.as_of)


@probe("cost_estimate", "evasion", "an equipment-hire line raised from 30 days to 250")
def _(world):
    def edit(rows):
        for r in rows:
            if "mixer" in r["desc"].lower():
                r["qty"] = "250"
    res = run(world, _honest(world, "clean", edit))
    return still(res, "cost_estimate", "ESTIMATE_ABOVE_FAIR_PRICE",
                 "Rs 5.5 lakh more in a line no reader prices")


@probe("cost_estimate", "noise", "honest unread items (earthwork, shuttering, curing ~10%): quiet")
def _(world):
    def edit(rows):
        rows += [{"desc": "Earthwork in excavation and filling for the subgrade", "unit": "cum",
                  "qty": "160", "rate": "220", "source": "District recent rates"},
                 {"desc": "Shuttering for the slab edges", "unit": "sqm", "qty": "95",
                  "rate": "380", "source": "District recent rates"},
                 {"desc": "Curing for 14 days", "unit": "sqm", "qty": "1050", "rate": "18",
                  "source": "District recent rates"}]
    return quiet(run(world, _honest(world, "clean", edit)), "cost_estimate",
                 "earthwork, shuttering and curing lines")


@probe("cost_estimate", "evasion", "sand and aggregate quantities doubled")
def _(world):
    def edit(rows):
        for r in rows:
            if "sand" in r["desc"].lower() or "aggregate" in r["desc"].lower():
                r["qty"] = f"{float(r['qty']) * 2:g}"
    return still(run(world, _honest(world, "clean", edit)), "cost_estimate",
                 "MATERIAL_QUANTITY_ABOVE_SIZE", "twice the sand")


@probe("cost_estimate", "evasion", "labour days multiplied by 2.5")
def _(world):
    def edit(rows):
        for r in rows:
            if "mason" in r["desc"].lower() or "labourer" in r["desc"].lower():
                r["qty"] = f"{float(r['qty']) * 2.5:g}"
    got = flags(run(world, _honest(world, "clean", edit)), "cost_estimate")
    return ("PASS" if got else "LIMIT",
            f"{got or 'nothing'}: labour days per m3 are not normed yet (CPWD's Analysis of "
            "Rates gives them, T096); the site videos show the pace of work")


@probe("cost_estimate", "noise", "rates written 'Rs 464/-' and quantities with spaces")
def _(world):
    p = form_of(world, "cost_padded")
    for k in [k for k in p if k.startswith("boq_rate_")]:
        p[k] = f"Rs {p[k]}/-"
    for k in [k for k in p if k.startswith("boq_qty_")]:
        p[k] = f" {p[k]} "
    res = run(world, work_of(p, record_of(world, "cost_padded"), world.place, world.as_of))
    got = flags(res, "cost_estimate")
    return ("PASS" if got == ["ESTIMATE_ABOVE_FAIR_PRICE"] else "FAIL",
            f"{got or 'nothing'} ({res['cost_estimate'].status.value})")


@probe("cost_estimate", "evasion", "rates written as words ('see attached'): never a clean chit")
def _(world):
    p = form_of(world, "cost_padded")
    for k in [k for k in p if k.startswith("boq_rate_")]:
        p[k] = "see attached"
    res = run(world, work_of(p, record_of(world, "cost_padded"), world.place, world.as_of))
    st = res["cost_estimate"].status
    return ("PASS" if st == Status.NOT_ASSESSABLE else "FAIL",
            f"{st.value}: {res['cost_estimate'].headline[:90]}")


@probe("dup_split", "evasion", "a 'new' hall pinned 60 m from the old (just past the 50 m line)")
def _(world):
    lat, _lon = wf.pin(6)
    p = form_of(world, "dup_rebuild")
    p.update(work_nature="New asset", prior_work_id="", prior_completion_date="",
             repeat_reason="", known_nearby_work_ids="", existing_asset_same_site="No",
             nearby_work_relationship="None known", latitude=f"{lat + 60 * METRE:.6f}")
    res = run(world, work_of(p, {}, world.place, world.as_of))
    noted = any(f.code == "NEAR_SANCTIONED_WORK" for f in res["dup_split"].findings)
    return ("PASS" if noted else "FAIL",
            f"note: {noted}; a pin past 50 m is another site by rule, so it is named in a note "
            "and the first site video (the hall already standing) settles it")


@probe("dup_split", "evasion", "split with the checked piece called a paver road / 'Other'")
def _(world):
    bad = []
    for sub in ("Paver block road", "Other", "Gravel / WBM"):
        p = form_of(world, "dup_split")
        p["road_subtype"] = sub
        p["work_title"] = p["work_title"].replace("CC road", sub)
        got = flags(run(world, work_of(p, {}, world.place, world.as_of)), "dup_split")
        if "SPLIT_JUST_UNDER_LIMIT" not in got:
            bad.append((sub, got))
    return ("PASS" if not bad else "FAIL", f"missed: {bad or 'none'} (pieces end to end by pin)")


@probe("dup_split", "evasion", "split with each piece described in other words")
def _(world):
    words = ["Lane paving from the main road", "Concrete surface, harijan basti approach",
             "Road work near the panchayat ground"]
    p = form_of(world, "dup_split")
    p["work_title"] = words[1]
    p["scope_of_work"] = words[1] + ", 95 m long, 3.5 m wide, 150 mm M20 over WBM."
    got = flags(run(world, work_of(p, {}, world.place, world.as_of)), "dup_split")
    return ("PASS" if "SPLIT_JUST_UNDER_LIMIT" in got else "FAIL",
            f"{got or 'nothing'}: the pieces still meet end to end by their pins")


@probe("time_rules", "evasion", "'complete' past the early line, checked the next day, never filmed")
def _(world):
    w = copy.deepcopy(world.records["time_fast"])
    san = date.fromisoformat(world.examples["time_fast"]["form"]["sanction_date"])
    w["completed_date"] = (san + timedelta(days=50)).isoformat()
    saved = world.as_of
    world.as_of = san + timedelta(days=51)
    try:
        res = run(world, w)
    finally:
        world.as_of = saved
    got = flags(res, "time_rules") + flags(res, "site_progress")
    return ("PASS" if "NO_SITE_VIDEO" in got else "FAIL",
            f"{got or 'nothing'}: complete with not one site video is asked at once")


def _clean_visits(world) -> list[dict]:
    return copy.deepcopy(world.examples["clean"]["record"]["site_visits"])


DARK = {"quality_ok": False, "views_match_site": None, "change": "cant_tell",
        "claim_verdict": "cant_tell", "viewpoints_matched": 0}


@probe("site_progress", "noise", "one dark video between good ones: a note, not a question")
def _(world):
    vs = _clean_visits(world)
    vs[1]["readings"].update(DARK)
    res = run(world, _site(world, "clean", vs))
    return quiet(res, "site_progress", "one dark month")


@probe("site_progress", "evasion", "the last two videos dark / viewpoints not filmed")
def _(world):
    vs = _clean_visits(world)
    vs[1]["readings"].update(DARK)
    vs[2]["readings"].update(views_match_site=None, viewpoints_matched=1, change="cant_tell")
    res = run(world, _site(world, "clean", vs))
    return still(res, "site_progress", "SITE_VIDEOS_UNUSABLE", "two unusable in a row")


@probe("site_progress", "noise", "weak GPS on every video, a viewpoint skipped: not asked")
def _(world):
    vs = _clean_visits(world)
    for v in vs:
        v["readings"].update(gps_weak=True, gps_inside=None, gps_distance_m=None)
    vs[2]["readings"].update(viewpoints_skipped=["v4"], viewpoints_matched=4)
    return quiet(run(world, _site(world, "clean", vs)), "site_progress", "weak GPS, v4 skipped")


@probe("site_progress", "noise", "a dark video with its GPS off the site: never 'filmed elsewhere'")
def _(world):
    vs = _clean_visits(world)
    vs[2]["readings"].update(quality_ok=False, gps_inside=False, gps_distance_m=800.0,
                             views_match_site=False)
    got = flags(run(world, _site(world, "clean", vs)), "site_progress")
    return ("PASS" if "NOT_FILMED_AT_THIS_SITE" not in got else "FAIL",
            f"{got or 'nothing'}: a dark video is no proof of anything")


@probe("site_progress", "evasion", "'not shown', a dark video, 'not shown': still twice in a row")
def _(world):
    vs = copy.deepcopy(world.examples["site_claim"]["record"]["site_visits"])
    dark = copy.deepcopy(vs[-1])
    dark["visit_id"] = "V4b"
    dark["captured_at"] = (date.fromisoformat(vs[3]["captured_at"][:10])
                           + timedelta(days=15)).isoformat()
    dark["readings"].update(DARK)
    vs.insert(4, dark)
    return still(run(world, _site(world, "site_claim", vs)), "site_progress", "CLAIM_NOT_SHOWN",
                 "a dark video slipped between the two")


@probe("site_progress", "evasion", "views never match while the GPS says 'at the site', twice")
def _(world):
    vs = _clean_visits(world)
    for v in vs[1:]:
        v["readings"].update(views_match_site=False, viewpoints_matched=0, change="cant_tell",
                             claim_verdict="cant_tell")
    return still(run(world, _site(world, "clean", vs)), "site_progress", "SITE_VIDEOS_UNUSABLE",
                 "GPS faked inside, another place filmed")


# ===================================================================================================
# damage: random junk anywhere
# ===================================================================================================

JUNK = [None, "", " ", "abc", "NaN", float("nan"), float("inf"), -1, 0, 1e15, -1e9, "1,00,000",
        "₹5 lakh", [], {}, [1, 2], {"x": 1}, True, "2026-02-30", "31/12/2025", "9999-99-99",
        "मंदिर", "\u0000", "x" * 3000, 12.5, "12.5", "-0", "1e400"]


def _damage_form(rng: random.Random, p: dict) -> dict:
    for k in rng.sample(sorted(p), k=min(len(p), rng.randint(1, 25))):
        p[k] = rng.choice(JUNK)
    return p


def _damage_engine(rng: random.Random, w: dict) -> dict:
    """Junk inside the engine's own form, visits and record (the API and the batch paths)."""
    def walk(x, depth=0):
        if isinstance(x, dict):
            for k in list(x):
                if rng.random() < 0.15:
                    x[k] = rng.choice(JUNK)
                else:
                    walk(x[k], depth + 1)
        elif isinstance(x, list):
            for i in range(len(x)):
                if rng.random() < 0.15:
                    x[i] = rng.choice(JUNK)
                else:
                    walk(x[i], depth + 1)
    for k in ("cost_form", "site_visits"):
        walk(w.get(k))
    for k in ("amount", "status", "sanction_date", "completed_date", "recommended_date",
              "work_type_code", "agency_name"):
        if rng.random() < 0.2:
            w[k] = rng.choice(JUNK)
    return w


def damage_rounds(world: World, n: int, seed: int) -> dict:
    rng = random.Random(seed)
    keys = sorted(world.examples)
    ctx = Context(stats=world.stats, as_of=world.as_of,
                  data=indexes(world.district + world.background
                               + list(world.records.values())))
    errors: Counter = Counter()
    contract: list[str] = []
    twice: list[str] = []
    samples: list[str] = []
    for i in range(n):
        key = rng.choice(keys)
        if i % 2:
            p = _damage_form(rng, form_of(world, key))
            try:
                w = work_of(p, record_of(world, key), world.place, world.as_of)
            except Exception as exc:                     # the adapter itself must not break
                errors[f"pswif: {type(exc).__name__}: {str(exc)[:80]}"] += 1
                continue
        else:
            w = _damage_engine(rng, copy.deepcopy(world.records[key]))
        a = assess_work(copy.deepcopy(w), ctx)
        for r in a.agents:
            if r.agent not in AGENTS:
                continue
            if r.status == Status.ERROR:
                errors[f"{r.agent}: {r.headline[:120]}"] += 1
                if len(samples) < 6:
                    samples.append(f"{key} #{i}: {r.agent}: {r.headline[:200]}")
            if not (0.0 <= r.risk <= 1.0) or any(not (0 <= f.risk <= 1) for f in r.findings):
                contract.append(f"{key} #{i} {r.agent}")
        b = assess_work(copy.deepcopy(w), ctx)
        if [(r.agent, r.status, tuple(sorted(f.code for f in r.findings))) for r in a.agents] \
                != [(r.agent, r.status, tuple(sorted(f.code for f in r.findings)))
                    for r in b.agents]:
            twice.append(f"{key} #{i}")
    return {"runs": n, "errors": dict(errors), "contract": contract, "different_twice": twice,
            "samples": samples}


# ===================================================================================================

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--damage", type=int, default=400, help="random damage runs")
    ap.add_argument("--seed", type=int, default=2026)
    ap.add_argument("--only", default="", help="run probes whose name contains this")
    args = ap.parse_args()
    world = build_world()
    rows = []
    for pr in PROBES:
        if args.only and args.only not in pr.name:
            continue
        try:
            verdict, detail = pr.fn(world)
        except Exception as exc:          # a probe that breaks is a FAIL of the agent under it
            verdict, detail = "FAIL", f"the probe raised {type(exc).__name__}: {exc}"
        rows.append({"agent": pr.agent, "kind": pr.kind, "probe": pr.name, "verdict": verdict,
                     "detail": detail})
        print(f"{verdict:5} {pr.agent:13} {pr.kind:8} {pr.name}\n      {detail}", flush=True)
    dmg = damage_rounds(world, args.damage, args.seed) if args.damage and not args.only else None
    tally = Counter(r["verdict"] for r in rows)
    lines = [f"Agent robustness loop (T135, T136): {len(rows)} probes on the work form's example "
             f"filings in {wf.DISTRICT} ({len(world.district):,} real works, "
             f"{len(world.background)} background filings), as of {world.as_of}",
             f"PASS {tally['PASS']}  FAIL {tally['FAIL']}  LIMIT {tally['LIMIT']}", ""]
    for agent in AGENTS:
        lines.append(f"== {agent}")
        for r in rows:
            if r["agent"] == agent:
                lines.append(f"  {r['verdict']:5} {r['kind']:8} {r['probe']}")
                lines.append(f"        {r['detail']}")
    if dmg:
        lines += ["", f"Random damage: {dmg['runs']} runs (seed {args.seed}), half through the "
                  "website form, half inside the engine's own form, visits and record",
                  f"  agent errors: {sum(dmg['errors'].values())} "
                  f"{json.dumps(dmg['errors'], ensure_ascii=False)[:600]}",
                  f"  contract broken: {len(dmg['contract'])}; a different answer the second "
                  f"time: {len(dmg['different_twice'])}"]
        lines += [f"  e.g. {s}" for s in dmg["samples"]]
    text = "\n".join(lines) + "\n"
    print("\n" + text)
    if not args.only:
        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.with_suffix(".txt").write_text(text, encoding="utf-8")
        OUT.with_suffix(".json").write_text(json.dumps({"probes": rows, "damage": dmg},
                                                       ensure_ascii=False, indent=1,
                                                       default=str) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
