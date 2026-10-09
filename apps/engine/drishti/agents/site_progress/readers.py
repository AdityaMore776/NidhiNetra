"""The readers that look at site photos for Site Progress v2 (T510). They run OFFLINE.

Both are run by data/build_site_observations.py over the downloaded evidence, once per photo
(cached by the photo's SHA-256), and store readings in the work's evidence facts. The engine
never calls a model: it judges claims against stored readings, so a page on the live site
never waits for, or pays for, a model.

ZeroShotReader   free and local: an open CLIP-family model (open_clip, CPU) scores a photo
                 against every line of reference/site_concepts.yaml. Needs `open_clip_torch`
                 and `torch` in the trial venv; the weights download once from the model hub.
                 Names what a photo shows; cannot count, measure or read a sentence like
                 "roof slab cast".
GeminiReader     optional (T501, the owner's key, free tier): a vision-language model judges
                 each claim against the photos: shown / not_shown / cant_tell, with a reason.
                 Off without GEMINI_API_KEY. A hard daily cap, a ledger of calls per day, and a
                 cache so no photo-and-claims pair is ever sent twice. The key travels in a
                 header, never in a URL, and is never written anywhere.
VLMReader        optional (T156): the fine-tuned claim judge of plan T150 (apps/vision, T154), run
                 on the team's own GPU, free. Off without DRISHTI_VLM_ADAPTER. Judges each claim
                 on matched last-visit / this-visit views; "cant_tell" unless confident.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import urllib.request
from collections.abc import Callable
from datetime import date
from pathlib import Path

from drishti.agents.site_progress.observe import observation, prompts

VERDICTS = ("shown", "not_shown", "cant_tell")


class ZeroShotReader:
    """Scores a photo against every concept line; returns the stored reading (observe.py)."""

    def __init__(self, model: str = "ViT-B-32", pretrained: str = "laion2b_s34b_b79k",
                 device: str = "cpu") -> None:
        import open_clip  # the trial venv only: the engine itself never imports a model
        import torch
        self.name = f"zeroshot:{model}/{pretrained}"
        self._torch = torch
        self.model, _, self.preprocess = open_clip.create_model_and_transforms(
            model, pretrained=pretrained, device=device)
        self.model.eval()
        self.device = device
        tokenizer = open_clip.get_tokenizer(model)
        self.texts = [p.text for p in prompts()]
        with torch.no_grad():
            t = self.model.encode_text(tokenizer(self.texts).to(device))
            self.text_features = t / t.norm(dim=-1, keepdim=True)

    def read(self, image) -> dict:
        """`image` is a PIL image (already turned upright)."""
        torch = self._torch
        with torch.no_grad():
            x = self.preprocess(image.convert("RGB")).unsqueeze(0).to(self.device)
            f = self.model.encode_image(x)
            f = f / f.norm(dim=-1, keepdim=True)
            scale = float(self.model.logit_scale.exp())
            logits = (scale * f @ self.text_features.T)[0].tolist()
        return observation(dict(zip(self.texts, logits, strict=True)), reader=self.name)


class QuotaReached(RuntimeError):
    """The day's cap of model calls is used up: the rest waits for tomorrow, unjudged."""


Transport = Callable[[str, dict, bytes], dict]

PROMPT = """You are helping a government officer check whether site photos of a public works
project show what the project's record claims. Judge ONLY from what is visible in the photos.
For each numbered claim answer:
  "shown"      the photos clearly show it
  "not_shown"  the photos clearly show the place and the claimed thing is clearly absent or
               clearly different (for example: the claim says a roof slab is cast and the photo
               shows walls with no roof)
  "cant_tell"  the photos do not let you decide (out of frame, too far, too dark, not the site)
Never guess intent and never accuse anyone. Give a short plain reason (at most 20 words) about
what is visible. Reply with JSON only: a list of {"claim": <number>, "verdict": "...",
"reason": "..."}.
Claims:
"""


def _post(url: str, headers: dict, body: bytes) -> dict:
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=120) as r:      # noqa: S310 (fixed https host)
        return json.loads(r.read().decode("utf-8"))


class GeminiReader:
    """Judges claims against photos with Gemini on the free tier, within a daily cap."""

    URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    def __init__(self, key: str | None = None, model: str | None = None,
                 daily_cap: int = 200, ledger: Path | None = None,
                 transport: Transport | None = None) -> None:
        key = key if key is not None else os.environ.get("GEMINI_API_KEY", "")
        if not key:
            raise ValueError("no GEMINI_API_KEY: the vision-language reader stays off")
        self._key = key
        self.model = model or os.environ.get("DRISHTI_GEMINI_MODEL", "gemini-2.5-flash")
        self.name = f"gemini:{self.model}"
        self.daily_cap = daily_cap
        self.ledger = ledger
        self._transport = transport or _post
        self._cache: dict[str, list[dict]] = {}
        self._book = self._load_ledger()

    def _load_ledger(self) -> dict:
        if self.ledger and self.ledger.exists():
            return json.loads(self.ledger.read_text(encoding="utf-8"))
        return {"calls": {}, "cache": {}}

    def _save_ledger(self) -> None:
        if self.ledger:
            self.ledger.parent.mkdir(parents=True, exist_ok=True)
            self.ledger.write_text(json.dumps(self._book, indent=1), encoding="utf-8")

    def judge(self, claims: list[str], photos: list[tuple[str, bytes]]) -> list[dict]:
        """`photos` = [(sha256, jpeg bytes)]. Returns one {claim, verdict, reason, reader}
        per claim, in order."""
        key = hashlib.sha256(json.dumps([self.model, claims, sorted(s for s, _ in photos)])
                             .encode("utf-8")).hexdigest()
        cached = self._cache.get(key) or self._book["cache"].get(key)
        if cached is not None:
            return cached
        today = date.today().isoformat()
        used = int(self._book["calls"].get(today, 0))
        if used >= self.daily_cap:
            raise QuotaReached(f"{used} calls today, cap {self.daily_cap}")
        text = PROMPT + "\n".join(f"{i + 1}. {c}" for i, c in enumerate(claims))
        parts = [{"text": text}] + [
            {"inline_data": {"mime_type": "image/jpeg", "data": base64.b64encode(b).decode()}}
            for _sha, b in photos]
        body = json.dumps({"contents": [{"parts": parts}],
                           "generationConfig": {"response_mime_type": "application/json",
                                                "temperature": 0}}).encode("utf-8")
        self._book["calls"][today] = used + 1
        self._save_ledger()                       # counted before the call: a crash still counts
        reply = self._transport(self.URL.format(model=self.model),
                                {"Content-Type": "application/json",
                                 "x-goog-api-key": self._key}, body)
        out = self._parse(reply, claims)
        self._cache[key] = out
        self._book["cache"][key] = out
        self._save_ledger()
        return out

    def _parse(self, reply: dict, claims: list[str]) -> list[dict]:
        try:
            text = reply["candidates"][0]["content"]["parts"][0]["text"]
            items = json.loads(text)
        except (KeyError, IndexError, TypeError, ValueError):
            items = []
        by_number = {}
        for it in items if isinstance(items, list) else []:
            try:
                by_number[int(it.get("claim"))] = it
            except (TypeError, ValueError, AttributeError):
                continue
        out = []
        for i, c in enumerate(claims, start=1):
            it = by_number.get(i) or {}
            verdict = it.get("verdict") if it.get("verdict") in VERDICTS else "cant_tell"
            reason = " ".join(str(it.get("reason") or "").split())[:200]
            out.append({"claim": c, "verdict": verdict, "reason": reason, "reader": self.name})
        return out


# A runner judges one (before, now) pair: (a_jpeg, b_jpeg, work_type, claim, kind) ->
# {"verdict", "probs": {verdict: p}, "reason"}. The real one wraps the fine-tuned model (T154).
PairRunner = Callable[[bytes, bytes, str, str, str], dict]

_WORK_WORDS = (("road", ("road", "sadak", "lane", "street", "path", "kharanja", "interlocking")),
               ("drain", ("drain", "nali", "naali", "nala")),
               ("boundary_wall", ("boundary wall", "compound wall", "chaardiwari")),
               ("building", ("hall", "building", "bhawan", "room", "anganwadi", "school", "shed",
                             "toilet", "complex", "centre", "center", "kendra")))
_PERIOD_WORDS = ("since the last", "this month", "since last", "pichhli", "is mahine")


def work_type_of(asset: str) -> str:
    a = f" {asset.lower()} "
    for wt, words in _WORK_WORDS:
        if any(w in a for w in words):
            return wt
    return "other"


class VLMReader:
    """The fine-tuned claim judge (T150 plan, T154 model, T156 reader). OFFLINE and behind a
    switch: build_site_visits.py uses it only when DRISHTI_VLM_ADAPTER names a trained adapter;
    readings stay notes, never counted, until real visits pass T120 §14 (AGENTS.md rule 4).

    Same contract as GeminiReader.judge: `photos` are ("before-<viewpoint>", jpeg) and
    ("now-<viewpoint>", jpeg). Each claim is judged on every viewpoint seen both last time and now;
    the views are combined so that one confident "shown" is enough to say shown, "not_shown" needs
    EVERY judged view to say so confidently, and anything else is "cant_tell" (never a finding).
    A claim with no before view is judged on the now view alone (A = B), and then only "reached"."""

    def __init__(self, runner: PairRunner | None = None, adapter: str | None = None,
                 base: str | None = None, sure: float = 0.6, asset: str = "") -> None:
        self.sure = sure
        self.asset = asset
        if runner is None:
            adapter = adapter or os.environ.get("DRISHTI_VLM_ADAPTER", "")
            if not adapter:
                raise ValueError("no DRISHTI_VLM_ADAPTER: the fine-tuned reader stays off")
            base = base or os.environ.get("DRISHTI_VLM_BASE", "Qwen/Qwen3-VL-4B-Instruct")
            runner = _model_runner(base, adapter)
            self.name = f"vlm:{Path(adapter).name}"
        else:
            self.name = "vlm:test"
        self._run = runner

    def judge(self, claims: list[str], photos: list[tuple[str, bytes]]) -> list[dict]:
        before = {n.split("-", 1)[1]: b for n, b in photos if n.startswith("before-")}
        now = {n.split("-", 1)[1]: b for n, b in photos if n.startswith("now-")}
        wt = work_type_of(" ".join([self.asset, *claims]))
        out = []
        for c in claims:
            kind = "period" if any(w in c.lower() for w in _PERIOD_WORDS) else "reached"
            pairs = [(before[v], now[v]) for v in now if v in before]
            if not pairs and kind == "reached":
                pairs = [(b, b) for b in now.values()]
            answers = [self._run(a, b, wt, c, kind) for a, b in pairs]
            out.append(self._combine(c, answers))
        return out

    def _combine(self, claim: str, answers: list[dict]) -> dict:
        def p(a, v):
            return float((a.get("probs") or {}).get(v, 1.0 if a.get("verdict") == v else 0.0))
        shown = [a for a in answers if a.get("verdict") == "shown" and p(a, "shown") >= self.sure]
        judged = [a for a in answers if a.get("verdict") in ("shown", "not_shown")]
        if shown:
            best = max(shown, key=lambda a: p(a, "shown"))
            verdict, reason = "shown", best.get("reason", "")
        elif judged and len(judged) == len(answers) and all(
                a["verdict"] == "not_shown" and p(a, "not_shown") >= self.sure for a in judged):
            verdict, reason = "not_shown", judged[0].get("reason", "")
        else:
            verdict = "cant_tell"
            reason = ("the views do not let the reader decide" if answers
                      else "no view to judge the claim on")
        return {"claim": claim, "verdict": verdict,
                "reason": " ".join(str(reason or "").split())[:200], "reader": self.name}


def _model_runner(base: str, adapter: str) -> PairRunner:     # pragma: no cover (GPU, trial venv)
    import io

    from drishti_vision import vlm  # the trial venv only: the engine itself never imports it
    from PIL import Image
    loaded = vlm.load(base, quant4=True, adapter=adapter)

    def run(a: bytes, b: bytes, work_type: str, claim: str, kind: str) -> dict:
        o = vlm.judge_images(loaded, Image.open(io.BytesIO(a)), Image.open(io.BytesIO(b)),
                             work_type, claim, kind)
        ans = o["answer"] or {}
        return {"verdict": ans.get("verdict", "cant_tell"), "probs": o["probs"] or {},
                "reason": ans.get("reason", "")}
    return run
