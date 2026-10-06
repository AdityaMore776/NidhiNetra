"""What DRISHTI does to one work, step by step: the trace behind the Visualization Engine (T092).

A judge sees six steps on the page (apps/web/src/app/explain): the work goes in, private details
are hidden, the description is read, the checks look at it at once, the score adds up, the
officer gets a result. This module runs the work through the SAME pipeline as the batch
(orchestrator.assess_work) and lays out what each step's picture needs. It computes no score of
its own: the score's arithmetic is replayed from the fusion's own functions and checked against
the pipeline's answer (tests/test_explain.py).

Everything returned is shown to the public: text goes through the site's masker, no MP is named,
and a work's other works in the district appear only by id, amount, date and masked wording.
"""

from __future__ import annotations

import re
from datetime import date

from drishti import records, reference
from drishti.agents import registry
from drishti.agents.compliance import agent as compliance
from drishti.agents.compliance.eligibility import v2 as not_allowed
from drishti.agents.contract import Status
from drishti.agents.dup_split.match import place_agreement, place_words, text_sim
from drishti.agents.dup_split.repeat import PIN_METRES, PLACE_MIN, TEXT_MIN, Rec
from drishti.agents.statistical import scope as reader
from drishti.agents.statistical.text import LENGTH, stated_length
from drishti.fusion import calibrated
from drishti.fusion import fuse as fusion
from drishti.pipeline.orchestrator import Context, assess_work
from drishti.presanction import judge as presanction_judge
from drishti.validation.pii import mask

VERSION = "explain-1.0.0"
NEIGHBOURS = 6
PRIVATE = re.compile(r"\[(name|phone|number)\]")
# what the page colours each kind of word as, in this order of precedence
KINDS = ("private", "not_allowed", "quantity", "goods", "build", "place")
SCOPE_WORDS = {reader.GOODS: "goods: a purchase", reader.WORKS: "a construction or repair",
               reader.MAST: "high-mast lights"}


def _day(x) -> str | None:
    return x.isoformat() if isinstance(x, date) else None


def _counts(text: str, typ: str | None) -> list[tuple[int, int]]:
    """Where the cost reader finds a count of units ("50 nos street lights", "one high mast")."""
    spans = [m.span() for m in reader._COUNT.finditer(text)
             if not reader._NOT_A_COUNT_BEFORE.search(text[max(0, m.start() - 12):m.start()])]
    unit = reader.SINGLE_UNITS.get(typ or "")
    if unit:
        spans += [m.span() for m in re.finditer(reader._ONE + unit + r"\b", text, re.I)]
    return spans


def _segments(text: str, keyword: str | None, typ: str | None = None) -> list[dict]:
    """The description cut into runs, each with the kind of word it is (or none)."""
    kind = [None] * len(text)

    def mark(spans, k):
        for a, b in spans:
            for i in range(a, b):
                if kind[i] is None or KINDS.index(k) < KINDS.index(kind[i]):
                    kind[i] = k

    places = set(place_words(text).split())
    mark([m.span() for m in PRIVATE.finditer(text)], "private")
    if keyword:
        mark([m.span() for m in re.finditer(re.escape(keyword), text, re.I)], "not_allowed")
    mark([m.span() for m in LENGTH.finditer(text)], "quantity")
    mark(_counts(text, typ), "quantity")
    mark([m.span() for m in re.finditer(r"\b\d[\d,.]*\s*(?:km|kms|nos?|nag|units?|sets?|pcs|"
                                        r"sq\.?\s*f(?:ee)?t|sqm)\b", text, re.I)], "quantity")
    mark([m.span() for m in reader._GOODS_VERB.finditer(text)], "goods")
    mark([m.span() for m in reader._GOODS_NOUN.finditer(text)], "goods")
    mark([m.span() for m in reader._BUILD.finditer(text)], "build")
    mark([m.span() for m in re.finditer(r"[^\W\d_]+", text)
          if m.group(0).lower() in places], "place")
    out: list[dict] = []
    for ch, k in zip(text, kind, strict=True):
        if out and out[-1]["k"] == k:
            out[-1]["t"] += ch
        else:
            out.append({"t": ch, "k": k})
    return out


def _reading(w: dict, text: str) -> dict:
    typ = w.get("work_type_code")
    r = reader.read(typ, text)
    na = not_allowed(text) if text else None
    length = stated_length(text)
    rec = w.get("recommended_date")
    return {
        "segments": _segments(text, na.keyword if na else None, typ),
        "facts": {
            "what": SCOPE_WORDS.get(r.scope, r.scope),
            # no object at all, or R12's reading: a few words, no number, no place
            "says_nothing": r.undescribed or bool(
                text and len(text.split()) <= compliance.SCOPE_MAX_WORDS
                and not re.search(r"\d", text) and not compliance.WORD_NUMBER.search(text)
                and not place_words(text)),
            "place_named": bool(place_words(text)),
            "count": r.count,
            "single_unit": reader.single_unit(typ, text),
            "length_m": None if length != length else round(length, 1),     # NaN: none stated
            "several_sites": r.many_sites,
            "bundle": r.bundle,
            "not_allowed": ({"word": na.keyword, "item": na.annexure_item, "rule": na.text}
                            if na else None),
            "era": (None if not isinstance(rec, date) else
                    "digital era (2023 on)" if rec.year >= 2023 else "before eSAKSHI went digital"),
        },
    }


def _rules(findings, only: tuple[str, ...] | None = None) -> list[dict]:
    fired = {f.evidence.get("rule"): f for f in findings if f.evidence.get("rule")}
    out = []
    for rid, r in compliance.rules().items():
        if not r.get("evaluable", True) or (only and rid not in only):
            continue
        f = fired.get(rid)
        out.append({"id": rid, "title": r["title"], "ref": r.get("guideline_ref"),
                    "raised": f is not None,
                    "severity": f.evidence.get("severity") if f else None})
    return out


def _neighbours(w: dict, ctx: Context, result) -> dict:
    index = (ctx.data or {}).get("dup_split")
    me = Rec.of(w)
    if index is None or me is None:
        return {"compared": 0, "nearest": []}
    flagged = {(f.evidence or {}).get("other") for f in result.findings} - {None}
    others = [x for x in index.by_district.get(me.district, []) if x.work_id != me.work_id]
    scored = sorted(((text_sim(me.description, x.description), x) for x in others),
                    key=lambda t: -t[0])[:NEIGHBOURS]
    # T100: "flag" is the look-alike line (a note, never counted); a repeat is asked only by map pin
    return {"compared": len(others), "text_min": TEXT_MIN, "place_min": PLACE_MIN,
            "flag": TEXT_MIN, "pin_metres": PIN_METRES,
            "nearest": [{"work_id": x.work_id, "description": mask(x.description)[:140],
                         "amount": x.amount, "date": _day(x.rec or x.done),
                         "likeness": round(sim, 3),
                         "place": round(place_agreement(me.raw_place, x.raw_place), 1),
                         "flagged": x.work_id in flagged} for sim, x in scored]}


def _picture(r, w: dict, ctx: Context) -> dict | None:
    ev = r.evidence or {}
    if r.agent == "compliance":
        return {"rules": _rules(r.findings)}
    if r.agent == "time_rules":
        window = ev.get("window") or {}
        return {"rules": _rules(r.findings, ("R01", "R06", "R13", "R14")),
                "recommended": _day(w.get("recommended_date")),
                "sanctioned": _day(w.get("sanction_date")),
                "completed": _day(w.get("completed_date")), "as_of": ctx.as_of.isoformat(),
                "sanction_clock_days": int(compliance._clause("SANCTION_PERIOD",
                                                              "sanction_period_days")),
                "window_start": window.get("start"), "early_line": window.get("early"),
                "late_line": window.get("late")}
    if r.agent == "site_progress":
        return {"visits": ev.get("visits") or []}
    if r.agent == "cost_estimate":
        out = {k: ev.get(k) for k in ("sites", "grand_total", "mp_amount", "mp_gap")
               if ev.get(k) is not None}
        whole = ev.get("whole") or {}
        if whole:
            out["whole"] = {k: whole.get(k) for k in ("verdict", "fair_total", "gap",
                                                       "gap_share", "coverage")}
        return out
    if r.agent == "dup_split":
        return _neighbours(w, ctx, r)
    if r.agent == "delay":
        return {"recommended": _day(w.get("recommended_date")),
                "sanctioned": _day(w.get("sanction_date")),
                "completed": _day(w.get("completed_date")), "as_of": ctx.as_of.isoformat(),
                "sanction_clock_days": int(compliance._clause("SANCTION_PERIOD",
                                                              "sanction_period_days")),
                "completion_clock_days": int(compliance._clause("COMPLETION_PERIOD",
                                                                "completion_period_days"))}
    if r.agent == "office_patterns":
        # the office's two habits against the whole scheme: {office, of, share, national_share}
        return {k: ev[k] for k in ("priced_just_under_a_limit", "built_within_a_week_of_sanction")
                if isinstance(ev.get(k), dict)}
    return None


# the evidence a page may show in short beside a finding (T134): numbers, dates, work IDs and
# item names the finding's own sentence already gives; never free text from the record, and never
# the Hindi sentence
FACT_KEYS = frozenset({
    "gap", "gap_share", "fair_total", "coverage", "grand_total", "above_fair_rate",
    "priced_lines", "top", "site", "material", "quantity", "needed", "unit", "why", "ratio",
    "lines", "price_per_unit", "where", "p98", "median", "n", "mp_amount", "mp_gap", "other",
    "metres", "other_amount", "other_completed", "months_after_completion", "nature", "size",
    "total", "limit", "others", "days", "segments", "value", "early", "late", "videos", "stalled",
    "visit", "visits", "claims", "reused_from", "same_place_as", "mock_location", "kind",
    # T135
    "unexplained", "overlap", "declared", "same_ground", "share", "amount", "items", "filmed",
    "form_size", "scope_size",
    # T141: the labour rows asked about (trade, day rate, its trade's rate, person-days)
    "rows", "extra"})


def _plain(v, depth: int = 0) -> bool:
    if v is None or isinstance(v, bool | int | float):
        return True
    if isinstance(v, str):
        return len(v) <= 160
    if depth < 2 and isinstance(v, list):
        return len(v) <= 20 and all(_plain(x, depth + 1) for x in v)
    if depth < 2 and isinstance(v, dict):
        return all(isinstance(k, str) and _plain(x, depth + 1) for k, x in v.items())
    return False


def _finding(f) -> dict:
    ev = f.evidence or {}
    return {"code": f.code, "text": f.text, "risk": round(f.risk, 4), "hard": f.hard,
            "rule": ev.get("rule"), "severity": ev.get("severity"),
            "facts": {k: v for k, v in ev.items() if k in FACT_KEYS and _plain(v)}}


def _scoring(a, ctx: Context) -> dict:
    """The fusion's arithmetic, one finding and one engine at a time (v3, fusion/calibrated.py)."""
    rel = (ctx.reliability if isinstance(ctx.reliability, calibrated.Reliability)
           else calibrated.Reliability.load())
    weights = fusion.weights()
    engines, chain, miss = [], [], 1.0
    for r in a.agents:
        if r.status != Status.ASSESSED or weights.get(r.agent, 0.0) <= 0:
            continue
        kinds = []
        for f in r.findings:
            if f.risk <= 0:
                continue
            p, rate = calibrated.chance(r.agent, f, rel)
            kinds.append({"code": f.code, "risk": round(f.risk, 4),
                          "ref_risk": round(rate.ref_risk, 4),
                          "strength": round(min(1.0, f.risk / rate.ref_risk), 4)
                          if rate.ref_risk > 0 else 0.0,
                          "hit_rate": round(rate.hit_rate, 4), "basis": rate.basis,
                          "read": [rate.worth, rate.read] if rate.basis == "measured" else None,
                          "chance": round(p, 4)})
        p, _top = calibrated.engine_chance(r, rel)
        if p <= 0:
            continue
        engines.append({"engine": r.agent, "name": fusion.LABELS.get(r.agent, r.agent),
                        "chance": round(p, 4), "findings": kinds})
    for e in sorted(engines, key=lambda e: -e["chance"]):
        miss *= 1.0 - e["chance"]
        chain.append({"engine": e["engine"], "chance": e["chance"], "score": round(1 - miss, 4)})
    return {"method": fusion.version(), "engines": engines, "chain": chain,
            "raw": round(1 - miss, 4), "floor": a.fused.hard_trigger is not None,
            "score": round(a.fused.score, 4), "band": a.fused.band,
            "lines": {"MEDIUM": calibrated.MEDIUM, "HIGH": calibrated.HIGH,
                      "CRITICAL": calibrated.CRITICAL}}


def explain(work: dict, ctx: Context) -> dict:
    """The trace of one work through the pipeline (see the module note)."""
    w = records.work(work)
    a = assess_work(w, ctx)
    text = mask(w.get("description") or "") or ""
    hidden = {k: text.count(f"[{k}]") - (w.get("description") or "").count(f"[{k}]")
              for k in ("name", "phone", "number")}
    types = reference.work_types()
    specs = registry.by_id()
    weights = fusion.weights()
    checks = []
    for r in a.agents:
        spec = specs.get(r.agent)
        checks.append({"id": r.agent, "name": spec.name if spec else r.agent,
                       "question": spec.question if spec else "",
                       "counted": weights.get(r.agent, 0.0) > 0,
                       "status": r.status.value, "verdict": r.verdict, "risk": round(r.risk, 4),
                       "headline": mask(r.headline), "limitations": list(r.limitations),
                       "findings": [_finding(f) for f in r.findings],
                       "picture": _picture(r, w, ctx) if r.status == Status.ASSESSED else None})
    typ = w.get("work_type_code")
    ps = presanction_judge(a) if w.get("status") == "RECOMMENDED" else None
    return {
        "version": VERSION,
        "as_of": ctx.as_of.isoformat(),
        "input": {"description": text, "work_type": typ,
                  "work_type_name": (types.get(typ) or {}).get("name") if typ else None,
                  "amount": w.get("amount"), "district": w.get("district_name"),
                  "state": w.get("state_name"), "office": mask(w.get("agency_name")),
                  "status": w.get("status"), "recommended": _day(w.get("recommended_date")),
                  "sanctioned": _day(w.get("sanction_date")),
                  "completed": _day(w.get("completed_date")),
                  "outside_constituency": w.get("is_outside_constituency")},
        "privacy": {"hidden": hidden},
        "reading": _reading(w, text),
        "checks": checks,
        "scoring": _scoring(a, ctx),
        "result": {"band": a.fused.band, "score": round(a.fused.score, 4),
                   "in_queue": a.fused.band in ("HIGH", "CRITICAL"), "limited": a.fused.limited,
                   "colour": ps.colour if ps else None, "advice": ps.advice if ps else None,
                   "reasons": [{"engine": x["label"], "text": mask(x["text_en"]),
                                "text_hi": x.get("text_hi"), "chance": x.get("chance"),
                                "basis": x.get("basis"), "read": x.get("read")}
                               for x in a.fused.reasons]},
    }
