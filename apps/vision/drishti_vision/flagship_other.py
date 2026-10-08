"""Gemini and OpenAI models as SiteClaim-Bench baselines (T155), over their REST APIs.

FAIR, AT EACH MODEL'S BEST (owner, 8 Oct 2026): the flagship gets the same system text, the same
question and the same two real photos as the tuned judge, and never sees a test item before it is
asked. It is NOT held back to the judge's limits: it gets the photos at full resolution (up to
FULL_SIDE; the judge works at vlm.MAX_SIDE), its own thinking, temperature 0. Its optional worked
examples (few_shot_examples) come from the TRAINING districts only, as the tuned judge's training
did. Which setting counts for each model is chosen on the calibration split, never the test.

Keys come from the environment (GEMINI_API_KEY, OPENAI_API_KEY; on Modal from a Modal Secret),
travel in headers only, and are never written anywhere. Model names and prices are arguments:
check both on the provider's pages on the day of the run (the owner's call: paid runs need the
owner's go-ahead, AGENTS.md rule 10).
"""

from __future__ import annotations

import base64
import io
import json
import os
import random
import re
import time
import urllib.error
import urllib.request
from pathlib import Path

from drishti_vision import vlm
from drishti_vision.vlmdata import SYSTEM, user_prompt

# The task's own rules, as the tuned judge learnt them from its training labels (8 Oct 2026: on
# the plain prompt the flagship mistook "B shows the finished road" claims for "built since A",
# and refused most real progress because before/after photos were taken from different spots).
# Rules only: no example, no answer, nothing from the test.
RULES = (
    "How to decide:\n"
    "- There are two kinds of claim. 'What B shows now' (for example 'CC road completed'): judge "
    "only whether photo B shows that stage; photo A is context, and two similar photos of the "
    "finished work support a 'completed' claim. 'Work done between A and B' (for example "
    "'completed since the last visit'): shown only if B has permanent structure that A does "
    "not.\n"
    "- shown: the photos support the claim. not_shown: the photos go against it (nothing "
    "permanent added; B less built than A; B at an earlier stage than claimed; finished work "
    "already in A claimed again as new). cant_tell: the photos cannot decide (B is clearly "
    "another place, too dark, or the view is blocked).\n"
    "- A work's site photos are taken on different days, often from different spots and "
    "angles; that alone does not make them different places. Call it another place only when "
    "what is visible cannot be the same site (a different kind of structure, surroundings that "
    "cannot match).\n"
    "- People, vehicles, stacked materials, light, shadows and season are never progress.")

FULL_SIDE = 3072     # the photos' own resolution, only very large files shrunk (request size)


def _jpeg_b64(path: Path, max_side: int = FULL_SIDE) -> str:
    """The photo as a JPEG: at full resolution by default; max_side=vlm.MAX_SIDE gives exactly the
    tuned judge's view (vlm.load_image)."""
    im = vlm.load_image(path, max_side)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=95)
    return base64.b64encode(buf.getvalue()).decode()


def _post(url: str, headers: dict, body: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=300) as r:      # noqa: S310 (fixed https hosts)
        return json.loads(r.read().decode())


class QuotaExhausted(RuntimeError):
    """The provider's daily quota is used up: stop the run; it resumes from its saved answers."""
    stop_run = True


def daily_quota(error_body: str) -> bool:
    return bool(re.search(r"PerDay", error_body))


def retry_after(error_body: str, default: float = 30.0) -> float:
    m = re.search(r'"retryDelay"\s*:\s*"([\d.]+)s"', error_body)
    return float(m.group(1)) if m else default


def few_shot_examples(items: list, k: int = 4, seed: int = 0) -> list:
    """Worked examples for the flagship, the same for every question: real items from the
    TRAINING split only, one of each answer first (shown, not_shown, cant_tell), then a
    same-type different place if there is one."""
    rng = random.Random(seed)
    pool = [i for i in items if i.split == "train" and i.real]
    rng.shuffle(pool)
    out = []
    for want in ("shown", "not_shown", "cant_tell"):
        hit = next((i for i in pool if i.target["verdict"] == want and i not in out), None)
        if hit:
            out.append(hit)
    for i in pool:
        if len(out) >= k:
            break
        if i not in out and (i.trick == "other_site_same" or len(out) < k):
            out.append(i)
    return out[:k]


def _gemini_turn(it: dict, root: Path, max_side: int = FULL_SIDE) -> list[dict]:
    def img(rel: str) -> dict:
        return {"inline_data": {"mime_type": "image/jpeg",
                                "data": _jpeg_b64(root / rel, max_side)}}
    return [{"text": "Photo A (last visit):"}, img(it["image_a"]),
            {"text": "Photo B (this visit):"}, img(it["image_b"]),
            {"text": user_prompt(it["work_type"], it["claim"], it["claim_kind"])}]


class GeminiJudge:
    URL = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"

    def __init__(self, model: str, price_in: float | None = None,
                 price_out: float | None = None, examples: list | None = None,
                 root: Path | None = None, min_interval: float = 0.0,
                 max_retries: int = 8, max_side: int = FULL_SIDE) -> None:
        self.key = os.environ.get("GEMINI_API_KEY", "")
        if not self.key:
            raise ValueError("set GEMINI_API_KEY")
        self.model, self.prices, self.name = model, (price_in, price_out), f"gemini:{model}"
        self.min_interval, self.max_retries, self._last = min_interval, max_retries, 0.0
        self.max_side = max_side
        self.history: list[dict] = []          # worked examples as earlier turns of the chat
        for ex in examples or []:
            d = ex if isinstance(ex, dict) else ex.__dict__
            self.history += [{"role": "user", "parts": _gemini_turn(d, root, max_side)},
                             {"role": "model", "parts": [{"text": json.dumps(
                                 vlm.answer_of(d), ensure_ascii=False)}]}]
        if examples:
            self.name += f"+{len(examples)}shot"
        if max_side != FULL_SIDE:
            self.name += f"@{max_side}px"

    def _call(self, body: dict) -> dict:
        for attempt in range(self.max_retries + 1):
            wait = self.min_interval - (time.time() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.time()
            try:
                return _post(self.URL.format(m=self.model), {"x-goog-api-key": self.key}, body)
            except urllib.error.HTTPError as e:
                msg = e.read().decode(errors="replace")
                if e.code == 429 and daily_quota(msg):
                    raise QuotaExhausted(msg[:300]) from None
                if e.code in (429, 500, 502, 503, 504) and attempt < self.max_retries:
                    time.sleep(min(120.0, retry_after(msg, 10.0 * 2 ** attempt)))
                    continue
                raise RuntimeError(f"HTTP {e.code}: {msg[:300]}") from None
        raise RuntimeError("no answer after retries")

    def __call__(self, item, root: Path) -> dict:
        it = item if isinstance(item, dict) else item.__dict__
        body = {"system_instruction": {"parts": [{"text": SYSTEM}]},
                "contents": self.history + [{"role": "user",
                                             "parts": _gemini_turn(it, root, self.max_side)}],
                "generationConfig": {"response_mime_type": "application/json",
                                     "temperature": 0}}
        t0 = time.perf_counter()
        r = self._call(body)
        secs = time.perf_counter() - t0
        try:      # the answer is the last text part (thinking models may send more parts)
            text = [p["text"] for p in r["candidates"][0]["content"]["parts"]
                    if "text" in p and not p.get("thought")][-1]
        except (KeyError, IndexError):
            text = ""
        u = r.get("usageMetadata", {})
        # billed tokens: thinking is billed as output, so it counts (priced afterwards from the
        # provider's page on the day, gemini_cost())
        usage = {"in": u.get("promptTokenCount", 0),
                 "out": u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)}
        cost = None
        if None not in self.prices:
            cost = (usage["in"] * self.prices[0] + usage["out"] * self.prices[1]) / 1e6
        return {"text": text, "answer": vlm.parse(text), "probs": None, "usage": usage,
                "seconds": round(secs, 3), "served_by": r.get("modelVersion", self.model),
                "cost_usd": cost}


class OpenAIJudge:
    URL = "https://api.openai.com/v1/responses"

    def __init__(self, model: str, price_in: float | None = None,
                 price_out: float | None = None) -> None:
        self.key = os.environ.get("OPENAI_API_KEY", "")
        if not self.key:
            raise ValueError("set OPENAI_API_KEY")
        self.model, self.prices, self.name = model, (price_in, price_out), f"openai:{model}"

    def __call__(self, item, root: Path) -> dict:
        it = item if isinstance(item, dict) else item.__dict__

        def img(p: Path) -> dict:
            return {"type": "input_image", "image_url": f"data:image/jpeg;base64,{_jpeg_b64(p)}"}

        content = [{"type": "input_text", "text": "Photo A (last visit):"},
                   img(root / it["image_a"]),
                   {"type": "input_text", "text": "Photo B (this visit):"},
                   img(root / it["image_b"]),
                   {"type": "input_text", "text": user_prompt(it["work_type"], it["claim"],
                                                              it["claim_kind"])}]
        body = {"model": self.model, "instructions": SYSTEM,
                "input": [{"role": "user", "content": content}]}
        t0 = time.perf_counter()
        r = _post(self.URL, {"Authorization": f"Bearer {self.key}"}, body)
        secs = time.perf_counter() - t0
        text = r.get("output_text") or "".join(
            c.get("text", "") for o in r.get("output", []) if o.get("type") == "message"
            for c in o.get("content", []))
        u = r.get("usage", {})
        cost = None
        if None not in self.prices:
            cost = (u.get("input_tokens", 0) * self.prices[0]
                    + u.get("output_tokens", 0) * self.prices[1]) / 1e6
        return {"text": text, "answer": vlm.parse(text), "probs": None,
                "seconds": round(secs, 3), "served_by": self.model, "cost_usd": cost}
