"""Claude as a SiteClaim-Bench baseline (T155): the same prompt and photos as the claim judge.

Uses the official `anthropic` SDK. Credentials come from the environment (ANTHROPIC_API_KEY or an
`ant auth login` profile); nothing is written anywhere. Notes for the current models (Claude API
reference, Sep 2026):
- Claude Opus 5.5 (default) and Claude Sonnet 5.5 take no `temperature`; thinking is adaptive and
  cannot be turned off on Opus 5.5. Depth is set by `output_config.effort`; Opus 5.5's default is
  "medium", so the effort is set explicitly (a flagship gets its best setting, "high").
- Refusal fallbacks are on (`fallbacks: "default"`). If another model answered, the answer is kept
  but marked `served_by`, and vlmeval scores the flagship only on what it answered itself.
- Prices (USD per million tokens) for the cost-per-1,000-checks comparison; check them at run time.
"""

from __future__ import annotations

import base64
import time
from pathlib import Path

from drishti_vision import vlm
from drishti_vision.vlmdata import SYSTEM, user_prompt

PRICES = {"claude-opus-5-5": (4.00, 20.00), "claude-sonnet-5-5": (2.00, 10.00)}


def _b64(path: Path, max_side: int = 1024) -> str:
    import io
    im = vlm.load_image(path, max_side)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=90)
    return base64.standard_b64encode(buf.getvalue()).decode("utf-8")


class ClaudeJudge:
    def __init__(self, model: str = "claude-opus-5-5", effort: str = "high") -> None:
        import anthropic
        self.client = anthropic.Anthropic()
        self.model, self.effort = model, effort
        self.name = f"{model}@{effort}"

    def __call__(self, item, root: Path) -> dict:
        it = item if isinstance(item, dict) else item.__dict__
        content = [
            {"type": "text", "text": "Photo A (last visit):"},
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                         "data": _b64(root / it["image_a"])}},
            {"type": "text", "text": "Photo B (this visit):"},
            {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                         "data": _b64(root / it["image_b"])}},
            {"type": "text", "text": user_prompt(it["work_type"], it["claim"],
                                                 it["claim_kind"])},
        ]
        t0 = time.perf_counter()
        r = self.client.beta.messages.create(
            model=self.model, max_tokens=16000, system=SYSTEM,
            output_config={"effort": self.effort},
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
            messages=[{"role": "user", "content": content}])
        secs = time.perf_counter() - t0
        served_by = getattr(r, "model", self.model)
        if r.stop_reason == "refusal":
            return {"text": "", "answer": None, "probs": None, "seconds": round(secs, 3),
                    "refused": True, "served_by": served_by, "cost_usd": self._cost(r)}
        text = "".join(b.text for b in r.content if b.type == "text")
        return {"text": text, "answer": vlm.parse(text), "probs": None,
                "seconds": round(secs, 3), "served_by": served_by, "cost_usd": self._cost(r)}

    def _cost(self, r) -> float | None:
        p = PRICES.get(self.model)
        u = getattr(r, "usage", None)
        if not p or u is None:
            return None
        return (u.input_tokens * p[0] + u.output_tokens * p[1]) / 1e6
