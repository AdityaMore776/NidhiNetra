"""Risk Fusion v3 (2 Oct 2026): the score is the chance a work is worth an officer's look.

Fusion v2 (fuse.py) adds each engine's signal times a fixed blueprint weight. Measured, that
leaves most known problems out of the review queue: no single engine can reach HIGH (Guideline
Compliance at its strongest gives 0.18 of the 0.22 needed), so a split, a repeat or a temple
work found with certainty stays MEDIUM unless a second engine happens to fire. On the planted
test 4 of 50 fakes reached the queue (T080); on synthetic countries 4% (data/trial/
synthetic_eval.py).

v3 uses what the team measured by reading flags by eye (reference/reliability.json):

  chance of a finding   p = hit rate x strength
                        hit rate = (worth + 1) / (read + 4): the share of such flags read as worth
                          a look, pulled toward 1 in 4 when few were read; a kind never read counts
                          1 in 4 (proof before launch: it cannot queue a work on its own)
                        strength = risk / ref_risk (1 for fixed-risk findings, e.g. R12, R07)
  an engine             the findings of one engine combine as independent evidence, the same
                        kind of finding counted once (its strongest)
  the work              1 - prod(1 - p_engine): a second engine adds what the first left open
  counted engines       only those with a weight in the registry (shown-not-counted engines stay
                        0: Fund Flow repeats R01, Paperwork and Photo Evidence are pilot-only)
  floor                 a serious rule breach (hard, risk >= 0.6) lifts the score to High, two to
                        Critical, as in v2, as its own part
  bands                 CRITICAL >= 0.80 and two counted engines each >= 0.15 (or a serious
                        breach and another engine): two different checks agree
                        HIGH     >= 0.50: more likely than not worth a look
                        MEDIUM   >= 0.25
                        LOW      otherwise
  parts                 each engine's share of the score in proportion to -ln(1 - p): order-free,
                        and the parts add up exactly to the score
  reasons               the top three parts, the engine's own sentence in English and Hindi, with
                        the measured hit rate behind it

Officer verdicts (T070) feed the same table: Reliability.with_verdicts() adds them to worth/read,
so the score learns which flags are right without anyone retuning a cut-off.
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from functools import cache
from pathlib import Path

from drishti import reference
from drishti.agents.contract import AgentResult, Status

CRITICAL, HIGH, MEDIUM = 0.80, 0.50, 0.25
CORROBORATE = 0.15            # each of two engines at least this for CRITICAL
HARD_RISK = 0.60
MAX_REASONS = 3
VERSION = "risk-v3"


@dataclass(frozen=True)
class Rate:
    hit_rate: float
    ref_risk: float
    basis: str                # "measured", "design" or "prior"
    worth: int = 0
    read: int = 0
    source: str = ""


@dataclass
class Reliability:
    prior: tuple[int, int] = (1, 4)
    codes: dict[str, dict] = field(default_factory=dict)

    @classmethod
    @cache
    def load(cls) -> Reliability:
        path = Path(reference.__file__).resolve().parent / "reliability.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        p = data.get("prior") or {"worth": 1, "read": 4}
        return cls(prior=(int(p["worth"]), int(p["read"])), codes=dict(data["codes"]))

    def with_verdicts(self, verdicts: dict[str, tuple[int, int]]) -> Reliability:
        """Officer verdicts {code: (worth, read)} added to the measured counts (T070)."""
        codes = {k: dict(v) for k, v in self.codes.items()}
        for code, (worth, read) in verdicts.items():
            row = codes.setdefault(code, {"ref_risk": 1.0, "source": "officer verdicts"})
            row.pop("design", None)
            row["worth"] = int(row.get("worth", 0)) + int(worth)
            row["read"] = int(row.get("read", 0)) + int(read)
        return Reliability(prior=self.prior, codes=codes)

    def rate(self, key: str, default_ref: float = 1.0) -> Rate:
        a, n = self.prior
        row = self.codes.get(key)
        if row is None:
            return Rate(a / n, default_ref, "prior", source="not yet read by eye")
        ref = float(row.get("ref_risk", default_ref)) or default_ref
        if "design" in row:
            return Rate(float(row["design"]), ref, "design", source=row.get("source", ""))
        if "worth" in row and "read" in row:
            w, r = int(row["worth"]), int(row["read"])
            return Rate((w + a) / (r + n), ref, "measured", w, r, row.get("source", ""))
        return Rate(a / n, ref, "prior", source=row.get("source", ""))


@dataclass
class Part:
    source: str
    label: str
    weight: float          # the hit rate behind the engine's strongest finding
    contribution: float    # its share of the score


@dataclass
class Fused:
    score: float
    band: str
    limited: bool
    parts: list[Part]
    hard_trigger: str | None = None
    reasons: list[dict] = field(default_factory=list)


def band_of(score: float, engines_over: int = 2, hard: bool = False) -> str:
    """The band of a chance. CRITICAL also needs two counted engines (or a serious breach and
    another engine): one engine alone, however sure, is at most HIGH."""
    if score >= CRITICAL and (engines_over >= 2 or hard):
        return "CRITICAL"
    if score >= HIGH:
        return "HIGH"
    if score >= MEDIUM:
        return "MEDIUM"
    return "LOW"


def chance(engine: str, f, rel: Reliability) -> tuple[float, Rate]:
    """A finding's chance of being worth a look, and the rate it rests on."""
    rate = rel.rate(f"{engine}:{f.code}", default_ref=max(f.risk, 1e-9))
    strength = min(1.0, max(0.0, f.risk / rate.ref_risk)) if rate.ref_risk > 0 else 0.0
    return min(0.99, rate.hit_rate * strength), rate


def engine_chance(r: AgentResult, rel: Reliability) -> tuple[float, dict | None]:
    """The engine's chance: its kinds of finding as independent evidence, each kind once."""
    best: dict[str, tuple[float, object, Rate]] = {}
    for f in r.findings:
        if f.risk <= 0:
            continue
        p, rate = chance(r.agent, f, rel)
        if p > best.get(f.code, (-1.0,))[0]:
            best[f.code] = (p, f, rate)
    if not best:
        return 0.0, None
    miss = 1.0
    for p, _f, _rate in best.values():
        miss *= 1.0 - p
    top_p, top_f, top_rate = max(best.values(), key=lambda x: x[0])
    return 1.0 - miss, {"finding": top_f, "rate": top_rate, "p": top_p}


def fuse(results: list[AgentResult], weights: dict[str, float], labels: dict[str, str],
         hindi, rel: Reliability | None = None) -> Fused:
    rel = rel or Reliability.load()
    per: list[tuple[AgentResult, float, dict]] = []
    for r in results:
        if r.status != Status.ASSESSED or weights.get(r.agent, 0.0) <= 0:
            continue
        p, top = engine_chance(r, rel)
        if p > 0 and top is not None:
            per.append((r, p, top))
    miss = 1.0
    for _r, p, _top in per:
        miss *= 1.0 - p
    raw = 1.0 - miss

    counted = {r.agent for r, _p, _t in per}
    serious = [r for r in results if r.status == Status.ASSESSED and r.agent in weights
               and weights.get(r.agent, 0.0) > 0
               for f in r.findings if f.hard and f.risk >= HARD_RISK]
    floor = CRITICAL if len(serious) >= 2 else HIGH if serious else 0.0
    hard_trigger = serious[0].agent if serious else None

    logs = {r.agent: -math.log(max(1e-12, 1.0 - p)) for r, p, _t in per}
    total_log = sum(logs.values())
    parts: list[Part] = []
    reasons: list[dict] = []
    for r, p, top in per:
        share = raw * logs[r.agent] / total_log if total_log > 0 else 0.0
        f, rate = top["finding"], top["rate"]
        parts.append(Part(r.agent, labels.get(r.agent, r.agent), round(rate.hit_rate, 4), share))
        reasons.append({"source": r.agent, "label": labels.get(r.agent, r.agent),
                        "contribution": share, "code": f.code, "text_en": f.text,
                        "text_hi": (f.evidence or {}).get("message_hi") or hindi(f.code),
                        "chance": round(p, 4), "hit_rate": round(rate.hit_rate, 4),
                        "basis": rate.basis,
                        "read": [rate.worth, rate.read] if rate.basis == "measured" else None})
    score = raw
    if floor > raw:
        parts.append(Part("floor", labels.get("floor", "Serious rule breach"), 0.0, floor - raw))
        score = floor
    score = min(1.0, score)
    strong = sum(1 for _r, p, _t in per if p >= CORROBORATE)
    agree = (bool(serious) and len(counted) >= 2) or len(serious) >= 2
    band = band_of(score, strong, hard=agree)
    limited = any(r.status in (Status.NOT_ASSESSABLE, Status.ERROR) for r in results
                  if weights.get(r.agent, 0.0) > 0)
    parts.sort(key=lambda x: -x.contribution)
    reasons.sort(key=lambda x: -x["contribution"])
    return Fused(score=score, band=band, limited=limited, parts=parts,
                 hard_trigger=hard_trigger, reasons=reasons[:MAX_REASONS])
