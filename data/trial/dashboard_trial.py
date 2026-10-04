r"""Trial (2 Oct 2026): every engine on the eSAKSHI dashboard's own exports, an unseen snapshot.

The engines were built and tuned on the research export (2,09,993 works, 26 May 2026). The
dashboard tables downloaded on 2 Oct 2026 (data/esakshi_dashboard.py: 40,935 works, with real
sanction dates, disbursed money and photo flags) were never seen by any rule. This script runs the
whole pipeline on them as they stand that day:

  statistics     peer bands, durations, road curve and impossible-date rates are rebuilt from these
                 works (drishti/evaluation/stats.py, the method of data/build_stats.py), and the
                 word-price model is refitted on them (the method of data/build_price_model.py:
                 words in 20+ constituencies, ridge, per-type out-of-fold spreads by constituency)
  today          2 Oct 2026, the newest date in the tables

Writes results/dashboard_<tag>.json (bands, queue, how often each engine and finding fires) and
results/dashboard_<tag>_queue.csv + _codes.csv (random queue works and random works per finding,
descriptions masked with validation/pii.py, for reading by eye; labels in
dashboard_labels.py), and results/dashboard_<tag>_flags.json (the work ids each finding rarer
than 2,000 flags fired on, to compare two runs work by work). Work ids only, never a person.

Run: apps\engine\.venv\Scripts\python.exe data\trial\dashboard_trial.py --tag baseline
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
sys.path.insert(0, str(ROOT / "data"))

from esakshi_dashboard import load  # noqa: E402

from drishti.batch import indexes  # noqa: E402
from drishti.evaluation.stats import build_store  # noqa: E402
from drishti.fusion import fuse  # noqa: E402
from drishti.pipeline.orchestrator import Context, assess_work  # noqa: E402
from drishti.validation import pii  # noqa: E402

OUT = ROOT / "data" / "trial" / "results"
REVIEW = ("CRITICAL", "HIGH")
SEED = 1002
FLAG_LIST_MAX = 2000


def fit_price_model(works: list[dict]) -> dict | None:
    """The word-price model on these works (build_price_model.py's method), or None without
    scikit-learn."""
    try:
        import numpy as np
        from sklearn.feature_extraction import DictVectorizer
        from sklearn.linear_model import Ridge
        from sklearn.model_selection import GroupKFold
    except ImportError:
        return None
    from drishti.agents.statistical.price_model import features

    w = [x for x in works if x.get("amount") and x.get("work_type_code")]
    feats = [features(x) for x in w]
    groups = np.array([x.get("constituency") or "?" for x in w])
    spread_of: dict[str, set] = defaultdict(set)
    for f, g in zip(feats, groups, strict=True):
        for k in f:
            if k.startswith("w="):
                spread_of[k].add(g)
    keep = {k for k, s in spread_of.items() if len(s) >= 20}
    feats = [{k: v for k, v in f.items() if not k.startswith("w=") or k in keep} for f in feats]
    dv = DictVectorizer(sparse=True)
    x = dv.fit_transform(feats)
    y = np.log10(np.array([float(r["amount"]) for r in w]))
    oof = np.zeros(len(w))
    for tr, te in GroupKFold(n_splits=5).split(x, y, groups):
        oof[te] = Ridge(alpha=3.0).fit(x[tr], y[tr]).predict(x[te])
    resid = y - oof
    types = np.array([r["work_type_code"] for r in w])
    spread = {str(t): (float(np.quantile(resid[types == t], 0.10)),
                       float(np.quantile(resid[types == t], 0.90))) for t in np.unique(types)}
    final = Ridge(alpha=3.0).fit(x, y)
    weights = {str(n): float(c) for n, c in zip(dv.get_feature_names_out(), final.coef_,
                                                strict=True) if abs(c) > 1e-6}
    return {"version": "price-linear-dashboard", "intercept": float(final.intercept_),
            "weights": weights, "spread": spread,
            "default_spread": [float(np.quantile(resid, 0.10)), float(np.quantile(resid, 0.90))],
            "oof_median_abs_error_factor": round(float(10 ** np.median(np.abs(resid))), 3),
            "oof_share_inside": round(float(np.mean([lo <= r <= hi for r, (lo, hi) in zip(
                resid, (spread[t] for t in types), strict=True)])), 3)}


def assess_all(works: list[dict], as_of, model: dict | None):
    models = [{"name": "price_model", "data": model}] if model else []
    stats = build_store(works, models)
    ctx = Context(stats=stats, as_of=as_of, data=indexes(works))
    return [(w, assess_work(w, ctx)) for w in works]


def office_habits(works: list[dict]) -> dict | None:
    """How many offices have a routine habit (Office Patterns), counts only: no office named."""
    try:
        from drishti.agents.office_patterns.index import OfficeIndex
    except ImportError:          # engines from before 2 Oct 2026
        return None
    idx = OfficeIndex.build(works)
    out: dict[str, dict] = {}
    for r in idx.routine_offices():
        h = out.setdefault(r["habit"], {"offices": 0, "works": 0, "national_share": r["national"],
                                        "shares": []})
        h["offices"] += 1
        h["works"] += r["count"]
        h["shares"].append(r["share"])
    for h in out.values():
        s = sorted(h.pop("shares"))
        h["median_office_share"] = s[len(s) // 2]
    return out


def row(w: dict, a) -> dict:
    return {"work_id": w["work_id"], "band": a.fused.band, "score": round(a.fused.score, 4),
            "status": w["status"], "type": w["work_type_code"], "amount": w["amount"],
            "district": w["district_name"], "state": w["state_name"],
            "recommended": str(w["recommended_date"] or ""), "sanctioned":
            str(w["sanction_date"] or ""), "completed": str(w["completed_date"] or ""),
            "description": pii.mask(str(w["description"] or ""))[:300],
            "codes": ";".join(f"{r.agent}:{f.code}" for r in a.agents if r.assessed
                              for f in r.findings if f.risk > 0),
            # a reason can quote the description ("the same place named ..."), so mask it too
            "reasons": pii.mask(" | ".join(f"{r['label']}: {r['text_en'][:220]}"
                                           for r in a.fused.reasons))}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="baseline")
    ap.add_argument("--no-model", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    works, info = load()
    model = None if args.no_model else fit_price_model(works)
    results = assess_all(works, info["as_of"], model)
    n = len(results)
    bands = Counter(a.fused.band for _w, a in results)
    engine_fired, code_fired, status = Counter(), Counter(), Counter()
    by_code: dict[str, list[dict]] = defaultdict(list)
    rows = []
    for w, a in results:
        r = row(w, a)
        rows.append(r)
        for res in a.agents:
            status[(res.agent, res.status.value)] += 1
            codes = {f.code for f in res.findings if f.risk > 0} if res.assessed else set()
            if codes:
                engine_fired[res.agent] += 1
            for c in codes:
                code_fired[f"{res.agent}:{c}"] += 1
                by_code[f"{res.agent}:{c}"].append(r)
    queue = [r for r in rows if r["band"] in REVIEW]
    # how many queued works carry each finding (T125: what the queue is made of)
    queued_code = Counter(c for code, rs in by_code.items() for r in rs
                          if r["band"] in REVIEW for c in [code])
    rng = random.Random(SEED)
    res = {"tag": args.tag, "works": n, "as_of": str(info["as_of"]), "loader": {
               k: v for k, v in info.items() if k not in ("as_of", "unmapped_categories")},
           "price_model": None if model is None else {
               k: model[k] for k in ("version", "oof_median_abs_error_factor",
                                     "oof_share_inside")},
           "cutoffs": {"CRITICAL": fuse.CRITICAL, "HIGH": fuse.HIGH, "MEDIUM": fuse.MEDIUM},
           "bands": {b: bands.get(b, 0) for b in ("CRITICAL", "HIGH", "MEDIUM", "LOW")},
           "review_queue": len(queue), "review_share": round(len(queue) / n, 5),
           "engine_fired": {k: v for k, v in sorted(engine_fired.items())},
           "finding_fired": {k: v for k, v in code_fired.most_common()},
           "queued_with_finding": {k: v for k, v in queued_code.most_common()},
           "engine_status": {f"{a}:{s}": c for (a, s), c in sorted(status.items())},
           "office_habits": office_habits(works),
           "seconds": round(time.time() - t0)}
    (OUT / f"dashboard_{args.tag}.json").write_text(json.dumps(res, indent=2), encoding="utf-8")
    fields = list(rows[0])
    with (OUT / f"dashboard_{args.tag}_queue.csv").open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=fields)
        wr.writeheader()
        wr.writerows(rng.sample(queue, min(40, len(queue))))
    with (OUT / f"dashboard_{args.tag}_codes.csv").open("w", newline="", encoding="utf-8") as f:
        wr = csv.DictWriter(f, fieldnames=["sample_code"] + fields)
        wr.writeheader()
        for code, rs in sorted(by_code.items()):
            for r in rng.sample(rs, min(12, len(rs))):
                wr.writerow({"sample_code": code, **r})
    # which works each rarer finding fired on (ids only), so two runs can be compared work by
    # work (e.g. main's R07 reader against a branch's); the common notes are left out
    flags = {code: sorted(r["work_id"] for r in rs) for code, rs in sorted(by_code.items())
             if len(rs) < FLAG_LIST_MAX}
    (OUT / f"dashboard_{args.tag}_flags.json").write_text(json.dumps(flags, indent=0),
                                                          encoding="utf-8")
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
