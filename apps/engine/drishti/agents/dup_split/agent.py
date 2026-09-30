"""Duplicate & Split-Work engine: is this work repeated, or one job cut into pieces?

The comparison itself (meaning vectors of every description, compared inside each district;
data/build_dup_split.py) runs offline. Each work it links to another is stored in
work_signals["dup_split"] as

  pairs  up to 5 other works it repeats: {other, kind, score, gap_days, other_amount,
         this_is_later}; kind = after_completed (the first was finished before this one
         was recommended) or while_open (recommended again while the first was open)
  group  the chain of alike works it belongs to: {group_id, kind, size, total,
         under_limit, shared_place, days, others}; kind = same_site_split (the pieces
         name one place) or bulk_order (generic text: one purchase filed as many works)

This engine only reads them and turns them into a signal:

  pair after_completed   0.85   the strongest case: the same work funded again
  pair while_open        0.60
  group same_site_split  0.60   one job at one site in pieces
  group bulk_order       0.35   usually a legitimate bulk order, worth a look
  +0.20 when every piece is Rs 4-5 lakh and the total passes Rs 5 lakh (amounts pile up
  just under that limit nationally)

The work's signal is the strongest of these. Every member of a group carries its group id
so fusion can count the group once.

  NOT_ASSESSABLE  the comparison has not been run, or the work has no readable
                  description, date or amount to compare (not a clean chit)
  ASSESSED        otherwise; a work with no stored links was compared and matched nothing
"""

from __future__ import annotations

import time

from drishti.agents.contract import AgentResult, Finding, Status
from drishti.agents.statistical.scope import undescribed

AGENT = "dup_split"
VERSION = "dup-split-1.0.0"
QUESTION = "Is this work repeated, or one job cut into pieces?"
PAIR_RISK = {"after_completed": 0.85, "while_open": 0.60}
GROUP_RISK = {"same_site_split": 0.60, "bulk_order": 0.35}
UNDER_LIMIT_BONUS = 0.20
CONFIDENCE = 0.6       # text similarity finds candidates; only a site visit or file confirms


def _lakh(rs: float) -> str:
    return f"Rs {rs / 1e5:,.2f} lakh"


def _quiet(status: Status, text: str, t0: float) -> AgentResult:
    return AgentResult(agent=AGENT, status=status, verdict=status.value, risk=0.0,
                       confidence=0.0, hard=False, version=VERSION, headline=text,
                       duration_ms=int((time.perf_counter() - t0) * 1000))


def _pair_finding(p: dict, amount: float) -> Finding:
    other, gap = p["other"], int(p.get("gap_days") or 0)
    other_amt = float(p.get("other_amount") or 0)
    later = bool(p.get("this_is_later"))
    first = "that work" if later else "this work"      # the one recommended first
    when = f"{gap:,} days {'before' if later else 'after'} this one"
    if p["kind"] == "after_completed":
        code = "FUNDED_AGAIN_AFTER_COMPLETION"
        text = (f"Reads like work {other} ({_lakh(other_amt)}, recommended {when}); "
                f"{first} had already been completed when the other was recommended. Check "
                "whether the same work was funded again or this is a genuinely new site.")
    else:
        code = "REPEATED_WHILE_OPEN"
        text = (f"Reads like work {other} ({_lakh(other_amt)}, recommended {when}) while "
                f"{first} was still open. Check whether both are the same work.")
    return Finding(code, text, hard=False, risk=PAIR_RISK[p["kind"]],
                   evidence={"other": other, "kind": p["kind"], "score": p.get("score"),
                             "gap_days": gap, "other_amount": other_amt,
                             "this_amount": amount})


def _group_finding(g: dict) -> Finding:
    risk = GROUP_RISK[g["kind"]] + (UNDER_LIMIT_BONUS if g.get("under_limit") else 0.0)
    size, days, total = int(g["size"]), int(g.get("days") or 0), float(g["total"])
    others = ", ".join(g.get("others") or [])
    span = "on the same day" if days == 0 else f"within {days} days"
    if g["kind"] == "same_site_split":
        code = "SPLIT_AT_ONE_SITE"
        text = (f"One of {size} alike works for the same place "
                f"(\"{g.get('shared_place', '')}\") recommended {span}, "
                f"{_lakh(total)} in all. Check whether one job was cut into pieces.")
    else:
        code = "BULK_ORDER"
        text = (f"One of {size} alike works recommended {span}, "
                f"{_lakh(total)} in all; usually one purchase filed as many works.")
    if g.get("under_limit"):
        text += (" Every piece is between Rs 4 and 5 lakh while the total passes "
                 "Rs 5 lakh.")
    if others:
        text += f" Others: {others}."
    return Finding(code, text, hard=False, risk=min(1.0, risk),
                   evidence={k: g.get(k) for k in ("group_id", "kind", "size", "total",
                                                   "under_limit", "shared_place", "days",
                                                   "others")})


def assess(work: dict, built: bool) -> AgentResult:
    t0 = time.perf_counter()
    if not built:
        return _quiet(Status.NOT_ASSESSABLE, "Cannot be assessed: the duplicate comparison "
                      "has not been run yet. This is not a clean chit.", t0)
    amount = float(work.get("amount") or 0)
    if (undescribed(work.get("description")) or work.get("recommended_date") is None
            or amount <= 0):
        return _quiet(Status.NOT_ASSESSABLE, "Cannot be assessed: the record has no readable "
                      "description, date or amount to compare. This is not a clean chit.", t0)
    s = (work.get("signals") or {}).get("dup_split") or {}
    pairs = [p for p in s.get("pairs") or [] if p.get("kind") in PAIR_RISK]
    group = s.get("group") if (s.get("group") or {}).get("kind") in GROUP_RISK else None

    findings = [_pair_finding(p, amount) for p in pairs]
    if group:
        findings.append(_group_finding(group))
    findings.sort(key=lambda f: -f.risk)
    if not findings:
        return AgentResult(
            agent=AGENT, status=Status.ASSESSED, verdict="NO_REPEAT_FOUND", risk=0.0,
            confidence=CONFIDENCE, hard=False, version=VERSION,
            headline="Compared with every work in its district: no repeat or split found.",
            limitations=["Compares descriptions only; two records of one site worded very "
                         "differently are not matched."],
            duration_ms=int((time.perf_counter() - t0) * 1000))
    top = findings[0]
    return AgentResult(
        agent=AGENT, status=Status.ASSESSED, verdict=top.code, risk=top.risk,
        confidence=CONFIDENCE, hard=False, headline=top.text, version=VERSION,
        findings=findings,
        limitations=["Matched on the wording of descriptions; the district is the finest "
                     "location in the record, so only a site visit or the files can confirm "
                     "two works are one."],
        evidence={"group_id": group["group_id"] if group else None,
                  "pairs": len(pairs)},
        duration_ms=int((time.perf_counter() - t0) * 1000))
