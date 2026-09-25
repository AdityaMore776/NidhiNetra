"""The one shape every agent returns, so fusion and the UI need no special cases.

Two rules are enforced here rather than trusted to each agent:

  Plain, non-accusing language. A monitoring system that calls a work
  fraudulent has made a legal claim about a named official that it cannot
  support. Every headline and finding is checked against BANNED_WORDS.

  "Could not assess" is a status, never a low score. NOT_ASSESSABLE and
  NOT_APPLICABLE carry no risk and are shown as such; they are not a clean chit.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any

BANNED_WORDS = (
    "fraud", "fraudulent", "corrupt", "corruption", "guilty", "criminal", "embezzle",
    "stolen", "theft", "bribe", "scam", "culprit", "accused",
)
_BANNED = re.compile(r"\b(" + "|".join(BANNED_WORDS) + r")\b", re.I)


class Status(str, Enum):
    ASSESSED = "ASSESSED"
    NOT_APPLICABLE = "NOT_APPLICABLE"      # the question does not arise yet (no photos)
    NOT_ASSESSABLE = "NOT_ASSESSABLE"      # the question arises but the data cannot answer it
    NOT_BUILT = "NOT_BUILT"                # the agent is still in development
    ERROR = "ERROR"                        # the agent failed; never read as a finding


def check_plain_language(text: str) -> str:
    m = _BANNED.search(text or "")
    if m:
        raise ValueError(f"accusatory word {m.group(1)!r} in officer-facing text: {text!r}")
    return text


def _clamp(v: float) -> float:
    return max(0.0, min(1.0, float(v)))


@dataclass
class Finding:
    code: str
    text: str
    hard: bool
    risk: float
    evidence: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        check_plain_language(self.text)
        self.risk = _clamp(self.risk)


@dataclass
class AgentResult:
    agent: str
    status: Status
    verdict: str
    risk: float
    confidence: float
    hard: bool
    headline: str
    version: str
    findings: list[Finding] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    evidence: dict[str, Any] = field(default_factory=dict)
    duration_ms: int = 0

    def __post_init__(self) -> None:
        self.status = Status(self.status)
        self.risk = _clamp(self.risk)
        self.confidence = _clamp(self.confidence)
        check_plain_language(self.headline)
        for text in self.limitations:
            check_plain_language(text)

    @property
    def assessed(self) -> bool:
        return self.status == Status.ASSESSED

    def to_json(self) -> dict[str, Any]:
        d = asdict(self)
        d["status"] = self.status.value
        return d

    @classmethod
    def from_json(cls, d: dict[str, Any]) -> "AgentResult":
        d = dict(d)
        d["findings"] = [Finding(**f) for f in d.get("findings", [])]
        return cls(**d)


def not_built(agent: str, question: str) -> AgentResult:
    return AgentResult(agent=agent, status=Status.NOT_BUILT, verdict="NOT_BUILT", risk=0.0,
                       confidence=0.0, hard=False, version="none",
                       headline=f"In development: {question}")
