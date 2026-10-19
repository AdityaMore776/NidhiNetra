r"""The Cost agent's boundaries, measured (T167): a large random honest population and a dose curve
for each fraud scheme, in both worlds. No case here is hand-labelled: the honest population says
how often an honest estimate is checked or asked; each dose curve says where a scheme turns from
fits / edge to check, then to ask.

  apps\engine\.venv\Scripts\python.exe data\eval\cost\sweep.py [--honest 200] [--seeds 10]

Writes data/trial/results/t167_cost_sweep.{txt,json}.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import cases as C  # noqa: E402
import levels as L  # noqa: E402

OUT = C.ROOT / "data" / "trial" / "results"
ORDER = ("na", "fits", "edge", "check", "ask")


def honest(w: C.World, rng: random.Random) -> tuple[dict, str]:
    """One random honest filing over the FULL honest spread of the world's agencies."""
    bias = rng.uniform(-w.spread, w.spread)
    if rng.random() < 0.7:
        length, width = rng.uniform(60, 800), rng.choice((3.0, 3.5, 3.75, 4.5, 5.5))
        # an honest agency plans a bigger road over more days (its crews stay inside them)
        p = C.road(w, length=length, width=width, jitter=bias,
                   days=round(120 * max(1.0, length * width / 1050)))
        kind = "road"
    else:
        p = C.scale(C.hall(w, area=rng.uniform(80, 320)), 1 + bias)
        kind = "hall"
    p = C._noisy(p, rng, 0.03)
    for trade in ("mason", "beldar"):
        C.lab(p, trade, rng.uniform(0.9, 1.15))
    if rng.random() < 0.3:
        p["tax_treatment"] = "Added separately"
        p["other_charges"] = f"{C.lines_total(p) * 0.18:.0f}"
    if rng.random() < 0.3:
        p["lumpsum_components"] = f"{C.lines_total(p) * rng.uniform(0, 0.02):.0f}"
    if rng.random() < 0.1:
        C.add_line(p, "Road signage boards, retro-reflective", "nos", rng.randint(2, 6), 3500,
                   "Approved quotation")
    mp_x = rng.uniform(0.7, 1.1)
    if mp_x < 0.92:                      # over 10% below: the form asks a reason
        p["rate_deviation_notes"] = "The MP's amount was an early figure, before the survey."
    return C.finish(p, mp_x=mp_x), kind


def base(w: C.World, rng: random.Random, **kw) -> dict:
    """An honest 300 m road with an honest agency's own noise, before the dose."""
    return C._noisy(C.road(w, jitter=rng.uniform(-w.spread / 2, w.spread / 2), **kw), rng, 0.03)


def _workers(p: dict, trade: str, f: float) -> dict:
    for k in [k for k in p if k.startswith("lab_trade_") and p[k] == trade]:
        n = k.removeprefix("lab_trade_")
        p[f"lab_workers_{n}"] = f"{float(p[f'lab_workers_{n}']) * f:g}"
    return p


def _qty(p: dict, start: str, f: float) -> dict:
    n = C.find(p, start)
    p[f"boq_qty_{n}"] = f"{float(p[f'boq_qty_{n}']) * f:.2f}"
    p[f"boq_just_{n}"] = "Extra for the approaches"
    return p


def _other(p: dict, share: float) -> dict:
    p["other_charges"] = f"{C.lines_total(p) * share:.0f}"
    return p


# scheme -> (doses, the filing at a dose, what the dose means)
SCHEMES = {
    "uniform padding": ([0, 4, 6, 8, 10, 11, 12, 14, 16, 18, 20, 25, 30],
                        lambda w, r, d: C.scale(base(w, r), 1 + d / 100),
                        "% on every material"),
    "one line (cement)": ([0, 10, 20, 30, 40, 60, 80, 100],
                          lambda w, r, d: C.scale(base(w, r), 1 + d / 100, only=("Cement",)),
                          "% on the cement line"),
    "cement quantity": ([0, 5, 10, 15, 20, 25, 30, 40, 60],
                        lambda w, r, d: _qty(base(w, r), "Cement", 1 + d / 100),
                        "% more cement, justified"),
    "sand + stone quantity": ([0, 10, 15, 20, 25, 30, 40],
                              lambda w, r, d: _qty(_qty(base(w, r), "Coarse sand", 1 + d / 100),
                                                   "Stone aggregate", 1 + d / 100),
                              "% more sand and stone, justified"),
    "wages (every trade)": ([0, 20, 40, 50, 60, 80, 100, 140],
                            lambda w, r, d: C.lab(C.lab(base(w, r), "mason", 1 + d / 100),
                                                  "beldar", 1 + d / 100),
                            "% above the district's wage"),
    "ghost labourers": ([0, 25, 50, 100, 150, 200],
                        lambda w, r, d: _workers(base(w, r), "beldar", 1 + d / 100),
                        "% more labourers, same days"),
    "'other' charges, tax in rates": ([0, 3, 5, 8, 10, 12, 15, 20],
                                      lambda w, r, d: _other(base(w, r), d / 100),
                                      "% of the lines"),
    "solar lights, MP agrees": ([90, 100, 115, 125, 130, 150, 200],
                                lambda w, r, d: C.lights(20_896 * d / 100),
                                "% of the district's 98th percentile"),
    "solar lights, MP 20% lower": ([90, 100, 115, 125, 130, 150, 200],
                                   lambda w, r, d: C.lights(20_896 * d / 100,
                                                            mp=20_896 * d / 100 * 10 / 1.2),
                                   "% of the district's 98th percentile"),
}


def main() -> None:
    a = argparse.ArgumentParser()
    a.add_argument("--honest", type=int, default=200)
    a.add_argument("--seeds", type=int, default=10)
    args = a.parse_args()
    worlds = {n: C.build_world(n, s, seed) for n, (s, seed) in C.WORLDS.items()}
    out: dict = {"honest": {}, "schemes": {}}
    lines = ["T167 Cost agent sweep: a random honest population and a dose curve per scheme", ""]

    lines.append(f"== Honest population ({args.honest} random honest filings per world, the "
                 "world's FULL honest spread)")
    for name, w in worlds.items():
        rng = random.Random(4242)
        tally, flagged = Counter(), []
        for k in range(args.honest):
            p, kind = honest(w, rng)
            r = C.assess(w, p)
            lv = L.level(r)
            tally[lv] += 1
            if lv in ("check", "ask"):
                flagged.append({"n": k, "kind": kind, "level": lv,
                                "codes": sorted(f.code for f in r.findings if f.risk > 0)})
        out["honest"][name] = {"tally": dict(tally), "flagged": flagged}
        lines.append(f"  {name:5s} " + "  ".join(f"{lv} {tally[lv]}" for lv in ORDER)
                     + f"   checked {tally['check'] / args.honest:.1%}, asked "
                       f"{tally['ask'] / args.honest:.1%}")
        for f in Counter(c for x in flagged for c in x["codes"]).most_common():
            lines.append(f"        {f[0]}: {f[1]}")
    lines.append("")

    for scheme, (doses, make, unit) in SCHEMES.items():
        lines.append(f"== {scheme} (dose = {unit}; {args.seeds} honest bases per dose and world)")
        out["schemes"][scheme] = {}
        for name, w in worlds.items():
            row = []
            for d in doses:
                tally, gaps = Counter(), []
                for s in range(args.seeds):
                    p = make(w, random.Random(77 + s), d)
                    # the MP's amount follows the estimate (the MP agrees), except where the
                    # scheme sets it (the lights)
                    r = C.assess(w, C.finish(p, mp_x=None if scheme.startswith("solar")
                                             else 1.0))
                    tally[L.level(r)] += 1
                    gap = (r.evidence.get("whole") or {}).get("gap_share")
                    if isinstance(gap, float):
                        gaps.append(gap)
                row.append((d, dict(tally), (min(gaps), max(gaps)) if gaps else None))
            out["schemes"][scheme][name] = row
            lines.append(f"  {name}")
            for d, t, g in row:
                cells = " ".join(f"{lv[0].upper()}{t.get(lv, 0):>2}" for lv in ORDER[1:])
                lines.append(f"    {d:>4}  {cells}   {_bar(t, args.seeds):10s}"
                             + (f"  whole estimate vs the market: {g[0]:+.0%} to {g[1]:+.0%}"
                                if g else ""))
        lines.append("")
    lines.append("Levels: F fits, E edge, C check, A ask (counts of the seeds). Bar: . fits/edge, "
                 "c check, A ask. The dose is on the agency's own honest prices, which already "
                 "sit a few % above or below the market; the agent sees only the market gap.")
    text = "\n".join(lines)
    print(text)
    (OUT / "t167_cost_sweep.txt").write_text(text + "\n", encoding="utf-8")
    (OUT / "t167_cost_sweep.json").write_text(json.dumps(out, indent=1), encoding="utf-8")


def _bar(t: dict, n: int) -> str:
    return ("." * (t.get("fits", 0) + t.get("edge", 0) + t.get("na", 0))
            + "c" * t.get("check", 0) + "A" * t.get("ask", 0))


if __name__ == "__main__":
    main()
