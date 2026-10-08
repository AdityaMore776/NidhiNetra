"""The flagship baseline through Gemini's Batch API (T155): the same requests as GeminiJudge, sent
as one file and answered within 24 hours at half the standard price.

Why: the live API allows only so many requests a day for the top model (250 on the owner's tier,
8 Oct 2026), and a ton of checks would in practice be sent in bulk, so the batch price is also the
flagship's fair best price. Each line asks exactly what the live judge asks (same system text,
question, full-resolution photos, temperature 0). Steps (REST, ai.google.dev/gemini-api/docs/
batch-mode): build the JSONL file, upload it (Files API, resumable), create the batch job, poll it,
download the answers; rows_from_results turns them into vlmeval rows.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from drishti_vision import vlm
from drishti_vision.flagship_other import FULL_SIDE, RULES, _gemini_turn
from drishti_vision.vlmdata import SYSTEM

API = "https://generativelanguage.googleapis.com"


def request_line(item, root: Path, max_side: int = FULL_SIDE, prompt: str = "plain",
                 max_output: int = 0) -> str:
    """`prompt`: "plain" (the tuned judge's own system text) or "rules" (plus the task's rules,
    RULES). `max_output` caps the answer, thinking included, so a request's worst-case price is
    known before it is sent (spend.py)."""
    it = item if isinstance(item, dict) else item.__dict__
    system = SYSTEM if prompt == "plain" else SYSTEM + "\n\n" + RULES
    cfg = {"response_mime_type": "application/json", "temperature": 0}
    if max_output:
        cfg["maxOutputTokens"] = max_output
    req = {"system_instruction": {"parts": [{"text": system}]},
           "contents": [{"role": "user", "parts": _gemini_turn(it, root, max_side)}],
           "generationConfig": cfg}
    return json.dumps({"key": it["id"], "request": req})


def batch_cost_usd(rows: list[dict], model: str) -> float:
    """What a collected batch was billed: its answers' tokens at the batch price."""
    from drishti_vision import spend
    return sum(spend.usd(model, r["usage"]["in"], r["usage"]["out"], batch=True)
               for r in rows if r.get("usage"))


def rows_from_results(lines: list[str], items: list) -> list[dict]:
    """The batch's answers as prediction rows (vlmeval.row), skipping failed requests."""
    from drishti_vision import vlmeval
    by = {i.id: i for i in items}
    out = []
    for line in lines:
        if not line.strip():
            continue
        r = json.loads(line)
        it, resp = by.get(r.get("key")), r.get("response")
        if it is None or not resp:
            continue
        try:
            text = [p["text"] for p in resp["candidates"][0]["content"]["parts"]
                    if "text" in p and not p.get("thought")][-1]
        except (KeyError, IndexError):
            text = ""
        u = resp.get("usageMetadata", {})
        usage = {"in": u.get("promptTokenCount", 0),
                 "out": u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)}
        out.append(vlmeval.row(it, {"text": text, "answer": vlm.parse(text), "probs": None,
                                    "seconds": None, "usage": usage, "cost_usd": None,
                                    "served_by": f"{resp.get('modelVersion', '')} (batch)"}))
    return out


def _req(url: str, method: str = "GET", data: bytes | None = None, headers: dict | None = None,
         want_headers: bool = False):
    import urllib.error
    h = {"x-goog-api-key": os.environ["GEMINI_API_KEY"], **(headers or {})}
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    try:
        with urllib.request.urlopen(req, timeout=600) as r:      # noqa: S310 (fixed https host)
            body = r.read()
            return (body, dict(r.headers)) if want_headers else body
    except urllib.error.HTTPError as e:      # Google's own reason, readable (and picklable)
        raise RuntimeError(f"HTTP {e.code}: {e.read().decode(errors='replace')[:600]}") from None


def upload(path: Path, display_name: str) -> str:
    """Resumable upload to the Files API; returns the file's name ("files/...")."""
    size = path.stat().st_size
    _, hdr = _req(f"{API}/upload/v1beta/files", "POST",
                  json.dumps({"file": {"display_name": display_name}}).encode(),
                  {"X-Goog-Upload-Protocol": "resumable", "X-Goog-Upload-Command": "start",
                   "X-Goog-Upload-Header-Content-Length": str(size),
                   "X-Goog-Upload-Header-Content-Type": "application/jsonl",
                   "Content-Type": "application/json"}, want_headers=True)
    url = {k.lower(): v for k, v in hdr.items()}["x-goog-upload-url"]
    body = _req(url, "POST", path.read_bytes(),
                {"X-Goog-Upload-Offset": "0", "X-Goog-Upload-Command": "upload, finalize",
                 "Content-Length": str(size)})
    return json.loads(body)["file"]["name"]


def create(model: str, file_name: str, display_name: str) -> str:
    body = _req(f"{API}/v1beta/models/{model}:batchGenerateContent", "POST",
                json.dumps({"batch": {"display_name": display_name,
                                      "input_config": {"file_name": file_name}}}).encode(),
                {"Content-Type": "application/json"})
    return json.loads(body)["name"]


def status(batch_name: str) -> dict:
    return json.loads(_req(f"{API}/v1beta/{batch_name}"))


def cancel(batch_name: str) -> None:
    _req(f"{API}/v1beta/{batch_name}:cancel", "POST", b"", {"Content-Type": "application/json"})


def download(responses_file: str) -> list[str]:
    body = _req(f"{API}/download/v1beta/{responses_file}:download?alt=media")
    return body.decode().splitlines()
