r"""Trial (2 Oct 2026): every engine on synthetic countries it has never seen, with planted fakes.

Each seed builds a fresh country (apps/engine/drishti/evaluation/synthetic.py: made-up states,
districts, villages, offices and MPs; about 19,000 works shaped like the real export) and plants
labelled problems: price mark-ups (3x, 5x, 10x, and 10x on "one light"), reworded repeats after
completion or while open, same-site splits and splits into numbered stretches just under
Rs 5 lakh, repairs soon after a work was built, prohibited works, outside-area sums, big vague
sums, constructions finished in days, impossible dates, an office that prices works at the limit
and one that closes works in days. Look-alikes the engines must leave alone are planted too
(temples as landmarks, schools named "Shishu Mandir", batches for different villages, opposite
sides of one road, bulk entry when the portal opened, big projects that state their size).

Statistics and the word-price model are rebuilt from each country (the method of build_stats.py
and build_price_model.py), so nothing is tuned to one draw. The labels are known, so this is the
only RECALL measurement there is; precision on real works comes from reading them by eye
(dashboard_trial.py). Background works are ordinary by construction: a queued background work is
counted as a false alarm, an upper bound on noise.

Writes results/synthetic_eval_<tag>.json: per seed and pooled, recall by planted kind (meant engine
/ MEDIUM+ / review queue / top 5%), look-alike false alarms, queue size and precision.

Run: apps\engine\.venv\Scripts\python.exe data\trial\synthetic_eval.py --tag v3 --seeds 1 2 3
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
sys.path.insert(0, str(ROOT / "data" / "trial"))

from dashboard_trial import fit_price_model  # noqa: E402

from drishti.evaluation.harness import run, summarise  # noqa: E402
from drishti.evaluation.synthetic import Generator  # noqa: E402

OUT = ROOT / "data" / "trial" / "results"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tag", default="current")
    ap.add_argument("--seeds", type=int, nargs="+", default=[11, 12, 13])
    ap.add_argument("--no-model", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    per_seed, pooled = {}, []
    for seed in args.seeds:
        corpus = Generator(seed=seed).build()
        model = None if args.no_model else fit_price_model(corpus.works)
        rows, rep = run(corpus, [{"name": "price_model", "data": model}] if model else None)
        per_seed[str(seed)] = {k: rep[k] for k in rep if k != "kinds"} | {
            "recall_by_kind": {k: v for k, v in rep["kinds"].items() if v["positive"]}}
        pooled.extend(rows)
        print(f"seed {seed}: {rep['works']:,} works, queue {rep['queue']} "
              f"(precision {rep['queue_precision']}), positives queued "
              f"{rep['positives_queued']}, caught by meant engine "
              f"{rep['positives_caught_by_meant_engine']}", flush=True)
    total = summarise(pooled, time.time() - t0)
    by_kind = defaultdict(dict)
    for k, v in total["kinds"].items():
        by_kind["planted" if v["positive"] else "look-alike or background"][k] = v
    res = {"tag": args.tag, "seeds": args.seeds, "pooled": {k: v for k, v in total.items()
                                                            if k != "kinds"},
           "pooled_by_kind": by_kind, "per_seed": per_seed,
           "seconds": round(time.time() - t0)}
    (OUT / f"synthetic_eval_{args.tag}.json").write_text(json.dumps(res, indent=2),
                                                        encoding="utf-8")
    print(json.dumps(res["pooled"], indent=2))
    for group, kinds in by_kind.items():
        print(group)
        for k, v in sorted(kinds.items()):
            print(f"  {k:32s} n={v['n']:5d} meant={v['meant_code_fired']:.2f} "
                  f"medium+={v['medium_or_above']:.2f} queued={v['queued']:.2f} "
                  f"top5={v['top5pct']:.2f}")


if __name__ == "__main__":
    main()
