r"""Trial 1b (T020, 30 Sept 2026) - the Cost engine v2 against v1, on real works.

The owner found the live cost agent (v1) giving odd answers: a library building judged
against book orders ("typical Rs 10,000", hundreds of times typical), many works at the
identical "5.0x", every queued work at the same score. v2 (agents/statistical/agent.py)
changes what is compared and how. This script measures both the same way.

Question 1, planted mark-ups (as trial 1):
  - take 1,000 real works, rebuild the peer bands WITHOUT them, multiply each amount by
    1.5 / 2 / 3 / 5 / 10 and count how many each version flags
  - false alarms: 20,000 untouched works run through the same bands
  - two test pools: trial 1's pool (works v1 reads as typical, with a district cohort:
    this pool favours v1) and a random pool of described single-site works
  - version B's learned range for every work comes from a model that never saw the
    work's constituency (data/build_cost_model.py), so a planted amount never reaches
    the model that judges it

Question 2, what the flags are on the REAL corpus: every version is run on all works;
the flag counts, the share with identical ratios, and a sample for reading by eye
(results/cost_v2_flag_sample_{dev,test}.csv; the labels, and what they mean, are in
cost_v2_labels.py, and the precision is computed from them).

Variants:
  v1     the frozen live agent (cost_v1_agent.py) on v1 bands
  A      v2 rules on scope-aware peers (no model)
  B      v2 reading gates + the learned range alone (USE_PEERS off)
  A+B    v2 rules AND the learned range must agree (the engine's default when loaded)

Run:  .venv-trial\Scripts\python.exe data\trial\cost_trial_v2.py
"""

from __future__ import annotations

import json
import sys
from datetime import date
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
sys.path.insert(0, str(ROOT / "data"))
sys.path.insert(0, str(ROOT / "data" / "trial"))

import cost_v1_agent  # noqa: E402
import cost_v2_labels as labels  # noqa: E402
from build_stats import clean_mask, cohorts, cost_cohorts, scope_frame  # noqa: E402
from drishti.agents.statistical import agent as v2  # noqa: E402
from drishti.agents.statistical.band import MIN_COHORT  # noqa: E402
from drishti.agents.statistical.cohort import StatsStore  # noqa: E402

BUILD = ROOT / "data" / "build"
OUT = ROOT / "data" / "trial" / "results"
FACTORS = (1.5, 2.0, 3.0, 5.0, 10.0)
V1_FLAGS = {"COST_ABOVE_PEERS", "BUNDLED_SANCTION", "UNIT_RATE_ABOVE"}
V2_FLAGS = {"COST_ABOVE_PEERS", "BUNDLED_SANCTION", "UNIT_RATE_ABOVE", "UNIT_PRICE_ABOVE",
            "SCOPE_FAR_LARGER"}
AS_OF = date(2026, 5, 26)



def clean(rec: dict) -> dict:
    return {k: (None if (isinstance(v, float) and np.isnan(v)) or v is pd.NaT else v)
            for k, v in rec.items()}


def store(bands: pd.DataFrame) -> StatsStore:
    return StatsStore.from_rows(bands[bands.n >= MIN_COHORT].to_dict("records"),
                                pd.read_parquet(BUILD / "duration_stats.parquet").to_dict("records"),
                                pd.read_parquet(BUILD / "unit_rate_models.parquet").to_dict("records"))


def run_v1(rec: dict, stats: StatsStore):
    return cost_v1_agent.assess(rec, stats, AS_OF)


def run_v2(rec: dict, stats: StatsStore, model: str):
    """model: 'A' (no learned range), 'B' (learned range alone), 'AB' (both agree)."""
    r = dict(rec)
    if model == "A":
        r.pop("cost_expected", None)
    v2.USE_PEERS = model != "B"
    try:
        return v2.assess(r, stats, AS_OF)
    finally:
        v2.USE_PEERS = True


def is_flag(res, codes) -> bool:
    return res.status.value == "ASSESSED" and any(f.code in codes for f in res.findings)


def main() -> None:
    w = pd.read_parquet(BUILD / "works.parquet")
    w = w[(w.amount > 0) & w.work_type_code.notna()].copy()
    w["l"] = np.log10(w.amount.astype(float))
    exp = pd.read_parquet(BUILD / "cost_expected.parquet").set_index("work_id")
    sf = scope_frame(w)

    # ---- pools (trial 1's pool is rebuilt exactly as trial 1 did)
    full = cohorts(w)
    td = full[(full.level == "type_district") & (full.n >= MIN_COHORT)].set_index(
        ["work_type_code", "key"])
    m = td.reindex(pd.MultiIndex.from_arrays([w.work_type_code, w.district_lgd]))
    z_now = (w.l.values - m.p50.values) / m.sd.values
    pool1 = w[m.n.notna().values & ~sf.bundle.values & (np.abs(z_now) < 2)].sample(
        n=1000, random_state=26)
    rest1 = w.drop(pool1.index)
    pool2 = rest1[clean_mask(sf.loc[rest1.index]).values].sample(n=1000, random_state=28)
    rest = rest1.drop(pool2.index)
    control = rest.sample(n=20000, random_state=27)

    s_v1 = store(cohorts(rest))
    s_v2 = store(cost_cohorts(rest, sf.loc[rest.index]))

    def records(df: pd.DataFrame, factor: float = 1.0):
        for rec in df.to_dict("records"):
            r = clean(rec)
            r["amount"] = float(r["amount"]) * factor
            if r["work_id"] in exp.index:
                e = exp.loc[r["work_id"]]
                r["cost_expected"] = {"q10": float(e.q10), "q50": float(e.q50),
                                      "q90": float(e.q90)}
            yield r

    variants = {
        "v1": lambda r: is_flag(run_v1(r, s_v1), V1_FLAGS),
        "A": lambda r: is_flag(run_v2(r, s_v2, "A"), V2_FLAGS),
        "B": lambda r: is_flag(run_v2(r, s_v2, "B"), V2_FLAGS),
        "A+B": lambda r: is_flag(run_v2(r, s_v2, "AB"), V2_FLAGS),
    }
    planted = {}
    for name, fn in variants.items():
        res = {"false_alarm_rate": float(np.mean([fn(r) for r in records(control)]))}
        for pname, pool in (("pool_trial1", pool1), ("pool_random_clean", pool2)):
            res[pname] = {f"caught_x{f:g}": float(np.mean([fn(r) for r in records(pool, f)]))
                          for f in FACTORS}
        planted[name] = res
        print(name, json.dumps(res), flush=True)

    # ---- the real corpus: what each version flags
    s_full_v1 = store(cohorts(w))
    s_full_v2 = store(cost_cohorts(w, sf))
    rows = []
    for r in records(w):
        out = {"work_id": r["work_id"]}
        a = run_v1(r, s_full_v1)
        f1 = [f for f in a.findings if f.code in V1_FLAGS]
        out["v1"] = f1[0].code if f1 else ""
        out["v1_ratio"] = next((f.evidence.get("ratio") for f in f1 if "ratio" in f.evidence),
                               None)
        for name, model in (("A", "A"), ("A+B", "AB")):
            b = run_v2(r, s_full_v2, model)
            fs = sorted((f for f in b.findings if f.code in V2_FLAGS), key=lambda f: -f.risk)
            out[name] = fs[0].code if fs else ""
            out[f"{name}_risk"] = fs[0].risk if fs else 0.0
            out[f"{name}_text"] = fs[0].text if fs else ""
            out[f"{name}_top"] = fs[0].evidence.get("top_ratio") if fs else None
        rows.append(out)
    real = pd.DataFrame(rows).merge(
        w[["work_id", "work_type_code", "district_name", "amount", "description"]], on="work_id")
    corpus = {}
    for name in ("v1", "A", "A+B"):
        flagged = real[real[name] != ""]
        ratio_col = "v1_ratio" if name == "v1" else f"{name}_top"
        rr = flagged[ratio_col].dropna().round(1)
        corpus[name] = {
            "flagged": int(len(flagged)),
            "by_code": flagged[name].value_counts().to_dict(),
            "most_common_ratio_share": float(rr.value_counts(normalize=True).iloc[0]) if len(rr) else 0,
            "top5_ratios": {str(k): int(v) for k, v in rr.value_counts().head(5).items()},
            "library_flags": int((flagged.work_type_code == "LIBRARY").sum()),
        }
        if name != "v1":
            corpus[name]["risk_quartiles"] = [round(float(q), 3) for q in
                                              flagged[f"{name}_risk"].quantile([.25, .5, .75])]
    print(json.dumps(corpus, indent=2))

    # ---- by eye. DEV: the first sample, already read (cost_v2_flag_sample_dev.csv, labels
    # in cost_v2_labels.DEV). TEST: drawn after the rules froze: the 30 highest-risk flags
    # plus 30 random flags never seen in DEV or DEV2 (seed 32).
    seen = (set(labels.V1_DEV) | set(labels.AB_DEV) | set(labels.V1_DEV2)
            | set(labels.AB_DEV2))
    samples = []
    for name in ("v1", "A+B"):
        flagged = real[real[name] != ""]
        key = "v1_ratio" if name == "v1" else f"{name}_risk"
        top = flagged.sort_values(key, ascending=False).head(30)
        pool = flagged.drop(top.index)
        pool = pool[~pool.work_id.isin(seen)]
        rnd = pool.sample(n=min(30, len(pool)), random_state=32)
        for part, df in (("top", top), ("random", rnd)):
            for x in df.to_dict("records"):
                samples.append({"version": name, "part": part, "work_id": x["work_id"],
                                "type": x["work_type_code"], "amount": x["amount"],
                                "district": x["district_name"],
                                "description": str(x["description"])[:300],
                                "flag": x[name],
                                "text": x["A+B_text"] if name != "v1" else ""})
    sample = pd.DataFrame(samples)
    OUT.mkdir(parents=True, exist_ok=True)
    sample.to_csv(OUT / "cost_v2_flag_sample_test.csv", index=False)

    def precision(df: pd.DataFrame, lab_of) -> dict:
        out = {}
        for name in ("v1", "A+B"):
            s = df[df.version == name]
            lab = s.work_id.map(lab_of(name))
            if lab.notna().any():
                out[name] = {part: {"read": int(lab[s.part == part].notna().sum()),
                                    "like_for_like": int((lab[s.part == part] == "like").sum())}
                             for part in ("top", "random")}
        return out

    v1_all = {**labels.V1_DEV, **labels.V1_DEV2}
    ab_all = {**labels.AB_DEV, **labels.AB_DEV2}
    dev = pd.read_csv(OUT / "cost_v2_flag_sample_dev.csv")
    dev_p = precision(dev, lambda n: labels.V1_DEV if n == "v1" else labels.AB_DEV)
    dev2 = pd.read_csv(OUT / "cost_v2_flag_sample_dev2.csv")
    dev2_p = precision(dev2, lambda n: v1_all if n == "v1" else ab_all)
    # a TEST work already read in a DEV sample (e.g. v1's top, which never changes) keeps
    # its earlier label
    test_p = precision(sample, lambda n: {**(v1_all if n == "v1" else ab_all), **labels.TEST})
    result = {"test_works_per_pool": 1000, "control_works": len(control),
              "planted": planted, "real_corpus": corpus,
              "precision_by_eye": {"dev_sample_1": dev_p, "dev_sample_2": dev2_p,
                                   "test_sample_rules_frozen": test_p or "not read yet"}}
    (OUT / "cost_trial_v2.json").write_text(json.dumps(result, indent=2))
    print(json.dumps({"precision_by_eye": result["precision_by_eye"]}, indent=2))


if __name__ == "__main__":
    main()
