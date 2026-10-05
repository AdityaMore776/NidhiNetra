r"""Agent architecture bake-off (T137): other designs tested against the current four agents.

The owner (5 Oct 2026): "test different agent architectures ... see which one runs the best and is
the most accurate, and also doesn't have any problems or loopholes ... only when it's proven to be
better then you switch it." The current agents stay as they are; every candidate here is run on the
same benchmarks, with the same honest-form false-alarm rate, so their catch rates compare fairly.

  cost     the whole-estimate decision. The current rule asks when the money gap is 15%+ of the
           fair price (and Rs 50,000+). Candidates read the same priced lines differently:
             gap_cal    the current statistic with its line set to the calibrated false-alarm rate
             z_equal    the mean of the lines' log excess over the fair rate, in units of the
                        district's own measured price spread (every line one vote)
             z_ivw      the same mean weighted by each material's precision (a tight-priced material
                        counts more than a scattered one)
             z_money    the money gap divided by its own expected honest scatter (the current
                        statistic, made aware of the spread)
             union      gap_cal or z_ivw (each at half the false-alarm budget)
             iforest    an isolation forest on the lines' log excess (machine learning, trained on
                        the district's other forms)
           on planted CC-road forms (data/trial/cost_whole_trial.py's generator): honest spreads of
           5, 10 and 15%, a mixed spread per material, a scarce district and the SoR; padding of
           every line +10/+15/+20/+30%, one line x2, two lines +40%.
  site     Site Progress's decision logic on simulated sites over 12 months, with a reader that
           errs as a real one would (dark videos, weak GPS, a claim judged "not shown" by mistake)
  dup      Duplicate Work: a spatial grid index against the current scan (same answers, timing)
  fusion   the score: the current noisy-OR against max, mean and log-odds sums

Writes results/architecture_bakeoff_<part>.txt and .json.
Run:  apps\engine\.venv\Scripts\python.exe data\trial\architecture_bakeoff.py cost
"""

from __future__ import annotations

import argparse
import json
import math
import random
import statistics
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
sys.path.insert(0, str(ROOT / "data" / "trial"))
import cost_whole_trial as cwt  # noqa: E402

from drishti.agents.cost_estimate import rates, whole  # noqa: E402

OUT = ROOT / "data" / "trial" / "results"
TARGET_FPR = 0.01            # each candidate's line is set so 1 in 100 honest forms is asked
MIN_SHARE = 0.05             # never ask about less than 5% (a minor difference is not a question)
SIGMA_FLOOR, SIGMA_DEFAULT = 0.03, 0.10
PER_AGENCY = 3               # at most this many recent forms of one agency in the spread


# ==================================================================================================
# Cost
# ==================================================================================================
#
# Honest forms vary in two ways (both ASSUMPTIONS until real forms, T098):
#   per line   each rate x exp(N(0, sigma)) (a shop, a quote, a rounding)
#   per form   a remote site, carriage, a bad road: honest, and it moves several lines together,
#              which is exactly what padding looks like. Two shapes: "carriage" moves the bulk
#              materials (sand, aggregate, GSB: priced at the site, by the truck) by one factor
#              exp(N(0, tau)); "+site" moves every line of the form by it (a stress test)

MIXED = {"cement": 0.04, "labour_skilled": 0.06, "labour_unskilled": 0.08, "aggregate": 0.10,
         "granular_base": 0.15, "sand": 0.20}
# (label, fair rate from, sigma, tau, other forms, other agencies, noisy agencies)
SCENARIOS = [
    ("district 5%", "district", 0.05, 0.0, 60, 12, 0),
    ("district 10%", "district", 0.10, 0.0, 60, 12, 0),
    ("district 15%", "district", 0.15, 0.0, 60, 12, 0),
    ("district mixed", "district", MIXED, 0.0, 60, 12, 0),
    ("district 5% +carriage 10%", "district", 0.05, ("bulk", 0.10), 60, 12, 0),
    ("district 10% +carriage 10%", "district", 0.10, ("bulk", 0.10), 60, 12, 0),
    ("district mixed +carriage 10%", "district", MIXED, ("bulk", 0.10), 60, 12, 0),
    ("district 5% +site 5%", "district", 0.05, 0.05, 60, 12, 0),
    ("district 10% +site 5%", "district", 0.10, 0.05, 60, 12, 0),
    ("scarce 10% +carriage 10%", "district", 0.10, ("bulk", 0.10), 8, 4, 0),
    ("district 10%, 3 noisy agencies", "district", 0.10, ("bulk", 0.10), 60, 12, 3),
    ("SoR 10% +carriage 10%", "sor", 0.10, ("bulk", 0.10), 0, 0, 0),
]
BULK = {"sand", "aggregate", "granular_base"}
PEERS_MIN_FORMS, PEERS_MIN_AGENCIES = 20, 5     # fewer: the peer line falls back to the current
PADDINGS = [
    ("every line +10%", {"every": 1.10}),
    ("every line +15%", {"every": 1.15}),
    ("every line +20%", {"every": 1.20}),
    ("every line +30%", {"every": 1.30}),
    ("cement rate x2", {"rate": {"cement": 2.0}}),
    ("cement and aggregate +40%", {"rate": {"cement": 1.4, "aggregate": 1.4}}),
    ("sand rate x2", {"rate": {"sand": 2.0}}),
]
CAP_LINE = whole.GAP_SHARE   # an adaptive line is never above the current 15% (never more lenient)
SCALE_FLOOR = 0.02           # the peers' scatter is never taken as tighter than this


def honest(rng: random.Random, sigma, tau=0.0) -> dict:
    """cost_whole_trial's honest road: one spread or a spread per material, and a per-form level
    on every line (tau a number) or on the bulk materials only (tau = ("bulk", t))."""
    f = cwt.honest(rng, 0.0)
    only, t = tau if isinstance(tau, tuple) else (None, tau)
    level = rng.gauss(0, t) if t else 0.0
    for ln in f["sites"][0]["lines"]:
        m = ln.get("material_id")
        if m in cwt.BASE:
            s = sigma[m] if isinstance(sigma, dict) else sigma
            shift = level if only is None or m in BULK else 0.0
            ln["rate"] = round(cwt.BASE[m][1] * math.exp(shift + rng.gauss(0, s)), 2)
    return f


def _robust(xs: list[float]) -> tuple[float, float]:
    c = statistics.median(xs)
    return c, 1.4826 * statistics.median(abs(x - c) for x in xs)


class Peers:
    """The district's other forms as honest company for a statistic: each form's rates against the
    other agencies' medians (one vote per agency, at most PER_AGENCY forms each)."""

    def __init__(self, others: list[dict]):
        self.forms = []
        per: dict[str, list[dict]] = defaultdict(list)
        for w in others:
            per[w["cost_form_meta"]["saved_by"]].append(w)
        meds: dict[str, dict[str, float]] = defaultdict(dict)        # material -> agency -> median
        for a, ws in per.items():
            by_m = defaultdict(list)
            for w in ws:
                for ln in w["cost_form"]["sites"][0]["lines"]:
                    if ln.get("material_id") in cwt.BASE:
                        by_m[ln["material_id"]].append(ln["rate"])
            for m, rs in by_m.items():
                meds[m][a] = statistics.median(rs)
        sig: dict[str, list[float]] = defaultdict(list)
        for a, ws in per.items():
            fair = {m: statistics.median(v for b, v in d.items() if b != a)
                    for m, d in meds.items() if len(d) > 1}
            for w in ws[:PER_AGENCY]:
                lines = [{"m": ln["material_id"], "r": math.log(ln["rate"] / fair[ln["material_id"]]),
                          "q": ln["quantity"], "f": fair[ln["material_id"]]}
                         for ln in w["cost_form"]["sites"][0]["lines"]
                         if ln.get("material_id") in fair]
                for x in lines:
                    sig[x["m"]].append(x["r"])
                self.forms.append(lines)
        self.sigma = {m: max(SIGMA_FLOOR, _robust(v)[1]) for m, v in sig.items() if len(v) >= 5}
        self.stats = {nm: [rate_stat(nm, ls, self.sigma) for ls in self.forms]
                      for nm in ("rate_share", "ivw")}
        self.ok = len(per) >= PEERS_MIN_AGENCIES and len(self.forms) >= PEERS_MIN_FORMS
        self.null = {nm: _robust(v) for nm, v in self.stats.items()} if self.ok else {}

    def z(self, nm: str, value: float) -> float:
        c, s = self.null[nm]
        return (value - c) / max(s, SCALE_FLOOR if nm == "rate_share" else 0.25)


def rate_stat(nm: str, lines: list[dict], sigma: dict[str, float]) -> float:
    """A form's rates against the fair rates: the money share ("rate_share") or the precision-
    weighted mean log excess ("ivw")."""
    if not lines:
        return 0.0
    if nm == "rate_share":
        base = sum(x["q"] * x["f"] for x in lines)
        return sum(x["q"] * x["f"] * (math.exp(x["r"]) - 1) for x in lines) / base
    w = [1 / sigma.get(x["m"], SIGMA_DEFAULT) ** 2 for x in lines]
    return sum(wi * x["r"] for wi, x in zip(w, lines, strict=True)) / sum(w)


def features(form: dict, sor, index, peers: Peers | None) -> dict | None:
    """What every candidate reads: the judged whole estimate (as production judges it) and its
    priced lines against their fair rates."""
    w = whole.judge(form, cwt.computed(form), "ROAD_CC", sor, index, "TRIAL", "this-agency",
                    "W", cwt.TODAY)
    if w.verdict == "CANT_CHECK":
        return None
    sig = peers.sigma if peers and peers.ok else {}
    lines = [{"m": x.material, "r": math.log(x.rate / x.fair_rate), "q": x.fair_quantity,
              "f": x.fair_rate, "s": sig.get(x.material, SIGMA_DEFAULT), "a": x.fair_amount}
             for x in w.lines if x.fair_rate and x.fair_rate > 0 and x.rate > 0]
    return {"gap": w.gap, "share": w.gap_share, "lines": lines, "sig": sig}


def material(f: dict) -> bool:
    """Every candidate asks only about money that matters (the current rule's own floor)."""
    return f["gap"] >= whole.GAP_MIN_RS and f["share"] >= MIN_SHARE


def score(nm: str, f: dict, peers: Peers | None) -> float:
    """Each candidate's statistic (bigger = more like padding)."""
    ls = f["lines"]
    if not ls:
        return -math.inf
    if nm in ("gap", "gap_cal"):
        return f["share"]
    if nm == "z_ivw":                      # assumes every line's deviation is independent
        w = [1 / x["s"] ** 2 for x in ls]
        return sum(wi * x["r"] for wi, x in zip(w, ls, strict=True)) / math.sqrt(sum(w))
    if nm in ("peer_gap", "peer_ivw"):
        if not peers or not peers.ok:
            # too few peers to know their scatter: the current rule, unchanged
            return math.inf if f["share"] >= whole.GAP_SHARE else -math.inf
        key = "rate_share" if nm == "peer_gap" else "ivw"
        return peers.z(key, rate_stat(key, ls, f["sig"]))
    raise ValueError(nm)


def adaptive_line(peers: Peers | None, k: float, lo: float, hi: float) -> float:
    """A money line set from the district's honest scatter (median + k x scale of the peers'
    money share), held between lo and hi; the current 15% where the peers are too few."""
    if not peers or not peers.ok:
        return whole.GAP_SHARE
    c, sc = peers.null["rate_share"]
    return min(hi, max(lo, c + k * max(sc, SCALE_FLOOR)))


class Forest:
    """An isolation forest on the six core materials' log excess, trained on the district's other
    forms (machine learning; nothing to train on without peers)."""
    MATS = tuple(cwt.BASE)

    def __init__(self, peers: Peers | None):
        self.model = None
        if peers and peers.ok:
            from sklearn.ensemble import IsolationForest
            self.model = IsolationForest(n_estimators=200, random_state=0).fit(
                [self.vec(ls) for ls in peers.forms])

    def vec(self, lines: list[dict]) -> list[float]:
        got = {x["m"]: x["r"] for x in lines}
        return [got.get(m, 0.0) for m in self.MATS]

    def score(self, f: dict) -> float:
        if self.model is None or sum(max(0.0, x["r"]) for x in f["lines"]) <= 0:
            return -math.inf      # only excess counts as padding; a cheap form is not asked
        return -float(self.model.score_samples([self.vec(f["lines"])])[0])


def cost_world(scn, seed: str):
    label, source, sigma, tau, n_forms, n_agencies, noisy = scn
    rng = random.Random(f"{label}-{seed}")
    index = peers = None
    if source == "district":
        others = []
        for k in range(n_forms):
            agency = k % n_agencies
            # a noisy agency files scattered rates to loosen any line set from the peers' scatter
            f = honest(rng, 0.40 if agency < noisy else sigma, tau)
            others.append({"work_id": f"O{k}", "district_lgd": "TRIAL", "cost_form": f,
                           "cost_form_meta": {"saved_by": f"agency-{agency}"}})
        index = rates.RateIndex.build(others)
        peers = Peers(others)
    return rng, index, (cwt.SOR if source == "sor" else None), peers


STATS = ["gap", "gap_cal", "z_ivw", "peer_gap", "peer_ivw", "iforest"]
# adaptive money lines held in a band: (lo, hi). "stricter only" never asks less than today;
# "band" may ask less in a scattered district and more in a tight one
BANDS = {"line_stricter_only": (0.08, whole.GAP_SHARE), "line_band_12_20": (0.12, 0.20)}
COMBOS = {
    # the current rule, OR the peer-adaptive money line: never more lenient than today
    "cur_or_peer_gap": ("gap", "peer_gap"),
    "cur_or_peer_ivw": ("gap", "peer_ivw"),
}


def cost(n_test: int = 600, n_cal: int = 400) -> dict:
    # 1. calibration: honest forms from every scenario, pooled
    cal: dict[str, list[float]] = defaultdict(list)
    worlds = {}
    for scn in SCENARIOS:
        rng, index, sor, peers = cost_world(scn, "cal")
        forest = Forest(peers)
        worlds[scn[0]] = (forest,)
        for _ in range(n_cal):
            f = features(honest(rng, scn[2], scn[3]), sor, index, peers)
            for nm in STATS:
                v = (forest.score(f) if nm == "iforest" else score(nm, f, peers)) \
                    if f and material(f) else -math.inf
                cal[nm].append(v)
            # what the current rule leaves for the peer part of a combination
            cal["_cur"].append(bool(f and material(f) and f["share"] >= whole.GAP_SHARE))
            cal["_pairs"].append((f, peers))

    def line_at(xs: list[float], fpr: float) -> float:
        s = sorted(xs, reverse=True)
        k = max(0, int(round(fpr * len(s))) - 1)
        return s[k] + 1e-12 if s and s[k] > -math.inf else math.inf

    lines = {nm: line_at(cal[nm], TARGET_FPR) for nm in STATS}
    for band, (lo, hi) in BANDS.items():
        best = None
        for k in [x / 4 for x in range(4, 33)]:            # 1.0 .. 8.0
            fpr = statistics.fmean(
                bool(f and material(f) and f["share"] >= adaptive_line(pe, k, lo, hi))
                for f, pe in cal["_pairs"])
            if fpr <= TARGET_FPR:
                best = k
                break
        lines[band] = best if best is not None else 8.0
    lines["gap"] = whole.GAP_SHARE                       # the current rule, as deployed
    # each combination's peer part: the budget the current rule leaves, up to TARGET_FPR overall
    cur_rate = statistics.fmean(cal["_cur"])
    for combo, (_a, b) in COMBOS.items():
        left = [v for v, c in zip(cal[b], cal["_cur"], strict=True) if not c]
        budget = max(0.0, TARGET_FPR - cur_rate) * len(cal[b]) / max(1, len(left))
        lines[combo] = line_at(left, budget) if budget > 0 else math.inf

    def asks(nm: str, f: dict | None, peers: Peers | None, forest: Forest) -> bool:
        if not f or not material(f):
            return False
        if nm in COMBOS:
            a, b = COMBOS[nm]
            return f["share"] >= whole.GAP_SHARE or score(b, f, peers) >= lines[nm]
        if nm == "iforest":
            return forest.score(f) >= lines["iforest"]
        if nm in BANDS:
            lo, hi = BANDS[nm]
            return f["share"] >= adaptive_line(peers, lines[nm], lo, hi)
        return score(nm, f, peers) >= lines[nm]

    every = STATS + list(COMBOS) + list(BANDS)
    rows, t_spent = [], defaultdict(float)
    for scn in SCENARIOS:
        label = scn[0]
        rng, index, sor, peers = cost_world(scn, "test")
        forest = Forest(peers)
        forms = [honest(rng, scn[2], scn[3]) for _ in range(n_test)]
        base = [features(f, sor, index, peers) for f in forms]
        row = {"scenario": label, "honest_asked": {}, "caught": defaultdict(dict)}
        for nm in every:
            t0 = time.perf_counter()
            row["honest_asked"][nm] = sum(asks(nm, f, peers, forest) for f in base) / n_test
            t_spent[nm] += time.perf_counter() - t0
        for pname, kw in PADDINGS:
            padded = [features(cwt.variant(f, **kw), sor, index, peers) for f in forms]
            for nm in every:
                row["caught"][pname][nm] = sum(asks(nm, f, peers, forest)
                                               for f in padded) / n_test
        rows.append(row)
        print(f"{label}: honest asked " + ", ".join(f"{nm} {row['honest_asked'][nm]:.1%}"
                                                    for nm in every), flush=True)
    summary = {}
    for nm in every:
        p20 = [r["caught"]["every line +20%"][nm] for r in rows]
        summary[nm] = {
            "worst_honest_asked": max(r["honest_asked"][nm] for r in rows),
            "mean_honest_asked": statistics.fmean(r["honest_asked"][nm] for r in rows),
            "min_caught_+20%": min(p20), "mean_caught_+20%": statistics.fmean(p20),
            "mean_caught_+15%": statistics.fmean(r["caught"]["every line +15%"][nm]
                                                 for r in rows),
            "mean_caught_one_line": statistics.fmean(
                r["caught"][k][nm] for r in rows
                for k in ("cement rate x2", "cement and aggregate +40%", "sand rate x2")),
            "mean_caught_all": statistics.fmean(v[nm] for r in rows for v in r["caught"].values()),
            "cells_meeting_target": sum(r["honest_asked"][nm] <= 0.02
                                        and r["caught"]["every line +20%"][nm] >= 0.90
                                        for r in rows),
            "decide_ms": round(1000 * t_spent[nm] / (n_test * len(rows)), 4)}
    return {"target_fpr": TARGET_FPR, "lines": lines, "current_rule_pooled_fpr": cur_rate,
            "forms_per_cell": n_test, "rows": [{**r, "caught": dict(r["caught"])} for r in rows],
            "summary": summary}


# ==================================================================================================
# Site Progress
# ==================================================================================================
#
# A work filmed for 12 months (a first visit, then monthly), by a person and a reader that err as real
# ones do (rates are ASSUMPTIONS until the field trial, T126):
HONEST_ERR = {"miss": 0.08, "dark": 0.08, "partial": 0.08, "gps_weak": 0.10, "gps_jitter": 0.03,
              "views_lost": 0.02, "unsealed": 0.02, "pause": 0.15}
JUDGE_HONEST = {"shown": 0.80, "cant_tell": 0.15, "not_shown": 0.05}   # a real claim, a good video
JUDGE_GHOST = {"not_shown": 0.70, "cant_tell": 0.20, "shown": 0.10}    # a claim not built
FRAUDS = ("ghost claims", "ghost claims, reader fooled 1 in 3", "reused footage",
          "filmed elsewhere", "filmed 200 m away", "GPS faked inside, filmed elsewhere",
          "bad videos on purpose", "never filmed")
MONTHS = 12


def _pick(rng: random.Random, dist: dict) -> str:
    x, acc = rng.random(), 0.0
    for k, p in dist.items():
        acc += p
        if x < acc:
            return k
    return k


def simulate(rng: random.Random, kind: str, start) -> dict:
    """One work's site visits as the video job would read them."""
    from datetime import timedelta
    visits = []
    fraud_from = 3
    for m in range(MONTHS):
        if m and rng.random() < HONEST_ERR["miss"]:
            continue
        if kind == "never filmed":
            continue
        when = start + timedelta(days=30 * m)
        r = {"sealed": rng.random() >= HONEST_ERR["unsealed"], "in_app": True,
             "mock_location": False, "gps_inside": True, "quality_ok": True,
             "viewpoints_expected": 5, "viewpoints_matched": 5, "views_match_site": True,
             "change": "changed", "claim_verdict": None, "reused_from": [], "same_place_as": []}
        if m == 0:
            r.update(views_match_site=None, change=None)
        else:
            ghost = kind.startswith("ghost") and m >= 2
            judge = (JUDGE_GHOST if kind == "ghost claims" else
                     {"not_shown": 0.50, "cant_tell": 0.17, "shown": 0.33} if ghost
                     else JUDGE_HONEST)
            if not ghost:
                judge = JUDGE_HONEST
            r["change"] = ("no_change" if ghost and rng.random() < 0.85 else
                           "no_change" if rng.random() < HONEST_ERR["pause"] else "changed")
            r["claim_verdict"] = _pick(rng, judge)
        dodge = kind == "bad videos on purpose" and m >= 2 and rng.random() < 0.8
        x = rng.random()
        if dodge or x < HONEST_ERR["dark"]:
            r.update(quality_ok=False, views_match_site=None, viewpoints_matched=0,
                     change="cant_tell" if m else None, claim_verdict="cant_tell" if m else None)
        elif x < HONEST_ERR["dark"] + HONEST_ERR["partial"] and m:
            r.update(views_match_site=None, viewpoints_matched=1, change="cant_tell")
        elif x < HONEST_ERR["dark"] + HONEST_ERR["partial"] + HONEST_ERR["views_lost"] and m:
            r.update(views_match_site=False, viewpoints_matched=0, change="cant_tell",
                     claim_verdict="cant_tell")
        y = rng.random()
        if y < HONEST_ERR["gps_weak"]:
            r.update(gps_weak=True, gps_inside=None)
        elif y < HONEST_ERR["gps_weak"] + HONEST_ERR["gps_jitter"]:
            r.update(gps_inside=False, gps_distance_m=rng.uniform(60, 300))
        if m >= fraud_from:
            if kind == "reused footage" and rng.random() < 0.9:
                r["reused_from"] = [{"work_id": "W", "visit_id": "V1", "frames": 40}]
            if kind == "filmed elsewhere" and rng.random() < 0.85:
                r.update(gps_inside=False, gps_distance_m=rng.uniform(1000, 5000),
                         views_match_site=False, viewpoints_matched=0, change="cant_tell")
            if kind == "filmed 200 m away":
                r.update(gps_inside=False, gps_distance_m=rng.uniform(150, 250),
                         views_match_site=False, viewpoints_matched=0, change="cant_tell")
            if kind == "GPS faked inside, filmed elsewhere":
                r.update(gps_inside=True, views_match_site=False, viewpoints_matched=0,
                         change="cant_tell", claim_verdict="cant_tell")
        visits.append({"visit_id": f"V{m + 1}", "kind": "baseline" if m == 0 else "monthly",
                       "captured_at": when.isoformat(), "claim": "stage done" if m else None,
                       "readings": r})
    return {"work_id": "W", "status": "SANCTIONED", "sanction_date": start.isoformat(),
            "cost_form": {"work": {"nature": "new"}, "timing": {"start_month": start.isoformat()[:7]}},
            "site_visits": visits}


CLAIM_CODES = {"CLAIM_NOT_SHOWN", "SITE_VIDEOS_UNUSABLE", "NOT_FILMED_AT_THIS_SITE"}
FAR_M = 300.0            # a GPS point this far out is past phone multipath in a village or town


def _unusable(v, visits_mod, far_rule: bool, old: bool = False) -> str | None:
    why = visits_mod.unusable(v)
    if old and why == "views do not match the site" and v.get("gps_inside") is False:
        return None                       # T136: any GPS out with other views was "elsewhere"
    if why or not far_rule:
        return why
    # with the distance rule, a video near (not far) from the site whose views do not match is
    # unusable, never "filmed elsewhere": filming 200 m away is still caught, twice in a row
    if v.get("views_match_site") is False and v.get("quality_ok") is not False \
            and v.get("mock_location") is not True \
            and (v.get("gps_distance_m") or 0) < FAR_M:
        return "views do not match the site"
    return None


def _elsewhere(vs, far_rule: bool) -> bool:
    for v in vs:
        views_out = v.get("views_match_site") is False and v.get("quality_ok") is not False
        gps_out = v.get("mock_location") is True or (
            v.get("gps_inside") is False
            and (not far_rule or (v.get("gps_distance_m") or 0) >= FAR_M))
        if views_out and gps_out:
            return True
    return False


def site_candidates(work: dict, as_of, sp, visits_mod) -> dict[str, set]:
    """What each design asks. All share the yes/no checks (footage seen before, never filmed...);
    they differ in how they read claims, unusable videos and "filmed elsewhere":
      current      the T136 design: a claim not shown twice in a row ("can't tell" between does
                   not reset); the last two videos unusable; filmed elsewhere = GPS out and views out
      engine       the agent as it is now (after T137: tuned, every video so far unusable from the
                   third, and a completion with no final video)
      far300       the current claims and unusable rules; filmed elsewhere needs the GPS 300 m+ out
                   (or a mock location); a near video with other views is unusable instead
      window       far300, but 2+ "not shown" among the last 4 readable visits, and 3 of the last 4
                   unusable
      cusum        far300, with claims and unusable videos in one running score: "not shown" +2.6,
                   "can't tell" +0.3, "shown" -2.1, an unusable video +0.7, a usable one -0.3,
                   floored at 0, asking at CUSUM_LINE (set to the current design's false alarms)"""
    r = sp.assess(work, as_of)
    engine = {f.code for f in r.findings if f.risk > 0}
    shared = engine - CLAIM_CODES - {"COMPLETE_NOT_FILMED"}
    vs = [v for v in visits_mod.of(work) if visits_mod.accepted(v) and v.captured <= as_of]
    monthly = [v for v in vs if v.kind != "baseline"]
    # the T136 design (before this bake-off): two unusable in a row; elsewhere at any distance
    old = set(shared)
    if _elsewhere(vs, False):
        old.add("NOT_FILMED_AT_THIS_SITE")
    if "CLAIM_NOT_SHOWN" in engine:
        old.add("CLAIM_NOT_SHOWN")
    if len(vs) >= 2 and all(_unusable(v, visits_mod, False, old=True) for v in vs[-2:]) \
            and "NOT_FILMED_AT_THIS_SITE" not in old:
        old.add("SITE_VIDEOS_UNUSABLE")
    out = {"current": old, "engine": engine}
    far = set(shared)
    if _elsewhere(vs, True):
        far.add("NOT_FILMED_AT_THIS_SITE")
    if "CLAIM_NOT_SHOWN" in engine:
        far.add("CLAIM_NOT_SHOWN")
    last = vs[-2:]
    if len(last) == 2 and all(_unusable(v, visits_mod, True) for v in last) \
            and "NOT_FILMED_AT_THIS_SITE" not in far:
        far.add("SITE_VIDEOS_UNUSABLE")
    out["far300"] = far
    w = {c for c in far if c not in ("CLAIM_NOT_SHOWN", "SITE_VIDEOS_UNUSABLE")}
    readable = [v for v in monthly if v.get("quality_ok") is not False]
    if sum(v.claim_verdict == "not_shown" for v in readable[-4:]) >= 2:
        w.add("CLAIM_NOT_SHOWN")
    if sum(bool(_unusable(v, visits_mod, True)) for v in vs[-4:]) >= 3:
        w.add("SITE_VIDEOS_UNUSABLE")
    out["window"] = w
    # tuned: far300, unusable when 4 of the last 5 videos are; claims as the current design
    t = {x for x in far if x != "SITE_VIDEOS_UNUSABLE"}
    if sum(bool(_unusable(v, visits_mod, True)) for v in vs[-5:]) >= 4 \
            and "NOT_FILMED_AT_THIS_SITE" not in t:
        t.add("SITE_VIDEOS_UNUSABLE")
    out["tuned"] = t
    # tuned_claims: tuned, and a claim asked when 3 of the last 5 readable visits do not show it
    tc = {x for x in t if x != "CLAIM_NOT_SHOWN"}
    if sum(v.claim_verdict == "not_shown" for v in readable[-5:]) >= 3:
        tc.add("CLAIM_NOT_SHOWN")
    out["tuned_claims"] = tc
    c = {x for x in far if x not in ("CLAIM_NOT_SHOWN", "SITE_VIDEOS_UNUSABLE")}
    score = 0.0
    for v in monthly:
        if _unusable(v, visits_mod, True):
            score += 0.7
        else:
            score += {"not_shown": 2.64, "cant_tell": 0.29, "shown": -2.08}.get(
                v.claim_verdict or "", 0.0) - 0.3
        score = max(0.0, score)
    if score >= CUSUM_LINE[0]:
        c.add("PROGRESS_NOT_AS_CLAIMED")
    out["cusum"] = c
    return out


CUSUM_LINE = [5.0]
DESIGNS = ("current", "engine", "far300", "window", "tuned", "tuned_claims", "cusum")


def site(n_honest: int = 2000, n_fraud: int = 500) -> dict:
    from datetime import date, timedelta
    from drishti.agents.site_progress import agent as sp
    from drishti.agents.site_progress import visits as visits_mod
    start = date(2025, 9, 1)
    checks = [start + timedelta(days=30 * m + 5) for m in range(2, MONTHS + 1)]

    def ever(work: dict) -> dict[str, set]:
        """Every design checked at each month's end, as the daily batch would: asked if ever."""
        got = {d: set() for d in DESIGNS}
        for day in checks:
            for d, codes in site_candidates(work, day, sp, visits_mod).items():
                got[d] |= codes
        return got

    def run(kind: str, n: int, seed: str, scale: float) -> list[dict]:
        rng = random.Random(f"site-{kind}-{seed}-{scale}")
        saved = dict(HONEST_ERR)
        for k in HONEST_ERR:
            HONEST_ERR[k] = saved[k] * scale
        try:
            return [ever(simulate(rng, kind, start)) for _ in range(n)]
        finally:
            HONEST_ERR.update(saved)

    res = {"scales": {}, "assumed_errors": dict(HONEST_ERR), "judge_honest": JUDGE_HONEST,
           "judge_ghost": JUDGE_GHOST, "far_m": FAR_M}
    t0 = time.perf_counter()
    for scale in (0.5, 1.0, 1.5):
        target = 0.02            # the cusum line: the lowest at which 2 in 100 honest works a year
        line = None
        for cand in [x / 2 for x in range(4, 41)]:
            CUSUM_LINE[0] = cand
            again = run("honest", n_honest // 2, "cal", scale)
            if statistics.fmean(bool(x["cusum"]) for x in again) <= target:
                line = cand
                break
        CUSUM_LINE[0] = line or 12.0
        hon = run("honest", n_honest, "test", scale)
        row = {"cusum_line": CUSUM_LINE[0],
               "honest_asked": {d: statistics.fmean(bool(x[d]) for x in hon) for d in DESIGNS},
               "honest_codes": {d: dict(sorted(Counter_(c for x in hon for c in x[d]).items()))
                                for d in DESIGNS},
               "caught": {}}
        for kind in FRAUDS:
            got = run(kind, n_fraud, "test", scale)
            row["caught"][kind] = {d: statistics.fmean(bool(x[d]) for x in got)
                                   for d in DESIGNS}
        res["scales"][str(scale)] = row
        print(f"errors x{scale}: honest " + ", ".join(
            f"{d} {row['honest_asked'][d]:.1%}" for d in DESIGNS), flush=True)
    res["seconds"] = round(time.perf_counter() - t0, 1)
    return res


def Counter_(xs):
    from collections import Counter
    return Counter(xs)


def site_text(res: dict) -> list[str]:
    out = ["Site Progress decision bake-off: simulated works filmed for 12 months, every design "
           "checked at each month's end (asked = asked at any check). The person and the reader err "
           "at assumed rates (x1: " + ", ".join(f"{k} {v:.0%}" for k, v in
                                                res["assumed_errors"].items())
           + f"; an honest claim judged not shown {res['judge_honest']['not_shown']:.0%}), "
           "tried at half, as assumed and 1.5 times.", ""]
    for scale, row in res["scales"].items():
        out.append(f"errors x{scale} (cusum line {row['cusum_line']})")
        out.append(f"  {'':40} " + "".join(f"{d:>9}" for d in DESIGNS))
        out.append("  honest works asked anything".ljust(43) + "".join(
            f"{row['honest_asked'][d]:>9.1%}" for d in DESIGNS))
        for kind, v in row["caught"].items():
            out.append(f"  caught: {kind}".ljust(43) + "".join(f"{v[d]:>9.1%}" for d in DESIGNS))
        out.append("  honest works' questions: " + json.dumps(row["honest_codes"]))
        out.append("")
    return out


# ==================================================================================================
# Duplicate Work: the map grid
# ==================================================================================================

def dup(sizes=(1000, 3000, 10000)) -> dict:
    """One district with n filed roads scattered over 60 km: the time to build the index and to
    check one work, with the map grid (T137) and without (every earlier work looked at), and
    whether both give the same answers."""
    import copy

    import agent_robustness_loop as rl

    from drishti.agents.dup_split import agent as dup_agent
    from drishti.agents.dup_split.repeat import RepeatIndex
    world = rl.build_world()
    seed_road = world.background[0]
    rows = []
    for n in sizes:
        rng = random.Random(3)
        many = []
        for i in range(n):
            w = copy.deepcopy(seed_road)
            w["work_id"] = f"WF-MANY-{i}"
            loc = w["cost_form"]["sites"][0]["location"]
            dlat, dlon = rng.uniform(-0.3, 0.3), rng.uniform(-0.3, 0.3)
            for k in ("lat", "end_lat"):
                loc[k] += dlat
            for k in ("lon", "end_lon"):
                loc[k] += dlon
            many.append(w)
        t0 = time.perf_counter()
        grid = RepeatIndex.build(world.district + many)
        built = time.perf_counter() - t0
        scan = copy.copy(grid)
        scan._grid, scan._wide = {}, {}
        sample = many[:: max(1, n // 40)][:40]
        timing = {}
        for name, idx in (("grid", grid), ("scan", scan)):
            t0 = time.perf_counter()
            answers = [sorted(f.code for f in dup_agent.assess(w, idx).findings) for w in sample]
            timing[name] = ((time.perf_counter() - t0) / len(sample), answers)
        rows.append({"forms": n, "index_s": round(built, 2),
                     "check_ms_grid": round(1000 * timing["grid"][0], 1),
                     "check_ms_scan": round(1000 * timing["scan"][0], 1),
                     "district_s_grid": round(timing["grid"][0] * n),
                     "district_s_scan": round(timing["scan"][0] * n),
                     "same_answers": timing["grid"][1] == timing["scan"][1]})
        print(rows[-1], flush=True)
    return {"rows": rows}


def dup_text(res: dict) -> list[str]:
    out = ["Duplicate Work, the map grid (T137): one district of n filed roads; one work's check, "
           "and the whole district's batch (n checks)", "",
           f"{'forms':>7} {'check, grid':>12} {'check, scan':>12} {'district, grid':>15} "
           f"{'district, scan':>15} {'same answers':>13}"]
    for r in res["rows"]:
        out.append(f"{r['forms']:>7,} {r['check_ms_grid']:>9} ms {r['check_ms_scan']:>9} ms "
                   f"{r['district_s_grid']:>13} s {r['district_s_scan']:>13} s "
                   f"{str(r['same_answers']):>13}")
    out += ["", "Equivalence on random dense districts: tests/agents/dup_split/test_dup_grid.py "
            "(700 works, every at-site work, distance, overlap and nearby note the same)."]
    return out


def write(part: str, res: dict, text: list[str]) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    p = OUT / f"architecture_bakeoff_{part}"
    p.with_suffix(".json").write_text(json.dumps(res, indent=1, default=str) + "\n",
                                      encoding="utf-8")
    p.with_suffix(".txt").write_text("\n".join(text) + "\n", encoding="utf-8")
    print("\n".join(text))


def cost_text(res: dict) -> list[str]:
    s = res["summary"]
    out = [f"Cost decision bake-off: {res['forms_per_cell']} planted CC-road forms per cell; every "
           f"candidate's line set so {res['target_fpr']:.0%} of honest forms (pooled) are asked, "
           f"except 'gap' (the current rule, as deployed: 15% and Rs 50,000). All ask only about "
           f"Rs 50,000+ and {MIN_SHARE:.0%}+.", "",
           f"{'candidate':16} {'worst honest':>12} {'mean honest':>11} {'+20% min':>9} "
           f"{'+20% mean':>9} {'+15% mean':>9} {'one line':>8} {'all mean':>8} {'cells ok':>8} "
           f"{'ms':>7}"]
    for nm, v in s.items():
        out.append(f"{nm:16} {v['worst_honest_asked']:>12.1%} {v['mean_honest_asked']:>11.1%} "
                   f"{v['min_caught_+20%']:>9.1%} {v['mean_caught_+20%']:>9.1%} "
                   f"{v['mean_caught_+15%']:>9.1%} {v['mean_caught_one_line']:>8.1%} "
                   f"{v['mean_caught_all']:>8.1%} "
                   f"{v['cells_meeting_target']:>5}/{len(res['rows'])} {v['decide_ms']:>7}")
    out += ["", "By scenario (honest asked | caught at every line +20% | cement x2 | sand x2):"]
    for r in res["rows"]:
        out.append(f"  {r['scenario']}")
        for nm in s:
            c = r["caught"]
            out.append(f"    {nm:16} {r['honest_asked'][nm]:6.1%} | {c['every line +20%'][nm]:6.1%}"
                       f" | {c['cement rate x2'][nm]:6.1%} | {c['sand rate x2'][nm]:6.1%}")
    out += ["", "Target (plan T120 §14): honest asked <= 2% and every line +20% asked >= 90%, in "
            "every cell. Synthetic forms: the honest spreads are assumptions until real forms "
            "(T098)."]
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("part", choices=["cost", "site", "dup"])
    ap.add_argument("--n", type=int, default=600)
    args = ap.parse_args()
    if args.part == "cost":
        res = cost(args.n)
        write("cost", res, cost_text(res))
    if args.part == "site":
        res = site()
        write("site", res, site_text(res))
    if args.part == "dup":
        res = dup()
        write("dup", res, dup_text(res))


if __name__ == "__main__":
    main()
