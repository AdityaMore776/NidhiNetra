"""Run the whole pipeline over a labelled corpus and say what each engine caught.

For every planted kind (positive): how many were caught by the engine meant for them (one of
the label's finding codes, with a risk), how many reached MEDIUM or above, the review queue
(HIGH + CRITICAL) and the top 5% of the score. For every look-alike (HN_*) and the background:
how often the meant code fired anyway, and how often the work was queued. The queue's
precision is the share of queued works that are planted problems.

Background works are ordinary by construction, so a background work in the queue is a false
alarm here. On real data some of those would be real problems nobody planted: the synthetic
false-alarm rate is an upper bound of the engines' noise, not a measurement of real precision.
"""

from __future__ import annotations

import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field

from drishti.batch import indexes
from drishti.evaluation.stats import build_store
from drishti.evaluation.synthetic import Corpus
from drishti.pipeline.orchestrator import Context, assess_work

REVIEW = ("CRITICAL", "HIGH")
NOTICE = ("CRITICAL", "HIGH", "MEDIUM")


@dataclass
class Row:
    work_id: str
    kind: str
    positive: bool
    meant_caught: bool
    band: str
    score: float
    fired: dict[str, list[str]] = field(default_factory=dict)   # engine -> codes with risk


def run(corpus: Corpus, models: list[dict] | None = None) -> tuple[list[Row], dict]:
    t0 = time.perf_counter()
    stats = build_store(corpus.works, models)
    ctx = Context(stats=stats, as_of=corpus.as_of, data=indexes(corpus.works))
    rows: list[Row] = []
    for w in corpus.works:
        a = assess_work(w, ctx)
        lab = corpus.label(w["work_id"])
        fired = {r.agent: [f.code for f in r.findings if f.risk > 0]
                 for r in a.agents if r.assessed and any(f.risk > 0 for f in r.findings)}
        caught = bool(lab.meant) and any(c in lab.codes for c in fired.get(lab.meant, []))
        rows.append(Row(w["work_id"], lab.kind, lab.positive, caught, a.fused.band,
                        a.fused.score, fired))
    return rows, summarise(rows, time.perf_counter() - t0)


def summarise(rows: list[Row], seconds: float = 0.0) -> dict:
    """UNSCORED_* works (the generator cannot say whether they are problems) are reported by
    kind but left out of the queue's precision and the background's false alarms."""
    by_kind: dict[str, list[Row]] = defaultdict(list)
    for r in rows:
        by_kind[r.kind].append(r)
    scored = [r for r in rows if not r.kind.startswith("UNSCORED")]
    ranked = sorted(rows, key=lambda r: -r.score)
    top = {r.work_id for r in ranked[:max(1, len(rows) // 20)]}
    kinds = {}
    for kind, rs in sorted(by_kind.items()):
        n = len(rs)
        kinds[kind] = {
            "n": n, "positive": rs[0].positive,
            "meant_code_fired": round(sum(r.meant_caught for r in rs) / n, 3),
            "medium_or_above": round(sum(r.band in NOTICE for r in rs) / n, 3),
            "queued": round(sum(r.band in REVIEW for r in rs) / n, 3),
            "top5pct": round(sum(r.work_id in top for r in rs) / n, 3)}
    positives = [r for r in rows if r.positive]
    queue = [r for r in scored if r.band in REVIEW]
    background = by_kind.get("BACKGROUND", [])
    engines = Counter(e for r in background for e in r.fired)
    return {
        "works": len(rows), "seconds": round(seconds, 1),
        "bands": dict(Counter(r.band for r in rows)),
        "queue": len(queue), "queue_share": round(len(queue) / max(1, len(rows)), 4),
        "unscored_queued": sum(r.band in REVIEW for r in rows if r.kind.startswith("UNSCORED")),
        "queue_precision": round(sum(r.positive for r in queue) / max(1, len(queue)), 3),
        "positives": len(positives),
        "positives_caught_by_meant_engine": round(
            sum(r.meant_caught for r in positives) / max(1, len(positives)), 3),
        "positives_queued": round(sum(r.band in REVIEW for r in positives)
                                  / max(1, len(positives)), 3),
        "positives_medium_or_above": round(sum(r.band in NOTICE for r in positives)
                                           / max(1, len(positives)), 3),
        "positives_in_top5pct": round(sum(r.work_id in top for r in positives)
                                      / max(1, len(positives)), 3),
        "background_queued": round(sum(r.band in REVIEW for r in background)
                                   / max(1, len(background)), 4),
        "background_engine_fire_rate": {e: round(c / max(1, len(background)), 4)
                                        for e, c in sorted(engines.items())},
        "kinds": kinds}
