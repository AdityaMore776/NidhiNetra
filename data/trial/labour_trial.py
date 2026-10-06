r"""Labour, trade by trade (T141): planted filings, honest and padded, through the real path.

The owner (6 Oct 2026): "we just need to detect blatant irregularities, none of the 'can still be
made with lower amount of workers' or 'doesn't need this many', some projects might need that
amount of workers". So the Cost agent asks only when a trade's day rate is at least twice what
other agencies in the district pay that trade (labour.py), or workers stay on site longer than the
work lasts. This trial measures both on planted filings of the website form (PSWIF v1.1: its
labour schedule), each run through pswif.py, validate.py and the Cost agent exactly as the live
check does.

  districts   three wage levels (a low one, 15% above it, 60% above it); every trade has a market
              wage there. Eight agencies file six CC roads each (the district's rates); each
              agency pays the market times its own factor (lognormal, sd 10%), each row +-4%
  honest      filings by agencies not in the district's index: the same honest spread, 1 in 20
              from an agency 30% above the market (a remote site), crews of any size, sometimes
              rare trades (a welder, an electrician) or a trade not on the list with its grade
  padded      the honest filings changed one way each: one trade's rate x1.5 / x2 / x2.5 / x3,
              every rate x1.5, a helper declared "highly skilled" at an operator's rate (and 25%
              above it), a trade not on the list declared highly skilled at 2.2x / 3x an
              operator's rate, a watchman on site 1.6x the work's time, ten times the workers

--wages-in-whole measures the rule before T141's last change: the whole estimate judging every
wage like any line (whole.SETTLE_LABOUR off), written to results/labour_trial_wages_in_whole.*.

Nothing here is a real agency or work. Writes results/labour_trial.txt and .json.

Run:  apps\engine\.venv\Scripts\python.exe data\trial\labour_trial.py [--n 150] [--wages-in-whole]
"""

from __future__ import annotations

import argparse
import copy
import json
import math
import random
import sys
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(ROOT / "data" / "trial"))
sys.path.insert(0, str(ROOT / "apps" / "engine"))
import work_form_examples as wf  # noqa: E402

from drishti.agents.cost_estimate import agent, labour, rates, whole  # noqa: E402
from drishti.cost_form import catalog, pswif  # noqa: E402

OUT = ROOT / "data" / "trial" / "results" / "labour_trial"
AS_OF = date(2026, 10, 2)
# a district's market day wage for each trade (Rs), before its wage level
WAGE = {"beldar": 400, "helper": 410, "chowkidar": 390, "mate": 460, "mason": 700,
        "carpenter": 720, "bar_bender": 680, "painter": 660, "plumber": 720, "electrician": 760,
        "welder": 800, "driver": 700, "operator": 900, "supervisor": 950}
LEVELS = {"low": 1.0, "mid": 1.15, "high": 1.6}
# how often a filing has each trade beyond its masons and beldars
OPTIONAL = {"helper": 0.5, "carpenter": 0.4, "bar_bender": 0.3, "operator": 0.5, "mate": 0.4,
            "chowkidar": 0.3, "welder": 0.12, "electrician": 0.12, "plumber": 0.1,
            "painter": 0.1, "driver": 0.15, "supervisor": 0.15}
FEW = {"operator": (1, 4), "supervisor": (1, 2), "mate": (1, 3), "chowkidar": (1, 2),
       "driver": (1, 3)}
OTHER = (("Tile cutter", "skilled"), ("Stone carver", "skilled"),
         ("Pump fitter", "semi_skilled"), ("Survey chainman", "unskilled"))
AGENCY_SD = 0.10
ROW_SD = 0.04
PREMIUM, PREMIUM_SHARE = 1.30, 0.05
DAYS = 120                       # the filings' time to completion


def tag(i: int) -> str:
    """A made-up agency's name word: numbers and branch words are set aside when agencies are told
    apart (rates.agency_key: "Division 1" and "Division 2" are one agency), so names differ in
    words."""
    out = ""
    while True:
        out = "abcdefghjkmnpqrstuwyz"[i % 21] + out
        i //= 21
        if not i:
            return "k" + out


def grade_wage(grade: str, wages: dict) -> float:
    xs = [w for t, w in wages.items() if catalog.grade_of(f"labour_{t}") == grade]
    return sum(xs) / len(xs)


def crew(rng: random.Random, wages: dict, factor: float, days: int,
         other: bool = True) -> list[tuple]:
    """An honest labour schedule: (trade, workers, days each, rate, source, task, lines)."""
    trades = ["mason", "beldar"] + [t for t, p in OPTIONAL.items() if rng.random() < p]
    rows = []
    for t in trades:
        lo, hi = FEW.get(t, (1, 40))
        workers = rng.randint(lo, hi)
        on_site = max(1.0, round(rng.uniform(0.1, 1.0) * days * 2) / 2)
        rate = round(wages[t] * factor * rng.gauss(1, ROW_SD))
        rows.append((t, workers, on_site, rate, "District recent rates",
                     f"{catalog.material(f'labour_{t}')['label']} work on the road", "1-4"))
    if other and rng.random() < 0.1:
        name, grade = rng.choice(OTHER)
        rows.append(("other", rng.randint(1, 4), round(rng.uniform(5, days)),
                     round(grade_wage(grade, wages) * factor * rng.gauss(1, ROW_SD)),
                     "Approved quotation", f"{name} work on the road", "1-4", name, grade))
    return rows


def filing(rng: random.Random, ref: str, agency: str, k: int, rows: list[tuple]) -> dict:
    """A CC road filed on the website form, its labour schedule `rows`."""
    rec = AS_OF - timedelta(days=rng.randint(10, 150))
    p = wf.road(ref, agency, f"Gaon {k}", 30 + k % 200, rec, None, days=DAYS)
    for key in [x for x in p if x.startswith("lab_")]:
        del p[key]
    put(p, rows)
    return p


def put(p: dict, rows: list[tuple]) -> dict:
    for key in [x for x in p if x.startswith("lab_")]:
        del p[key]
    for n, r in enumerate(rows, start=1):
        trade, workers, days, rate, source, task, lines = r[:7]
        name, grade = (r[7], r[8]) if len(r) > 8 else ("", catalog.grade_of(f"labour_{trade}"))
        p.update({f"lab_trade_{n}": trade, f"lab_name_{n}": name, f"lab_grade_{n}": grade,
                  f"lab_workers_{n}": f"{workers:g}", f"lab_days_{n}": f"{days:g}",
                  f"lab_rate_{n}": f"{rate:g}", f"lab_task_{n}": task, f"lab_lines_{n}": lines,
                  f"lab_source_{n}": source})
    total = wf.estimate_total(p)
    p.update(technical_estimate=f"{total:.2f}", mplads_share=f"{total:.0f}",
             mp_recommended_amount=f"{round(total, -3):.0f}")
    return p


def to_work(p: dict, district: str) -> dict:
    w = pswif.to_work(p, today=AS_OF)
    w.update(district_lgd=district, district_name=district, state_name="Testland")
    return w


def lognormal(rng: random.Random, sd: float) -> float:
    return math.exp(rng.gauss(0, sd))


def district_index(rng: random.Random, name: str, wages: dict) -> rates.RateIndex:
    works = []
    for a in range(8):
        factor = lognormal(rng, AGENCY_SD)
        for f in range(6):
            p = filing(rng, f"BG-{name}-{a}-{f}", f"Background agency {name} {tag(a)}", a * 6 + f,
                       crew(rng, wages, factor, DAYS, other=False))
            works.append(to_work(p, f"T|{name}"))
    return rates.RateIndex.build(works)


def judge(p: dict, district: str, index: rates.RateIndex) -> tuple[set[str], str]:
    w = to_work(p, district)
    r = agent.assess(w, SimpleNamespace(as_of=AS_OF, data={"sor": None, "rates": index}))
    return {f.code for f in r.findings if f.risk > 0}, r.status.value


# ---- the padding, one way per filing --------------------------------------------------------

def _rows(p: dict) -> list[tuple]:
    rows, n = [], 1
    while f"lab_trade_{n}" in p:
        g = lambda k, n=n: p[f"lab_{k}_{n}"]  # noqa: E731
        rows.append((g("trade"), float(g("workers")), float(g("days")), float(g("rate")),
                     g("source"), g("task"), g("lines"), g("name"), g("grade")))
        n += 1
    return rows


def pad_one(by: float):
    def f(rng, p, wages):
        rows = _rows(p)
        listed = [i for i, r in enumerate(rows) if r[0] != "other"]
        i = rng.choice(listed)
        r = rows[i]
        rows[i] = (r[0], r[1], r[2], round(r[3] * by), *r[4:])
        return put(p, rows)
    return f


def pad_all(by: float):
    def f(rng, p, wages):
        return put(p, [(r[0], r[1], r[2], round(r[3] * by), *r[4:]) for r in _rows(p)])
    return f


def helper_inflated(over: float):
    def f(rng, p, wages):
        rows = [r for r in _rows(p) if r[0] != "helper"]
        rows.append(("helper", rng.randint(4, 20), round(rng.uniform(20, DAYS)),
                     round(wages["operator"] * over), "District recent rates",
                     "Carrying material to the masons", "1-4", "", "highly_skilled"))
        return put(p, rows)
    return f


def other_inflated(times_operator: float):
    def f(rng, p, wages):
        rows = _rows(p)
        rows.append(("other", rng.randint(1, 4), round(rng.uniform(20, DAYS)),
                     round(wages["operator"] * times_operator), "Approved quotation",
                     "Special finishing of the surface", "1-4", "Surface finisher",
                     "highly_skilled"))
        return put(p, rows)
    return f


def days_beyond(rng, p, wages):
    rows = [r for r in _rows(p) if r[0] != "chowkidar"]
    rows.append(("chowkidar", rng.randint(1, 3), round(DAYS * 1.6), round(wages["chowkidar"]),
                 "District recent rates", "Guarding the material and the site", "1-4", "",
                 "unskilled"))
    return put(p, rows)


def many_workers(rng, p, wages):
    return put(p, [(r[0], r[1] * 10, *r[2:]) for r in _rows(p)])


SCENARIOS = {
    "one trade x1.5": (pad_one(1.5), "LABOUR_RATE_FAR_ABOVE"),
    "one trade x2": (pad_one(2.0), "LABOUR_RATE_FAR_ABOVE"),
    "one trade x2.5": (pad_one(2.5), "LABOUR_RATE_FAR_ABOVE"),
    "one trade x3": (pad_one(3.0), "LABOUR_RATE_FAR_ABOVE"),
    "every rate x1.5": (pad_all(1.5), None),
    "helper as 'highly skilled' at an operator's rate": (helper_inflated(1.0),
                                                         "LABOUR_RATE_FAR_ABOVE"),
    "helper as 'highly skilled' at 1.25x an operator's rate": (helper_inflated(1.25),
                                                               "LABOUR_RATE_FAR_ABOVE"),
    "Other trade, 'highly skilled', at 2.2x an operator": (other_inflated(2.2),
                                                          "LABOUR_RATE_FAR_ABOVE"),
    "Other trade, 'highly skilled', at 3x an operator": (other_inflated(3.0),
                                                        "LABOUR_RATE_FAR_ABOVE"),
    "a watchman on site 1.6x the work's time": (days_beyond, "LABOUR_DAYS_BEYOND_WORK"),
    "ten times the workers, honest rates": (many_workers, None),
}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=150, help="honest filings per district")
    ap.add_argument("--seed", type=int, default=141)
    ap.add_argument("--wages-in-whole", action="store_true",
                    help="the whole estimate judges every wage like any line (before T141)")
    args = ap.parse_args()
    out_path = OUT
    if args.wages_in_whole:
        whole.SETTLE_LABOUR = False
        out_path = OUT.with_name(OUT.name + "_wages_in_whole")
    rng = random.Random(args.seed)
    out = {"n_per_district": args.n, "seed": args.seed, "rule": {
        "rate_margin": labour.RATE_MARGIN, "pool_margin": labour.POOL_MARGIN,
        "grade_step": labour.GRADE_STEP, "min_rs": labour.MIN_RS}, "districts": {}}
    lines = [("[wages judged in the whole estimate like any line: the rule before T141's last "
              "change]\n" if args.wages_in_whole else "")
             + f"Labour trial (T141): {args.n} honest filings a district, each padded one way at a "
             f"time; rule: a trade's rate at {labour.RATE_MARGIN:g}x what other agencies pay it "
             f"here ({labour.POOL_MARGIN:g}x its grade's pool), Rs {labour.MIN_RS:,}+ extra", ""]
    totals: dict[str, Counter] = {}
    for name, level in LEVELS.items():
        wages = {t: w * level for t, w in WAGE.items()}
        index = district_index(rng, name, wages)
        district = f"T|{name}"
        honest: list[tuple[dict, dict]] = []
        asked = Counter()
        status = Counter()
        for i in range(args.n):
            factor = lognormal(rng, AGENCY_SD) * (PREMIUM if rng.random() < PREMIUM_SHARE else 1)
            p = filing(rng, f"T-{name}-{i}", f"New agency {name} {tag(i)}", 1000 + i,
                       crew(rng, wages, factor, DAYS))
            got, st = judge(p, district, index)
            status[st] += 1
            for c in got:
                asked[c] += 1
            asked["any labour question"] += any(c.startswith("LABOUR") for c in got)
            asked["any question"] += bool(got)
            honest.append((p, {"factor": factor}))
        res = {"honest": {"n": args.n, "status": dict(status), "asked": dict(asked)},
               "padded": {}}
        lines.append(f"== {name} wages (x{level:g}): honest filings {args.n}, "
                     f"assessed {status.get('ASSESSED', 0)}")
        lines.append(f"  honest asked: labour {asked['any labour question']}/{args.n} "
                     f"({asked['any labour question'] / args.n:.1%}), any question "
                     f"{asked['any question']}/{args.n}"
                     + (f" {dict((k, v) for k, v in asked.items() if 'any' not in k)}"
                        if asked['any question'] else ""))
        for label, (fn, code) in SCENARIOS.items():
            hit, other_q, sts = 0, Counter(), Counter()
            for p, _meta in honest:
                q = fn(rng, copy.deepcopy(p), wages)
                got, st = judge(q, district, index)
                sts[st] += 1
                if code and code in got:
                    hit += 1
                for c in got:
                    if c != code:
                        other_q[c] += 1
            share = hit / len(honest)
            res["padded"][label] = {"caught": hit, "n": len(honest), "share": round(share, 4),
                                    "code": code, "other_questions": dict(other_q),
                                    "status": dict(sts)}
            totals.setdefault(label, Counter()).update({"hit": hit, "n": len(honest)})
            what = (f"{code} {hit}/{len(honest)} ({share:.0%})" if code else "meant to be quiet")
            lines.append(f"  {label:52} {what}; other questions {dict(other_q) or 'none'}")
        out["districts"][name] = res
        lines.append("")
        print("\n".join(lines[-len(SCENARIOS) - 4:]), flush=True)
    lines.append("== all districts")
    for label, c in totals.items():
        code = SCENARIOS[label][1]
        if code:
            lines.append(f"  {label:52} caught {c['hit']}/{c['n']} ({c['hit'] / c['n']:.0%})")
    text = "\n".join(lines) + "\n"
    print("\n" + text)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.with_suffix(".txt").write_text(text, encoding="utf-8")
    out_path.with_suffix(".json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
