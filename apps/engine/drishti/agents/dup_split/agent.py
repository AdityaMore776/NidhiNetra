"""Duplicate & Split-Work engine: is this work repeated, or one job cut into pieces?

v2 (T051). The rules (match.py) run for every work: the batch builds one index of every
comparable work, the API builds one for the work's district. v1 read answers stored by an
offline job for the 2026 export only, so a new recommendation read "compared, nothing found"
without having been compared. Without an index this engine says it could not compare.

What it reports, with a signal that grows with the evidence (v1 gave six fixed values):

  pair after_completed   0.55 .. 0.95  the same work funded again after the first was finished;
                                       grows with the pair score (text, place, time, amount)
  pair while_open        0.35 .. 0.70  recommended again while the first was open
  group same_site_split  0.40 .. 0.55  one job at one site in pieces; grows with the pieces
  group bulk_order       0.10 .. 0.20  a series of identical purchases (15/15 read so by eye)
  under a limit          +0.10 .. 0.20 every piece at 80-100% of Rs 5 or 10 lakh and the
                                       total above it; more the closer the pieces sit to it

The work's signal is the strongest of these. Every member of a group carries its group id so
fusion can count the group once.

  NOT_ASSESSABLE  no comparison index was given, or the work has no readable description,
                  date or amount to compare (not a clean chit)
  ASSESSED        otherwise; a work with no match was compared with every work in its district
"""

from __future__ import annotations

import time

from drishti.agents.contract import AgentResult, Finding, Status
from drishti.agents.dup_split.match import FLAG, DupIndex

AGENT = "dup_split"
VERSION = "dup-split-2.0.0"
QUESTION = "Is this work repeated, or one job cut into pieces?"
PAIR_RISK = {"after_completed": (0.55, 0.95), "while_open": (0.35, 0.70)}
GROUP_RISK = {"same_site_split": 0.40, "bulk_order": 0.10}
# A "same place" group this large is a series, not one job in pieces: the splits read by
# eye had 2-5 pieces, while 16, 23 and 50 identical works sharing a typo ("tenker",
# "publiic", "knowledgew") were purchases filed as many works (queue sample, 30 Sept).
SERIES_SIZE = 6
CONFIDENCE = 0.6       # text similarity finds candidates; only a site visit or file confirms


def _lakh(rs: float) -> str:
    return f"Rs {rs / 1e5:,.2f} lakh"


def _quiet(status: Status, text: str, t0: float) -> AgentResult:
    return AgentResult(agent=AGENT, status=status, verdict=status.value, risk=0.0,
                       confidence=0.0, hard=False, version=VERSION, headline=text,
                       duration_ms=int((time.perf_counter() - t0) * 1000))


def pair_risk(kind: str, score: float) -> float:
    lo, hi = PAIR_RISK[kind]
    return lo + (hi - lo) * max(0.0, min(1.0, (score - FLAG) / (1.0 - FLAG)))


def group_risk(g: dict) -> float:
    if g["kind"] == "same_site_split":
        risk = GROUP_RISK["same_site_split"] + 0.05 * min(3, int(g["size"]) - 2)
    else:
        risk = GROUP_RISK["bulk_order"] + 0.01 * min(10, int(g["size"]))
    if g.get("under_limit") and g.get("limit"):
        mean = float(g["total"]) / int(g["size"])
        closeness = max(0.0, min(1.0, (mean / float(g["limit"]) - 0.8) / 0.2))
        risk += 0.10 + 0.10 * closeness
    return min(1.0, risk)


def _pair_finding(p: dict, amount: float) -> Finding:
    other, gap = p["other"], int(p.get("gap_days") or 0)
    other_amt = float(p.get("other_amount") or 0)
    later = bool(p.get("this_is_later"))
    first = "that work" if later else "this work"      # the one recommended first
    when = f"{gap:,} days {'before' if later else 'after'} this one"
    alike = (f"descriptions {float(p.get('text') or 0):.0%} alike, the same place named, "
             f"amounts {float(p.get('amount_diff') or 0):.0%} apart")
    if p["kind"] == "after_completed":
        code = "FUNDED_AGAIN_AFTER_COMPLETION"
        text = (f"Reads like work {other} ({_lakh(other_amt)}, recommended {when}; {alike}); "
                f"{first} had already been completed when the other was recommended. Check "
                "whether the same work was funded again or this is a genuinely new site.")
    else:
        code = "REPEATED_WHILE_OPEN"
        text = (f"Reads like work {other} ({_lakh(other_amt)}, recommended {when}; {alike}) "
                f"while {first} was still open. Check whether both are the same work.")
    return Finding(code, text, hard=False, risk=pair_risk(p["kind"], float(p["score"])),
                   evidence={"other": other, "kind": p["kind"], "score": p.get("score"),
                             "text_similarity": p.get("text"), "gap_days": gap,
                             "other_amount": other_amt, "this_amount": amount})


def _group_finding(g: dict) -> Finding:
    size, days, total = int(g["size"]), int(g.get("days") or 0), float(g["total"])
    others = ", ".join(g.get("others") or [])
    span = "on the same day" if days == 0 else f"within {days} days"
    piece = total / size
    if g["kind"] == "same_site_split":
        code = "SPLIT_AT_ONE_SITE"
        # the matched place words stay in the evidence, not the sentence: they are rare
        # words of the description, and can be a person's name ("near X's house")
        text = (f"One of {size} alike works naming the same place, recommended {span}: "
                f"{_lakh(total)} in all, about {_lakh(piece)} each. Check whether one job "
                "was cut into pieces.")
    else:
        code = "BULK_ORDER"
        text = (f"One of {size} alike works recommended {span}: {_lakh(total)} in all, about "
                f"{_lakh(piece)} each; usually one purchase filed as many works.")
    if g.get("under_limit") and g.get("limit"):
        text += (f" Every piece sits just under {_lakh(float(g['limit']))} while the total "
                 "passes it.")
    if others:
        text += f" Others: {others}."
    return Finding(code, text, hard=False, risk=group_risk(g),
                   evidence={k: g.get(k) for k in ("group_id", "kind", "size", "total",
                                                   "under_limit", "limit", "shared_place",
                                                   "days", "others", "cv")})


def assess(work: dict, index: DupIndex | None) -> AgentResult:
    t0 = time.perf_counter()
    if index is None or not work.get("district_lgd"):
        return _quiet(Status.NOT_ASSESSABLE, "Cannot be assessed: the works of its district "
                      "were not available to compare with. This is not a clean chit.", t0)
    found = index.check(work)
    if found is None:
        return _quiet(Status.NOT_ASSESSABLE, "Cannot be assessed: the record has no readable "
                      "description, date or amount to compare. This is not a clean chit.", t0)
    amount = float(work.get("amount") or 0)
    pairs = found["pairs"]
    group = found["group"]
    if group and group["kind"] == "same_site_split" and int(group["size"]) >= SERIES_SIZE:
        group = {**group, "kind": "bulk_order"}

    findings = [_pair_finding(p, amount) for p in pairs]
    if group:
        findings.append(_group_finding(group))
    findings.sort(key=lambda f: -f.risk)
    if not findings:
        n = found.get("compared", 0)
        return AgentResult(
            agent=AGENT, status=Status.ASSESSED, verdict="NO_REPEAT_FOUND", risk=0.0,
            confidence=CONFIDENCE, hard=False, version=VERSION,
            headline=(f"Compared with the {n:,} other works of its district: no repeat or "
                      "split found." if n else
                      "No other work of its district is on record to compare with."),
            evidence={"compared": n},
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
