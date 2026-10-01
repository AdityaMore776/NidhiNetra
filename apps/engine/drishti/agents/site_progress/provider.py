"""Who judges a photo against a claim: the vision provider behind Site Progress (T510).

The engine never decides which AI service is used, nor pays for one (AGENTS.md rule 10: the
owner's decision). A provider is anything with `judge(claims, photos) -> list[Judgement]`.
The default is no provider: the engine then says it could not look, never "fine".

T501 (needs-owner) adds a Gemini provider on the free tier with a daily cap and a call ledger;
it plugs in here through `set_provider()` or the DRISHTI_VISION env switch, without touching
the engine's rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

VERDICTS = ("shown", "not_shown", "cant_tell")


@dataclass(frozen=True)
class Judgement:
    claim: str
    verdict: str          # shown | not_shown | cant_tell
    reason: str

    def __post_init__(self) -> None:
        if self.verdict not in VERDICTS:
            raise ValueError(f"verdict must be one of {VERDICTS}, not {self.verdict!r}")


class VisionProvider(Protocol):
    name: str

    def judge(self, claims: list[str], photos: list[dict]) -> list[Judgement]: ...


_PROVIDER: VisionProvider | None = None


def set_provider(p: VisionProvider | None) -> None:
    global _PROVIDER
    _PROVIDER = p


def provider() -> VisionProvider | None:
    return _PROVIDER
