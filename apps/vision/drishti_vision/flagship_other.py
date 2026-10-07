"""Gemini and OpenAI models as SiteClaim-Bench baselines (T155), over their REST APIs.

Same prompt, same photos, same JSON answer as the claim judge. Keys come from the environment
(GEMINI_API_KEY, OPENAI_API_KEY), travel in headers only, and are never written anywhere. The model
names and prices are arguments: check both on the provider's pages on the day of the run (the
owner's call: paid runs need the owner's go-ahead, AGENTS.md rule 10).
"""

from __future__ import annotations

import base64
import io
import json
import os
import time
import urllib.request
from pathlib import Path

from drishti_vision import vlm
from drishti_vision.vlmdata import SYSTEM, user_prompt


def _jpeg_b64(path: Path, max_side: int = 1024) -> str:
    im = vlm.load_image(path, max_side)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode()


def _post(url: str, headers: dict, body: dict) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), method="POST",
                                 headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=300) as r:      # noqa: S310 (fixed https hosts)
        return json.loads(r.read().decode())


class GeminiJudge:
    URL = "https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"

    def __init__(self, model: str, price_in: float | None = None,
                 price_out: float | None = None) -> None:
        self.key = os.environ.get("GEMINI_API_KEY", "")
        if not self.key:
            raise ValueError("set GEMINI_API_KEY")
        self.model, self.prices, self.name = model, (price_in, price_out), f"gemini:{model}"

    def __call__(self, item, root: Path) -> dict:
        it = item if isinstance(item, dict) else item.__dict__
        parts = [{"text": "Photo A (last visit):"},
                 {"inline_data": {"mime_type": "image/jpeg",
                                  "data": _jpeg_b64(root / it["image_a"])}},
                 {"text": "Photo B (this visit):"},
                 {"inline_data": {"mime_type": "image/jpeg",
                                  "data": _jpeg_b64(root / it["image_b"])}},
                 {"text": user_prompt(it["work_type"], it["claim"], it["claim_kind"])}]
        body = {"system_instruction": {"parts": [{"text": SYSTEM}]},
                "contents": [{"parts": parts}],
                "generationConfig": {"response_mime_type": "application/json",
                                     "temperature": 0}}
        t0 = time.perf_counter()
        r = _post(self.URL.format(m=self.model), {"x-goog-api-key": self.key}, body)
        secs = time.perf_counter() - t0
        try:
            text = r["candidates"][0]["content"]["parts"][0]["text"]
        except (KeyError, IndexError):
            text = ""
        u = r.get("usageMetadata", {})
        cost = None
        if None not in self.prices:
            cost = (u.get("promptTokenCount", 0) * self.prices[0]
                    + u.get("candidatesTokenCount", 0) * self.prices[1]) / 1e6
        return {"text": text, "answer": vlm.parse(text), "probs": None,
                "seconds": round(secs, 3), "served_by": self.model, "cost_usd": cost}


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
