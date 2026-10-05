"""Duplicate Work engine (stored id `dup_split`): is this work already sanctioned at this site?

v3 (T100, 3 Oct 2026, the owner's "simple and certain" pivot). The engine asks only what it can be
sure of, and that comes from the implementing agency's cost estimate form (work["cost_form"]):

  SANCTIONED_WORK_AT_THIS_SITE   risk 0.7  the form's map pin is within 50 m of the map pin of a
                                           sanctioned work of the same kind of asset (a linear
                                           work by both ends), and the agency did not name that
                                           work as the one this work continues
  REBUILT_SOON_AFTER_COMPLETION  risk 0.6  the agency declares this work rebuilds sanctioned work
                                           X, and X was completed less than 3 years before this
                                           work was recommended
  SPLIT_JUST_UNDER_LIMIT         risk 0.6  one job cut into pieces to stay under a sanction limit,
                                           in its strictest form (repeat.py: 2-5 alike pieces at
                                           one place or numbered parts, one MP, within 30 days,
                                           EVERY piece 96-100% of the Rs 5 or 10 lakh limit):
                                           14 dashboard groups read 12 yes, 2 grey, 0 not

Notes (risk 0, shown, never counted):
  CONTINUES_SANCTIONED_WORK   the earlier work the agency names (continuation, extension,
                              upgrade, reconstruction), and whether it is on record
  LOOKS_LIKE_SANCTIONED_WORK  an earlier sanctioned work of the same type naming the same place in
                              the same words; from words alone right about 2 times in 3 (the
                              strictest text rule, 13 of 16 on the team's 289 pairs read by eye),
                              so the form asks the agency, and its answer is shown

Removed in v3 (each read right about half the time, reference/reliability.json): splits whose
pieces sit anywhere in 80-100% of a limit, bulk orders, and repeats judged on words alone.
Measurements: data/trial/simple_certain_trial.py; plan: docs/plans/T099-T100-simple-and-certain.md.

  NOT_ASSESSABLE  no index of its district was given, or the record has no date or readable
                  description (and no map pin) to compare (not a clean chit)
  ASSESSED        otherwise
"""

from __future__ import annotations

import time
from datetime import timedelta

from drishti.agents.contract import AgentResult, Finding, Status
from drishti.agents.dup_split.repeat import PIN_METRES, RepeatIndex, pin_problems, same_ground

AGENT = "dup_split"
VERSION = "dup-split-3.0.0"
QUESTION = "Is this work already sanctioned here, or one job cut to stay under a limit?"
SITE_RISK = 0.7
REBUILT_RISK = 0.6
SPLIT_RISK = 0.6
REBUILT_WITHIN = timedelta(days=3 * 365)
NATURE_WORDS = {"continuation": "continues", "extension": "extends", "upgrade": "upgrades",
                "reconstruction": "rebuilds"}
ANSWER_WORDS = {"different": "a different work", "continues": "the work this one continues",
                "same": "the same work"}


def _lakh(rs: float) -> str:
    return f"Rs {rs / 1e5:,.2f} lakh"


def _rupees(rs: float) -> str:
    """Rs 4,99,942: the exact amount in Indian digit groups (pieces just under a limit differ
    in the last few hundred rupees)."""
    n = str(int(round(rs)))
    head, tail = n[:-3], n[-3:]
    while len(head) > 2:
        tail = f"{head[-2:]},{tail}"
        head = head[:-2]
    return f"Rs {head},{tail}" if head else f"Rs {tail}"


def _state(x) -> str:
    """What the record says about an earlier work, in words."""
    if x.done:
        return f"completed on {x.done.isoformat()}"
    if x.sanction:
        return f"sanctioned on {x.sanction.isoformat()}, not yet completed"
    return "sanctioned, not yet completed"


def _quiet(status: Status, text: str, t0: float) -> AgentResult:
    return AgentResult(agent=AGENT, status=status, verdict=status.value, risk=0.0,
                       confidence=0.0, hard=False, version=VERSION, headline=text,
                       duration_ms=int((time.perf_counter() - t0) * 1000))


def _said(answers: dict, wid: str) -> str:
    a = answers.get(wid) or {}
    answer = a.get("answer")
    word = ANSWER_WORDS.get(answer) if isinstance(answer, str) else None
    if not word:
        return ""
    why = a.get("difference")
    return (f" The agency says it is {word}"
            f"{f': {why!r}' if isinstance(why, str) and why.strip() else ''}.")


def _rebuilt(me, x, lead: str, nature: str | None, ground: bool) -> Finding:
    """REBUILT_SOON_AFTER_COMPLETION for earlier work x (completed less than 3 years before)."""
    months = (me.first - x.done).days // 30
    same = (" It is called a continuation or an upgrade, but it covers that work's own ground "
            "with the same size: the same asset built again." if ground else "")
    return Finding(
        "REBUILT_SOON_AFTER_COMPLETION",
        f"{lead} {x.work_id} ({_lakh(x.amount)}), which was completed on "
        f"{x.done.isoformat()}, {months} months before this one was recommended.{same} A new "
        "asset should not need rebuilding this soon: please check the first work's completion "
        "and quality.",
        hard=False, risk=REBUILT_RISK,
        evidence={"other": x.work_id, "nature": nature, "months_after_completion": months,
                  "other_amount": x.amount, "same_ground": ground, "kind": "declared"})


def assess(work: dict, index: RepeatIndex | None) -> AgentResult:
    t0 = time.perf_counter()
    if index is None or not work.get("district_lgd"):
        return _quiet(Status.NOT_ASSESSABLE, "Cannot be assessed: the works of its district "
                      "were not available to compare with. This is not a clean chit.", t0)
    found = index.check(work)
    if found is None:
        return _quiet(Status.NOT_ASSESSABLE, "Cannot be assessed: the record has no date, or no "
                      "readable description or map pin, to compare. This is not a clean chit.", t0)
    me, answers, link = found["me"], found["answers"], found["declared"]
    findings: list[Finding] = []

    # 1. the same site by map pin, not declared as the work this one continues. Declared, but
    #    lying on the ground of an earlier work that is not finished yet: still asked (T135)
    finished_named = []                  # named, finished and on the same ground: rebuilt?
    for x, d in found["at_site"]:
        named = ((link and link["work_id"] == x.work_id)
                 or (answers.get(x.work_id) or {}).get("answer") == "continues")
        if named and not same_ground(me, x):
            continue                     # a real continuation beside it
        if named and x.done:
            finished_named.append(x)
            continue
        share = found.get("overlap", {}).get(x.work_id)
        where = (f"Its alignment runs over {share:.0%} of sanctioned work {x.work_id}'s"
                 if share else f"The map pin is {d:,.0f} m from sanctioned work {x.work_id},")
        tail = (" The form names it as the work this one continues, but it lies on that work's "
                "own ground, which is not finished yet."
                if named else " The form does not name it as the work this one continues.")
        findings.append(Finding(
            "SANCTIONED_WORK_AT_THIS_SITE",
            f"{where} of the same kind ({_lakh(x.amount)}, {_state(x)}).{tail}"
            f"{_said(answers, x.work_id)} Please check on site whether it is the same work.",
            hard=False, risk=SITE_RISK,
            evidence={"other": x.work_id, "metres": round(d, 1), "other_amount": x.amount,
                      "other_completed": x.done.isoformat() if x.done else None,
                      "pin_metres": PIN_METRES, "overlap": share, "declared": bool(named),
                      "kind": "at_site"}))

    # 2. what the agency declares this work continues
    if link:
        x, verb = link["rec"], NATURE_WORDS.get(link["nature"], "continues")
        if x is None:
            findings.append(Finding(
                "CONTINUES_SANCTIONED_WORK",
                f"The agency says this work {verb} work {link['work_id']}, which is not on record "
                "in this district: check the work ID on the form.",
                hard=False, risk=0.0,
                evidence={"other": link["work_id"], "nature": link["nature"], "on_record": False,
                          "kind": "declared"}))
        elif ((link["nature"] == "reconstruction" or link.get("same_ground")) and x.done
              and me.first and timedelta(0) <= me.first - x.done < REBUILT_WITHIN):
            findings.append(_rebuilt(me, x, f"The agency says this work {verb} work",
                                     link["nature"], link["nature"] != "reconstruction"))
        else:
            findings.append(Finding(
                "CONTINUES_SANCTIONED_WORK",
                f"The agency says this work {verb} work {x.work_id} ({_lakh(x.amount)}, "
                f"{_state(x)}).",
                hard=False, risk=0.0,
                evidence={"other": x.work_id, "nature": link["nature"], "on_record": True,
                          "kind": "declared"}))

    # 2b. a finished work the form names only among its nearby works, on the same ground
    for x in finished_named:
        if link and link["work_id"] == x.work_id:
            continue                     # judged above
        if me.first and timedelta(0) <= me.first - x.done < REBUILT_WITHIN:
            findings.append(_rebuilt(me, x, "The form names as the work this one continues "
                                     "work", None, True))

    # 3. one job cut into pieces just under a limit (the strictest form only)
    g = found["split"]
    if g:
        others = [m for m in g["members"] if m != me.work_id]
        lo, hi = min(g["amounts"]), max(g["amounts"])
        span = "on the same day" if not g["days"] else f"within {g['days']} days"
        parts = (f" ({', '.join(x.replace(':', ' ') for x in g['segments'])})"
                 if g.get("segments") else "")
        what = ("works whose forms' map pins put them end to end or at one site"
                if g.get("kind") == "pins_split" else "alike works at one place")
        findings.append(Finding(
            "SPLIT_JUST_UNDER_LIMIT",
            f"One of {g['size']} {what}{parts}, recommended {span}: each "
            f"{_rupees(lo)}{'' if lo == hi else f' to {_rupees(hi)}'}, just under the "
            f"{_lakh(g['limit'])} limit, {_lakh(g['total'])} together. Please check whether one "
            f"job was cut into pieces to stay under the limit. Others: {', '.join(others)}.",
            hard=False, risk=SPLIT_RISK,
            evidence={"group_id": g["group_id"], "size": g["size"], "total": g["total"],
                      "limit": g["limit"], "others": others, "days": g["days"],
                      "segments": g.get("segments") or [], "kind": "split"}))

    # 4. look-alikes by words: a note, the form asks the agency
    asked = {f.evidence.get("other") for f in findings}
    for x, t in found["look_alike"]:
        if x.work_id in asked:
            continue
        findings.append(Finding(
            "LOOKS_LIKE_SANCTIONED_WORK",
            f"Reads like sanctioned work {x.work_id} ({_lakh(x.amount)}, {_state(x)}): the same "
            f"place named, descriptions {t:.0%} alike.{_said(answers, x.work_id)} From words "
            "alone this is right about 2 times in 3, so it is a note, not a question"
            + ("." if me.form else "; the cost estimate form asks the agency."),
            hard=False, risk=0.0,
            evidence={"other": x.work_id, "text_similarity": round(t, 3),
                      "other_amount": x.amount, "answer": (answers.get(x.work_id) or {})
                      .get("answer"), "kind": "look_alike"}))

    # 5. a same-kind building just past the one-site line (T136): a note, never counted
    for x, d in found.get("near") or []:
        if x.work_id in asked:
            continue
        named = x.work_id in answers or (link and link["work_id"] == x.work_id)
        findings.append(Finding(
            "NEAR_SANCTIONED_WORK",
            f"Sanctioned work {x.work_id} ({_lakh(x.amount)}, {_state(x)}) of the same kind has "
            f"its map pin {d:,.0f} m from this one, just past the {PIN_METRES:.0f} m that makes "
            "two pins one site"
            + (", and the form names it." if named else
               ", and the form names no nearby work. Check it is not the same building; the "
               "first site video shows whether the asset already stands.")
            + " A note, not a question.",
            hard=False, risk=0.0,
            evidence={"other": x.work_id, "metres": round(d, 1), "other_amount": x.amount,
                      "kind": "near"}))

    n, pinned = found["compared"], bool(me.sites)
    limits = pin_problems(me.form, me.linear)
    if not pinned:
        limits.append("Without the cost estimate form's map pin a repeat can only be looked for "
                      "by words, which are right about 2 times in 3: shown as notes, never "
                      "counted.")
    if not found["place_named"]:
        limits.append("The description names no place, so no look-alike can be found by words.")
    evidence = {"compared": n, "sanctioned_earlier": found["sanctioned_earlier"],
                "pinned": pinned, "pin_metres": PIN_METRES,
                "place_named": found["place_named"]}
    together = index.filed_together(me.work_id)
    if together:            # display only: the queue shows works filed together as one case
        evidence.update(group_id=together[0], size=together[1])
    asked_codes = [f for f in findings if f.risk > 0]
    if asked_codes:
        asked_codes.sort(key=lambda f: -f.risk)
        top = asked_codes[0]
        return AgentResult(
            agent=AGENT, status=Status.ASSESSED, verdict=top.code, risk=top.risk,
            confidence=0.9, hard=False, headline=top.text, version=VERSION,
            findings=asked_codes + [f for f in findings if f.risk == 0], limitations=limits,
            evidence=evidence, duration_ms=int((time.perf_counter() - t0) * 1000))
    if findings:
        return AgentResult(
            agent=AGENT, status=Status.ASSESSED, verdict=findings[0].code, risk=0.0,
            confidence=0.3, hard=False, headline=findings[0].text, version=VERSION,
            findings=findings, limitations=limits, evidence=evidence,
            duration_ms=int((time.perf_counter() - t0) * 1000))
    where = (f"no sanctioned work within {PIN_METRES:.0f} m of its map pin, and none of the "
             f"{n:,} other works of its district" if pinned else
             f"none of the {n:,} other works of its district")
    return AgentResult(
        agent=AGENT, status=Status.ASSESSED, verdict="NOT_SANCTIONED_BEFORE", risk=0.0,
        confidence=0.9 if pinned else 0.3, hard=False, version=VERSION,
        headline=(f"Nothing on record says this work is already sanctioned: {where} names this "
                  "place in the same words." if n else
                  "No other work of its district is on record to compare with."),
        limitations=limits, evidence=evidence,
        duration_ms=int((time.perf_counter() - t0) * 1000))
