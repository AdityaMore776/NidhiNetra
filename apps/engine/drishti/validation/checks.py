"""Step 2 of the deck: Data Validation - clean and check the record.

Each issue is BLOCK (the record cannot be processed), WARN (a record
inconsistency worth weight in fusion) or INFO (worth a human's read, almost no
weight). Fusion caps the combined weight of all issues at 0.30, so the record
alone can raise a work to MEDIUM at most, never to HIGH.

IMPOSSIBLE DATES are judged against their own recommendation quarter, because
    bulk entry when eSAKSHI opened explains most of them - see validation/timeline.py.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum

from drishti.agents.contract import check_plain_language
from drishti.validation.prohibited import match
from drishti.validation.timeline import TimelineRates, impossible_date


class Severity(str, Enum):
    BLOCK = "BLOCK"
    WARN = "WARN"
    INFO = "INFO"


@dataclass
class Issue:
    code: str
    severity: Severity
    message: str
    risk: float = 0.0
    clause: str | None = None

    def __post_init__(self) -> None:
        self.severity = Severity(self.severity)
        check_plain_language(self.message)

    def to_json(self) -> dict:
        d = asdict(self)
        d["severity"] = self.severity.value
        return d


def validate(work: dict, as_of: date, timeline: TimelineRates | None = None) -> list[Issue]:
    issues: list[Issue] = []
    rec, done = work.get("recommended_date"), work.get("completed_date")

    imp = impossible_date(rec, done, work.get("agency_name"), timeline)
    if imp:
        issues.append(Issue("IMPOSSIBLE_TIMELINE", Severity.WARN, imp.message, risk=imp.risk))

    if done and done > as_of:
        issues.append(Issue("FUTURE_DATE", Severity.WARN,
                            f"Completion date {done.isoformat()} is after the data was "
                            f"published ({as_of.isoformat()}).", risk=0.20))

    amount = work.get("amount")
    if amount is None or float(amount) <= 0:
        issues.append(Issue("MISSING_AMOUNT", Severity.WARN,
                            "The record carries no amount, so its cost cannot be checked.",
                            risk=0.05))

    if not work.get("work_type_code"):
        issues.append(Issue("MISSING_WORK_TYPE", Severity.INFO,
                            "The record carries no work type, so it has no peer group."))

    m = match(work.get("description"))
    if m:
        msg = (f"The description reads as \"{m.keyword}\" being the work itself, which "
               f"MPLADS Guidelines (June 2016) Annexure-II item {m.annexure_item} lists as "
               f"not permitted: {m.text}")
        if m.exceptions:
            msg += " Exceptions: " + " ".join(m.exceptions)
        msg += " Worth reading against the 2023 guidelines before any action."
        issues.append(Issue("PROHIBITED_CATEGORY", Severity.INFO, msg, risk=0.10,
                            clause=f"Annexure-II item {m.annexure_item}"))
    return issues
