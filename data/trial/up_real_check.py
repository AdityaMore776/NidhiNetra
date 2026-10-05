r"""The four agents on one region's real works: Uttar Pradesh (T136).

The owner (5 Oct 2026): "try to find valid data, you can choose a single specific region or state
... which has available data for you to train and test agents on actual examples". Uttar Pradesh is
the largest state in the eSAKSHI dashboard tables (data/esakshi_dashboard.py: 8,702 of 40,935
works; Jaunpur, the work form's demo district, alone 1,038). The tables are real works as the
public dashboard shows them on 2 Oct 2026; no implementing agency has filed the new cost estimate
form yet, so what can be tested on them is:

  1. every agent on every UP work, as the batch runs it (the whole country's works in the index):
     no agent may fail (an ERROR result); how often each one answers, and what it asks
  2. the Time & Rules agent's caps against UP's own finished works (sanction to completion, by
     type): does the national "longest usual time" hold for UP?
  3. UP's real prices per unit of size (reference/cost/uttar_pradesh.json, built from these works):
     the yardstick the demo's honest filings must sit inside (data/trial/end_to_end_examples.py)

Writes results/up_real_check.txt and .json: counts, percentiles and work ids only, never a
description or a person.

Run:  apps\engine\.venv\Scripts\python.exe data\trial\up_real_check.py
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
sys.path.insert(0, str(ROOT / "data"))

from build_time_bands import p  # noqa: E402
from esakshi_dashboard import load  # noqa: E402

from drishti.agents.contract import Status  # noqa: E402
from drishti.batch import indexes  # noqa: E402
from drishti.evaluation.stats import build_store  # noqa: E402
from drishti.pipeline.orchestrator import Context, assess_work  # noqa: E402

STATE = "Uttar Pradesh"
DISTRICT = "Jaunpur"
OUT = ROOT / "data" / "trial" / "results" / "up_real_check"
REF = ROOT / "apps" / "engine" / "drishti" / "reference"
AGENTS = ("cost_estimate", "dup_split", "time_rules", "site_progress")
MIN_WORKS = 30


def agents_on(works: list[dict], as_of) -> dict:
    """1. Every agent on every UP work, as the batch runs it."""
    ctx = Context(stats=build_store(works), as_of=as_of, data=indexes(works))
    up = [w for w in works if w.get("state_name") == STATE]
    status, fired, bands, errors = Counter(), Counter(), Counter(), Counter()
    flagged: dict[str, list[str]] = defaultdict(list)
    slowest, t0 = 0.0, time.perf_counter()
    for w in up:
        t = time.perf_counter()
        a = assess_work(w, ctx)
        slowest = max(slowest, time.perf_counter() - t)
        bands[a.fused.band] += 1
        for r in a.agents:
            status[(r.agent, r.status.value)] += 1
            if r.status == Status.ERROR:
                errors[r.agent] += 1
            for f in r.findings:
                if f.risk > 0 and r.status == Status.ASSESSED:
                    fired[f"{r.agent}:{f.code}"] += 1
                    if len(flagged[f"{r.agent}:{f.code}"]) < 10:
                        flagged[f"{r.agent}:{f.code}"].append(w["work_id"])
    took = time.perf_counter() - t0
    return {"works": len(up), "districts": len({w.get("district_name") for w in up}),
            "in_district": sum(w.get("district_name") == DISTRICT for w in up),
            "status": {a: {s: n for (ag, s), n in sorted(status.items()) if ag == a}
                       for a in AGENTS},
            "errors": dict(errors), "fired": dict(fired.most_common()),
            "flagged_examples": dict(flagged),
            "bands": {b: bands.get(b, 0) for b in ("CRITICAL", "HIGH", "MEDIUM", "LOW")},
            "seconds": round(took, 1), "ms_per_work": round(1000 * took / max(1, len(up)), 2),
            "slowest_ms": round(1000 * slowest, 1)}


def timelines(works: list[dict]) -> dict:
    """2. UP's finished works against the Time agent's national caps."""
    bands = json.loads((REF / "time_bands.json").read_text(encoding="utf-8"))
    up, india = defaultdict(list), defaultdict(list)
    for w in works:
        s, c = w.get("sanction_date"), w.get("completed_date")
        if s and c and c >= s:
            india[w["work_type_code"]].append((c - s).days)
            if w.get("state_name") == STATE:
                up[w["work_type_code"]].append((c - s).days)
    rows = []
    for t, v in sorted(up.items(), key=lambda kv: -len(kv[1])):
        nat = bands["types"].get(t)
        if len(v) < MIN_WORKS or not nat:
            continue
        rows.append({"type": t, "works": len(v), "p50": p(v, 50), "p90": p(v, 90),
                     "india_p50": nat["p50"], "india_p90": nat["p90"],
                     "p90_vs_india": round(p(v, 90) / nat["p90"] - 1, 3),
                     "within_india_p90": round(sum(d <= nat["p90"] for d in v) / len(v), 3)})
    lags = [(w["sanction_date"] - w["recommended_date"]).days for w in works
            if w.get("state_name") == STATE and w.get("recommended_date") and w.get("sanction_date")
            and w["sanction_date"] >= w["recommended_date"]]
    return {"types": rows, "sanction_lag": {
        "works": len(lags), "p50": p(lags, 50) if lags else None,
        "share_past_75_days": round(sum(x > 75 for x in lags) / len(lags), 3) if lags else None,
        "india_p50": bands["sanction_lag"]["p50"],
        "india_share_past_75_days": bands["sanction_lag"]["share_past"]["75"]}}


def prices() -> dict:
    """3. UP's real prices per unit of size (the Cost agent's standard items)."""
    ref = json.loads((REF / "cost" / "uttar_pradesh.json").read_text(encoding="utf-8"))
    out = {}
    for group, g in sorted(ref["groups"].items()):
        st = g["state"]
        if st["n"] < MIN_WORKS:
            continue
        out[group] = {"unit": g["unit"], **{k: st[k] for k in ("n", "p10", "median", "p90", "p98",
                                                              "tight")},
                      "district": {d: {k: v[k] for k in ("n", "median", "p90", "tight")}
                                   for d, v in g["districts"].items() if d == DISTRICT}}
    return {"source": ref["source"], "groups": out}


def main() -> None:
    works, info = load()
    res = {"state": STATE, "as_of": str(info["as_of"]), "all_works": len(works),
           "agents": agents_on(works, info["as_of"]), "timelines": timelines(works),
           "prices": prices()}
    a, tl, pr = res["agents"], res["timelines"], res["prices"]["groups"]
    lines = [f"Uttar Pradesh on the eSAKSHI dashboard tables ({len(works):,} works, as of "
             f"{info['as_of']}): {a['works']:,} works in {a['districts']} districts "
             f"({DISTRICT} {a['in_district']:,})", "",
             f"1. The four agents on every UP work: {a['seconds']} s ({a['ms_per_work']} ms a "
             f"work, slowest {a['slowest_ms']} ms); agent errors: {sum(a['errors'].values())}"]
    for ag in AGENTS:
        lines.append(f"   {ag:14} " + ", ".join(f"{s} {n:,}" for s, n in a["status"][ag].items()))
    lines.append("   asked: " + (", ".join(f"{k} {v:,}" for k, v in a["fired"].items()) or "none"))
    lines.append("   bands: " + ", ".join(f"{k} {v:,}" for k, v in a["bands"].items()))
    lines += ["", "2. UP's finished works against the Time agent's national caps (sanction to "
              "completion, days)"]
    for r in tl["types"]:
        lines.append(f"   {r['type']:16} {r['works']:5,} works: UP p50 {r['p50']:5.0f}, p90 "
                     f"{r['p90']:5.0f} | India p50 {r['india_p50']:5.0f}, p90 "
                     f"{r['india_p90']:5.0f} | UP p90 {r['p90_vs_india']:+.1%} | within India's "
                     f"p90: {r['within_india_p90']:.1%}")
    lag = tl["sanction_lag"]
    lines.append(f"   recommendation to sanction: UP median {lag['p50']} days ({lag['works']:,} "
                 f"works), {lag['share_past_75_days']:.1%} past 75 days; India median "
                 f"{lag['india_p50']}, {lag['india_share_past_75_days']:.1%} past 75 days")
    lines += ["", f"3. UP's real prices per unit of size ({res['prices']['source']}; groups with "
              f"{MIN_WORKS}+ works)"]
    for g, r in pr.items():
        dist = r["district"].get(DISTRICT)
        lines.append(f"   {g:14} {r['unit']:10} {r['n']:5,} works: p10 {r['p10']:>9,}, median "
                     f"{r['median']:>9,}, p90 {r['p90']:>9,}, p98 {r['p98']:>9,}"
                     f"{' (tight)' if r['tight'] else ''}"
                     + (f" | {DISTRICT}: {dist['n']} works, median {dist['median']:,}"
                        f"{' (tight)' if dist['tight'] else ''}" if dist else ""))
    text = "\n".join(lines) + "\n"
    print(text)
    OUT.with_suffix(".txt").write_text(text, encoding="utf-8")
    OUT.with_suffix(".json").write_text(json.dumps(res, indent=1, default=str) + "\n",
                                        encoding="utf-8")


if __name__ == "__main__":
    main()
