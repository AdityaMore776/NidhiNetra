r"""Trial (T080, 1 Oct 2026) - the planted-anomaly test: do the engines find 50 known problems?

The blueprint's proof step: copy the works, plant 50 labelled fakes, run the whole pipeline
blind, and report how many fakes reach the top 5% of the risk score (target 75%), the review
queue, and the engine meant to catch each one. Everything happens in memory on a copy of
data/build/works.parquet: no planted row ever reaches a database (source = SCENARIO).

The 50 fakes, built from real works chosen at random (seed 80), 10 of each kind:
  COST      a real work's amount raised 2x, 2.5x or 3x (the work itself is replaced, so no
            copy of it stays behind to look like a repeat)                 -> Cost Anomaly
  REPEAT    a real work filed again 60-300 days later in the same district, reworded
            ("construction of" -> "constructing", "cc road" -> "cement concrete road", ...),
            amount within 5%; the original stays                            -> Duplicate & Split
  SPLIT     a real Rs 12-20 lakh work replaced by 3, 3 and 4 pieces, each Rs 4.5-4.95 lakh,
            same text, place, office and day                                -> Duplicate & Split
  RULE      3 prohibited works (a temple, R07), 3 outside the constituency above Rs 25 lakh
            (R08), 2 big sums that say nothing (R12), 2 buildings complete in days (R13)
                                                                            -> Guideline Compliance
  TIMELINE  a completed work's completion date moved 30-200 days before its recommendation
            (R06)                                                           -> Guideline Compliance
Not planted: translated repeats (no offline translator; the duplicate rules compare words, so a
Hindi copy of an English work is expected to be missed - stated, not tested).

Writes results/planted_test.json (+ planted_test_rows.csv: one row per fake, work ids only).

Run:  apps\engine\.venv\Scripts\python.exe data\trial\planted_test.py
"""

from __future__ import annotations

import json
import random
import sys
import time
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "data"))

from common import BUILD, load_context, works_records  # noqa: E402
from drishti import config  # noqa: E402
from drishti.agents import registry  # noqa: E402
from drishti.agents.dup_split.match import place_words  # noqa: E402
from drishti.pipeline.orchestrator import assess_work  # noqa: E402

OUT = ROOT / "data" / "trial" / "results"
SEED = 80
TOP = 0.05
REVIEW = ("CRITICAL", "HIGH")
# which engine (and, for compliance, which rule) is meant to catch each kind
MEANT = {"COST": ("statistical", None), "REPEAT": ("dup_split", None),
         "SPLIT": ("dup_split", None), "TIMELINE": ("compliance", "R06")}
REWORD = [("construction of ", "constructing "), ("Construction of ", "Constructing "),
          ("cc road", "cement concrete road"), ("CC road", "cement concrete road"),
          ("CC Road", "Cement Concrete Road"), ("installation of ", "installing "),
          ("Installation of ", "Installing "), ("providing ", "supply of "),
          ("Providing ", "Supply of "), (" near ", " close to "), (" at ", " in "),
          (" village", " gram"), (" Village", " Gram")]


def reword(text: str) -> str:
    out = text
    for a, b in REWORD:
        out = out.replace(a, b)
    if out == text:                       # nothing to swap: change the order instead
        words = text.split()
        out = " ".join(words[1:] + words[:1]) if len(words) > 2 else text + " work"
    return out


def plant(works: pd.DataFrame, as_of: date) -> tuple[pd.DataFrame, list[dict]]:
    rng = random.Random(SEED)
    rows = works.to_dict("records")
    used: set[str] = set()
    fakes: list[dict] = []
    remove: set[str] = set()
    added: list[dict] = []

    def pick(cond, n):
        pool = [r for r in rows if r["work_id"] not in used and cond(r)]
        out = rng.sample(pool, n)
        used.update(r["work_id"] for r in out)
        return out

    def fake_id(kind, i):
        return f"SCENARIO-{kind}-{i:02d}"

    def replace(donor, kind, i, rule=None, **change):
        new = dict(donor) | change | {"work_id": fake_id(kind, i), "source": "SCENARIO"}
        remove.add(donor["work_id"])
        added.append(new)
        fakes.append({"work_id": new["work_id"], "kind": kind, "rule": rule,
                      "donor": donor["work_id"]})

    recent = lambda r: r["recommended_date"] and r["recommended_date"] >= date(2024, 7, 1)  # noqa: E731
    typed = lambda r: bool(r["work_type_code"]) and bool(place_words(r["description"]))  # noqa: E731

    # COST: 2x, 2.5x, 3x on ordinary works
    for i, d in enumerate(pick(lambda r: typed(r) and r["status"] != "RECOMMENDED"
                               and 100_000 <= (r["amount"] or 0) <= 1_000_000, 10)):
        k = (2.0, 2.5, 3.0)[i % 3]
        replace(d, "COST", i, amount=round(d["amount"] * k))
        fakes[-1]["times"] = k

    # REPEAT: the same work filed again, reworded; the original stays
    for i, d in enumerate(pick(lambda r: typed(r) and recent(r)
                               and r["recommended_date"] <= as_of - timedelta(days=90), 10)):
        later = min(as_of, d["recommended_date"] + timedelta(days=rng.randint(60, 300)))
        new = dict(d) | {"work_id": fake_id("REPEAT", i), "source": "SCENARIO",
                         "description": reword(d["description"]),
                         "amount": round(d["amount"] * rng.uniform(0.95, 1.05), -2),
                         "recommended_date": later, "status": "RECOMMENDED",
                         "completed_date": None}
        added.append(new)
        fakes.append({"work_id": new["work_id"], "kind": "REPEAT", "rule": None,
                      "donor": d["work_id"]})

    # SPLIT: one Rs 12-20 lakh work becomes 3, 3 and 4 pieces just under Rs 5 lakh
    n = 0
    for size, d in zip((3, 3, 4), pick(lambda r: typed(r) and recent(r)
                                       and 1_200_000 <= (r["amount"] or 0) <= 2_000_000, 3),
                       strict=True):
        remove.add(d["work_id"])
        for _ in range(size):
            new = dict(d) | {"work_id": fake_id("SPLIT", n), "source": "SCENARIO",
                             "amount": round(rng.uniform(450_000, 495_000), -2)}
            added.append(new)
            fakes.append({"work_id": new["work_id"], "kind": "SPLIT", "rule": None,
                          "donor": d["work_id"]})
            n += 1

    # RULE breaches, each on a real work's record
    i = 0
    for d in pick(lambda r: typed(r) and r["status"] != "RECOMMENDED", 3):
        replace(d, "RULE", i, rule="R07",
                description=f"Construction of temple in village {d['district_name']}")
        i += 1
    for d in pick(lambda r: typed(r) and not r["is_outside_constituency"], 3):
        replace(d, "RULE", i, rule="R08", is_outside_constituency=True,
                amount=float(rng.choice((3_000_000, 4_000_000, 5_000_000))))
        i += 1
    for d in pick(lambda r: r["work_type_code"] == "COMMUNITY_HALL", 2):
        replace(d, "RULE", i, rule="R12", description="Construction of community hall",
                amount=4_000_000.0)
        i += 1
    for d in pick(lambda r: r["work_type_code"] in ("COMMUNITY_HALL", "ROAD_CC")
                  and r["status"] == "COMPLETED" and recent(r)
                  and 500_000 <= (r["amount"] or 0) <= 1_500_000, 2):
        replace(d, "RULE", i, rule="R13",
                completed_date=d["recommended_date"] + timedelta(days=5))
        i += 1

    # TIMELINE: completed before it was recommended
    for i, d in enumerate(pick(lambda r: r["status"] == "COMPLETED" and recent(r)
                               and r["completed_date"] is not None, 10)):
        replace(d, "TIMELINE", i, rule="R06",
                completed_date=d["recommended_date"] - timedelta(days=rng.randint(30, 200)))

    kept = [r for r in rows if r["work_id"] not in remove]
    out = pd.DataFrame(kept + [{k: v for k, v in a.items() if k in works.columns}
                               for a in added], columns=works.columns)
    return out, fakes


def cost_sweep(works: pd.DataFrame, fakes: list[dict], ctx) -> dict:
    """The same 10 cost fakes at other mark-ups, through the Cost engine alone: where does it
    start asking? (It asks only beyond its comfort limit, about twice the usual top.)"""
    cost = next(e for e in registry.engines() if e.id == "statistical")
    base = {r["work_id"]: r for r in works_records(works[works.work_id.isin(
        [f["work_id"] for f in fakes if f["kind"] == "COST"])])}
    out = {}
    for times in (2.0, 3.0, 5.0, 10.0):
        hit = 0
        for f in fakes:
            if f["kind"] != "COST":
                continue
            w = base[f["work_id"]]
            hit += cost.assess(w | {"amount": w["amount"] / f["times"] * times}, ctx).risk > 0
        out[f"{times:g}x"] = {"n": 10, "hit": int(hit), "share": round(hit / 10, 2)}
    return out


def main() -> None:
    real = pd.read_parquet(BUILD / "works.parquet")
    as_of = config.snapshot_date()
    works, fakes = plant(real, as_of)
    assert len(fakes) == 50, len(fakes)
    ctx = load_context(works)                # the indexes see the fakes; the stats do not
    t0 = time.time()
    scores, eng = {}, defaultdict(dict)
    detail: dict[str, dict] = {}
    fake_ids = {f["work_id"] for f in fakes}
    for w in works_records(works):
        a = assess_work(w, ctx)
        scores[w["work_id"]] = (a.fused.score, a.fused.band)
        for r in a.agents:
            eng[r.agent][w["work_id"]] = r.risk
        if w["work_id"] in fake_ids:
            detail[w["work_id"]] = {
                "band": a.fused.band, "score": round(a.fused.score, 4),
                "rules": sorted({f.evidence.get("rule") for r in a.agents
                                 if r.agent == "compliance" for f in r.findings}),
                "engines_fired": sorted(r.agent for r in a.agents if r.risk > 0),
                "reasons": [x["label"] + ": " + x["text_en"][:160] for x in a.fused.reasons]}
    print(f"assessed {len(scores):,} works in {time.time() - t0:.0f}s")

    s = pd.Series({k: v[0] for k, v in scores.items()})
    cut = s.quantile(1 - TOP)
    rows = []
    for f in fakes:
        d = detail[f["work_id"]]
        engine, rule = MEANT.get(f["kind"], ("compliance", f["rule"]))
        sig = pd.Series(eng[engine])
        mine = sig[f["work_id"]]
        caught = mine > 0 and (rule is None or rule in d["rules"])
        rows.append(f | {"score": d["score"], "band": d["band"],
                         "top5_overall": bool(d["score"] > cut or
                                              (d["score"] == cut and d["score"] > 0)),
                         "queued": d["band"] in REVIEW,
                         "medium_or_above": d["band"] in REVIEW + ("MEDIUM",),
                         "meant_engine": engine, "meant_engine_caught": bool(caught),
                         "top5_in_engine": bool(mine > 0 and mine >= sig.quantile(1 - TOP)),
                         "engines_fired": d["engines_fired"], "reasons": d["reasons"]})
    df = pd.DataFrame(rows)

    def share(col, by=None):
        if by is None:
            return {"n": len(df), "hit": int(df[col].sum()), "share": round(df[col].mean(), 3)}
        return {k: {"n": len(g), "hit": int(g[col].sum()), "share": round(g[col].mean(), 3)}
                for k, g in df.groupby(by)}

    res = {"as_of": as_of.isoformat(), "seed": SEED, "works_scored": len(scores),
           "top5_score_cut": round(float(cut), 4),
           "real_bands": dict(Counter(v[1] for k, v in scores.items() if k not in fake_ids)),
           "overall": {"top5": share("top5_overall"), "queue": share("queued"),
                       "medium_or_above": share("medium_or_above"),
                       "meant_engine_caught": share("meant_engine_caught"),
                       "top5_in_meant_engine": share("top5_in_engine")},
           "by_kind": {"top5": share("top5_overall", "kind"), "queue": share("queued", "kind"),
                       "meant_engine_caught": share("meant_engine_caught", "kind")},
           "cost_sweep": cost_sweep(works, fakes, ctx),
           "rules": share("meant_engine_caught", df["rule"].fillna("-")),
           "target": "blueprint: 75% of fakes in the top 5% of the risk score",
           "not_planted": "translated repeats (no offline translator)"}
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "planted_test.json").write_text(json.dumps(res, indent=2, default=str),
                                           encoding="utf-8")
    df.drop(columns=["reasons"]).to_csv(OUT / "planted_test_rows.csv", index=False)
    print(json.dumps(res, indent=2, default=str))
    for r in df.itertuples():
        rule = r.rule if isinstance(r.rule, str) else ""
        print(f"{r.work_id:20} {r.kind:8} {rule:4} {r.band:8} {r.score:.3f} "
              f"caught={r.meant_engine_caught} top5={r.top5_overall} | "
              + " / ".join(x[:110] for x in r.reasons[:2]))


if __name__ == "__main__":
    main()
