"""Step 2 of the deck: Data Validation - clean and check the record.

Each issue is BLOCK (the record cannot be processed), WARN (a record
inconsistency worth weight in fusion) or INFO (worth a human's read, almost no
weight). Fusion caps the combined weight of all issues at 0.30, so the record
alone can raise a work to MEDIUM at most, never to HIGH.

IMPOSSIBLE DATES, AND THE ERA THAT EXPLAINS MOST OF THEM

    1,193 real works are recorded as completed before they were recommended.
    The old build measured why (AD-82): the rate collapses six-fold after the
    eSAKSHI portal's first months. Works already finished when the portal opened
    (April 2023) were back-entered with their true completion date and a
    recommendation date from the day of entry. So an impossible date recommended
    in April-December 2023 is named as a likely back-entry and weighs a third of
    one that has no such excuse.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum

from drishti.agents.contract import check_plain_language
from drishti.validation.prohibited import match

PORTAL_OPENED = date(2023, 4, 1)
MIGRATION_WINDOW_END = date(2023, 12, 31)


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


def validate(work: dict, as_of: date) -> list[Issue]:
    issues: list[Issue] = []
    rec, done = work.get("recommended_date"), work.get("completed_date")

    if rec and done and done < rec:
        gap = (rec - done).days
        migration = PORTAL_OPENED <= rec <= MIGRATION_WINDOW_END
        msg = (f"Recorded as completed {gap:,} days before it was recommended.")
        if migration:
            msg += (" It was recommended in the eSAKSHI portal's first months, when works "
                    "already finished were back-entered, so this is likely a data-entry "
                    "artefact; the completion record still needs confirming.")
        issues.append(Issue("IMPOSSIBLE_TIMELINE", Severity.WARN, msg,
                            risk=0.10 if migration else 0.30))

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
