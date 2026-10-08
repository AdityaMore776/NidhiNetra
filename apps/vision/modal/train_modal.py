"""The claim judge's training and scoring on a rented GPU (Modal), with the same code as on the PC.

The owner offered ~$30 of Modal credit for training (7 Oct 2026). Every function has a hard timeout,
so one run can never spend more than its limit (A100-40GB ~ $2.1 an hour at the time of writing;
check modal.com/pricing):

    sft      LoRA fine-tuning (vlm.fit)                         timeout 3 h
    rl       GRPO with checkable rewards (vlmrl.rl_fit)        timeout 4 h
    score    SiteClaim-Bench on a split (vlmeval)               timeout 1 h

Data goes up once to a Modal volume (photos, edited images, items.jsonl):

    modal volume create nidhinetra-vlm
    modal volume put nidhinetra-vlm D:\\nidhinetra-data\\gov\\mgnrega\\photos /gov/mgnrega/photos
    modal volume put nidhinetra-vlm D:\\nidhinetra-data\\vlm\\v1 /vlm/v1

Then, from apps/vision:

    modal run modal/train_modal.py::sft --items /data/vlm/v1/items.jsonl --out /data/runs/sft4b
    modal run modal/train_modal.py::rl --adapter /data/runs/sft4b/final --out /data/runs/rl4b
    modal run modal/train_modal.py::score --adapter /data/runs/rl4b/final --out
    /data/runs/rl4b/test.jsonl
    modal volume get nidhinetra-vlm /runs/rl4b D:\\nidhinetra-data\\runs\\rl4b

Photos never leave the team's own accounts (D:, the private volume); nothing goes to git.
"""

from __future__ import annotations

from pathlib import Path

import modal

HERE = Path(__file__).resolve().parent
PKG = HERE.parent / "drishti_vision"

image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("torch==2.11.0", "torchvision==0.26.0", "transformers==5.19.0", "peft==0.21.2",
                 "accelerate==1.15.0", "bitsandbytes==0.50.2", "pillow", "numpy",
                 "opencv-python-headless", "huggingface_hub")
    .env({"HF_HOME": "/data/hf-cache", "PYTHONIOENCODING": "utf-8"})
    .add_local_dir(str(PKG), "/root/drishti_vision")
)
vol = modal.Volume.from_name("nidhinetra-vlm", create_if_missing=True)
app = modal.App("nidhinetra-claim-judge", image=image)
GPU = "A100-40GB"


def _logger(every_s: float = 180.0):
    """print every progress line; save to the volume at most every `every_s` seconds. Many
    containers saving the shared volume every 25 answers queued behind each other (8 Oct 2026:
    a scoring run slowed from 1.3 s to over 10 s a check while 9 others ran)."""
    import time
    last = [time.time()]

    def log(s):
        print(s, flush=True)
        if time.time() - last[0] >= every_s:
            vol.commit()
            last[0] = time.time()
    return log

@app.function(gpu=GPU, volumes={"/data": vol}, timeout=3 * 3600)
def sft(items: str = "/data/vlm/v1/items.jsonl", out: str = "/data/runs/sft4b",
        base: str = "Qwen/Qwen3-VL-4B-Instruct", epochs: float = 2.0, rank: int = 16,
        lr: float = 1e-4, accum: int = 8, real_only: bool = False, edited_share: float = 0.2,
        max_items: int = 0, seed: int = 0, grad_ckpt: bool = False):
    import sys
    sys.path.insert(0, "/root")
    from drishti_vision import vlm
    cfg = vlm.TrainConfig(base=base, items=items, root="/data", out=out, quant4=False,
                          rank=rank, alpha=2 * rank, lr=lr, epochs=epochs, accum=accum,
                          real_only=real_only, edited_share=edited_share, eval_every=10**9,
                          max_items=max_items, seed=seed, grad_ckpt=grad_ckpt)
    info = vlm.fit(cfg, log=lambda s: print(s, flush=True))
    vol.commit()
    return {k: info[k] for k in ("items", "steps", "minutes", "peak_gpu_gb")}


@app.function(gpu=GPU, volumes={"/data": vol}, timeout=4 * 3600)
def rl(adapter: str = "/data/runs/sft4b/final", out: str = "/data/runs/rl4b",
       items: str = "/data/vlm/v1/items.jsonl", base: str = "Qwen/Qwen3-VL-4B-Instruct",
       prompts: int = 1500, group: int = 6, lr: float = 5e-6, hard: str = "",
       focus: str = "", real_only: bool = False, per_verdict: int = 0):
    """`focus`: comma-separated tricks to practise (vlmrl.focus_prompts); `real_only`: no edited
    items, as in sft --real-only."""
    import json
    import sys
    sys.path.insert(0, "/root")
    from drishti_vision import vlm, vlmrl
    cfg = vlmrl.RLConfig(base=base, adapter=adapter, items=items, root="/data", out=out,
                         quant4=False, group=group, lr=lr, prompts=prompts, save_every=100)
    tc = vlm.TrainConfig(base=base, items=items, root="/data", out=out, real_only=real_only)
    chosen = vlm.training_items(items, tc)
    if hard:                                   # predictions on the training split (H3)
        rows = [json.loads(x) for x in Path(hard).read_text(encoding="utf-8").splitlines() if x]
        chosen = (vlmrl.balanced_prompts(rows, chosen, per_verdict) if per_verdict
                  else vlmrl.hard_prompts(rows, chosen))
    elif focus:
        chosen = vlmrl.focus_prompts(chosen, tuple(focus.split(",")))

    info = vlmrl.rl_fit(cfg, prompts=chosen, log=_logger())
    vol.commit()
    return {k: info[k] for k in ("prompts", "skipped_flat_groups", "minutes", "peak_gpu_gb")}


@app.function(gpu=GPU, volumes={"/data": vol}, timeout=3600)
def score(adapter: str = "", out: str = "/data/runs/base/test.jsonl",
          items: str = "/data/vlm/v1/items.jsonl", split: str = "test",
          base: str = "Qwen/Qwen3-VL-4B-Instruct", limit: int = 0, batch: int = 8,
          real_only: bool = False, max_side: int = 512):
    return _score(adapter, out, items, split, base, limit, batch, real_only, max_side)


@app.function(gpu="L4", volumes={"/data": vol}, timeout=3 * 3600)
def score_l4(adapter: str = "", out: str = "/data/runs/base/test.jsonl",
             items: str = "/data/vlm/v1/items.jsonl", split: str = "test",
             base: str = "Qwen/Qwen3-VL-4B-Instruct", limit: int = 0, batch: int = 8,
             real_only: bool = False, max_side: int = 512):
    """The same scoring on an L4 (24 GB, about a third of the A100's price an hour): scoring is
    one answer at a time, so the big card mostly waits. Resumable, like score."""
    return _score(adapter, out, items, split, base, limit, batch, real_only, max_side)


@app.function(volumes={"/data": vol}, timeout=8 * 3600, secrets=[modal.Secret.from_name("gemini")])
def flagship(model: str = "", items: str = "/data/vlm/v6/items_eye.jsonl", split: str = "test",
             out: str = "", shots: int = 0, examples_from: str = "/data/vlm/v6/items_eye.jsonl",
             max_side: int = 3072, rpm: float = 0.0, limit: int = 0, list_models: bool = False,
             shard: int = 0, shards: int = 1):
    """Gemini as the flagship baseline (flagship_other.GeminiJudge), on a CPU container: the key
    comes from the Modal Secret "gemini" (the owner typed it into Modal; it never touches the PC).
    At its best: full-resolution photos, its own thinking; `shots` worked examples from the
    TRAINING split of `examples_from` only. Resumable; stops cleanly on the daily quota.
    `shard`/`shards`: this container answers every shards-th item (run several at once; the
    report script merges `<out>` files named *_s<k>.jsonl).
    `list_models`: print the models this key can call, and nothing else."""
    import json
    import os
    import sys
    import urllib.request
    sys.path.insert(0, "/root")
    if list_models:
        req = urllib.request.Request(
            "https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000",
            headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"]})
        with urllib.request.urlopen(req, timeout=60) as r:      # noqa: S310
            for m in json.loads(r.read().decode()).get("models", []):
                if "generateContent" in m.get("supportedGenerationMethods", []):
                    print(m["name"], m.get("inputTokenLimit"), m.get("displayName"), flush=True)
        return None
    from drishti_vision import flagship_other, vlmeval
    from drishti_vision.vlmdata import read_items
    its = [i for i in read_items(items) if i.split == split]
    its = its[:limit] if limit else its
    its = its[shard::shards]
    ex = flagship_other.few_shot_examples(read_items(examples_from), k=shots) if shots else None
    J = flagship_other.GeminiJudge(model, examples=ex, root=Path("/data"), max_side=max_side,
                                   min_interval=60.0 / rpm if rpm else 0.0)
    Path(out).parent.mkdir(parents=True, exist_ok=True)

    rows = vlmeval.predict(J, its, Path("/data"), Path(out), log=_logger())
    vol.commit()
    if not rows:
        return None
    res = vlmeval.score(rows)
    res["model"], res["answered_items"], res["asked_items"] = J.name, len(rows), len(its)
    Path(out.replace(".jsonl", "_score.json")).write_text(json.dumps(res, indent=1))
    vol.commit()
    return {"answered": len(rows), "of": len(its), **res["headline_real_only"]}


@app.function(volumes={"/data": vol}, timeout=3 * 3600, memory=8192,
              secrets=[modal.Secret.from_name("gemini")])
def flagship_batch(action: str = "submit", model: str = "gemini-3.1-pro-preview",
                   items: str = "/data/vlm/v6/items_eye2.jsonl", split: str = "test",
                   out_dir: str = "", chunk: int = 300):
    """Gemini through the Batch API (flagship_batch.py): `submit` builds the request file from
    the photos on the volume (chunks of `chunk` questions), uploads it and starts the jobs;
    `collect` reports their state and, when all have finished, writes <split>.jsonl and its
    score in `out_dir`. Same questions and photos as the live judge; half the price."""
    import json
    import sys
    sys.path.insert(0, "/root")
    from drishti_vision import flagship_batch as fb
    from drishti_vision import vlmeval
    from drishti_vision.vlmdata import read_items
    its = [i for i in read_items(items) if i.split == split]
    od = Path(out_dir)
    od.mkdir(parents=True, exist_ok=True)
    rec_p = od / f"batch_{split}.json"
    if action == "submit":
        jobs = []
        for k in range(0, len(its), chunk):
            p = Path(f"/tmp/req_{split}_{k}.jsonl")
            with open(p, "w", encoding="utf-8") as f:
                for it in its[k:k + chunk]:
                    f.write(fb.request_line(it, Path("/data")) + "\n")
            name = f"nidhinetra-{split}-{k}"
            fname = fb.upload(p, name)
            jobs.append({"batch": fb.create(model, fname, name), "file": fname,
                         "n": len(its[k:k + chunk]), "mb": round(p.stat().st_size / 1e6, 1)})
            print(jobs[-1], flush=True)
        rec_p.write_text(json.dumps({"model": model, "split": split, "items": items,
                                     "jobs": jobs}, indent=1))
        vol.commit()
        return jobs
    rec = json.loads(rec_p.read_text())
    if action == "cancel":                     # stop the jobs (owner, 8 Oct 2026: billing issue)
        for j in rec["jobs"]:
            try:
                fb.cancel(j["batch"])
            except Exception as e:  # noqa: BLE001 (a finished job cannot be cancelled)
                print(j["batch"], "cancel:", str(e)[:120], flush=True)
            try:
                st = fb.status(j["batch"])
                print(j["batch"], st.get("metadata", {}).get("state") or st.get("state"),
                      flush=True)
            except Exception as e:  # noqa: BLE001
                print(j["batch"], "status:", str(e)[:600], flush=True)
        return None
    states, lines = [], []
    for j in rec["jobs"]:
        st = fb.status(j["batch"])
        state = st.get("metadata", {}).get("state") or st.get("state")
        states.append(state)
        resp = (st.get("response") or {}).get("responsesFile") or \
            (st.get("metadata", {}).get("output") or {}).get("responsesFile")
        print(j["batch"], state, resp, flush=True)
        if state in ("JOB_STATE_SUCCEEDED", "BATCH_STATE_SUCCEEDED") and resp:
            lines += fb.download(resp)
    if not all(s in ("JOB_STATE_SUCCEEDED", "BATCH_STATE_SUCCEEDED") for s in states):
        return {"states": states}
    rows = fb.rows_from_results(lines, its)
    out = od / f"{split}.jsonl"
    out.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows),
                   encoding="utf-8")
    res = vlmeval.score(rows)
    res["model"], res["answered_items"], res["asked_items"] = rec["model"], len(rows), len(its)
    (od / f"{split}_score.json").write_text(json.dumps(res, indent=1))
    vol.commit()
    return {"answered": len(rows), "of": len(its), **res["headline_real_only"]}


LEDGER = "/data/budget/gemini_inr.json"     # the owner's Rs 800 Gemini credit (8 Oct 2026)


def _pending_usd() -> float:
    """Worst cases of submitted rounds not yet collected and billed: counted as spent."""
    import json
    return sum(json.loads(p.read_text()).get("reserved_usd", 0.0)
               for p in Path("/data/runs").glob("*/round_*.json")
               if not json.loads(p.read_text()).get("billed"))


@app.function(volumes={"/data": vol}, timeout=3 * 3600, memory=8192,
              secrets=[modal.Secret.from_name("gemini")])
def flagship_round(action: str = "submit", model: str = "gemini-3.1-pro-preview",
                   items: str = "/data/vlm/v6/items_eye2.jsonl", split: str = "test",
                   out_dir: str = "/data/runs/gem_pro31_rules", prompt: str = "rules",
                   max_output: int = 3000, est_in: int = 3500, start: int = 0, count: int = 0,
                   tag: int = 0, chunk: int = 300, stop_inr: float = 790.0):
    """One spending-controlled round of flagship questions through the Batch API (owner: Rs 800
    ceiling, not a rupee more). `submit`: of the split's items[start:start+count], takes only as
    many as fit under the ledger's stop line at their WORST case (est_in input tokens and the
    max_output cap, thinking included, at the batch price; rounds submitted but not yet billed
    count as spent), then uploads and starts them. `collect`: when finished, downloads the
    answers (free), records their real billed cost in the ledger once, and writes
    <split>_s<tag>.jsonl."""
    import json
    import sys
    sys.path.insert(0, "/root")
    from drishti_vision import flagship_batch as fb
    from drishti_vision import spend, vlmeval
    from drishti_vision.vlmdata import read_items
    led = spend.Ledger(LEDGER, limit_inr=800, stop_share=stop_inr / 800)
    od = Path(out_dir)
    od.mkdir(parents=True, exist_ok=True)
    rec_p = od / f"round_{split}_s{tag}.json"
    its = [i for i in read_items(items) if i.split == split]
    if action == "submit":
        if rec_p.exists():
            raise RuntimeError(f"{rec_p} exists: a round is never submitted twice")
        per = spend.usd(model, est_in, max_output, batch=True)
        pending = _pending_usd()
        room = (led.stop - led.spent_inr) / led.fx - pending
        sel = its[start:start + count] if count else its[start:]
        n = min(len(sel), int(room / per))
        if n <= 0:
            print(f"no room: spent Rs {led.spent_inr:.2f}, pending ${pending:.3f}", flush=True)
            return None
        sel = sel[:n]
        worst = n * per
        led.check(worst + pending, f"round {split} s{tag}")
        jobs = []
        for k in range(0, n, chunk):
            p = Path(f"/tmp/req_{split}_{tag}_{k}.jsonl")
            with open(p, "w", encoding="utf-8") as f:
                for it in sel[k:k + chunk]:
                    f.write(fb.request_line(it, Path("/data"), prompt=prompt,
                                            max_output=max_output) + "\n")
            name = f"nidhinetra-{prompt}-{split}-{tag}-{k}"
            jobs.append({"batch": fb.create(model, fb.upload(p, name), name),
                         "n": len(sel[k:k + chunk])})
        rec_p.write_text(json.dumps({"model": model, "split": split, "prompt": prompt,
                                     "items": items,
                                     "max_output": max_output, "ids": [i.id for i in sel],
                                     "jobs": jobs, "reserved_usd": worst, "billed": False},
                                    indent=1))
        vol.commit()
        print(f"submitted {n} items ({start}..{start + n - 1}); worst case Rs "
              f"{worst * led.fx:.2f}; ledger Rs {led.spent_inr:.2f}; next start {start + n}",
              flush=True)
        return {"n": n, "next_start": start + n, "worst_inr": worst * led.fx}
    rec = json.loads(rec_p.read_text())
    states, lines = [], []
    for j in rec["jobs"]:
        st = fb.status(j["batch"])
        state = st.get("metadata", {}).get("state") or st.get("state")
        states.append(state)
        resp = (st.get("response") or {}).get("responsesFile") or \
            (st.get("metadata", {}).get("output") or {}).get("responsesFile")
        if state == "BATCH_STATE_SUCCEEDED" and resp:
            lines += fb.download(resp)
    print(split, f"s{tag}", states, flush=True)
    if not all(s in ("BATCH_STATE_SUCCEEDED", "BATCH_STATE_FAILED", "BATCH_STATE_CANCELLED",
                     "BATCH_STATE_EXPIRED") for s in states):
        return {"states": states}
    ids = set(rec["ids"])
    # the round's own items file (8 Oct 2026: collecting against the default file matched only
    # 12 of 165 answers and under-recorded the cost)
    pool = [i for i in read_items(rec.get("items", items)) if i.split == split and i.id in ids]
    rows = fb.rows_from_results(lines, pool)
    if len(rows) < len(lines) - lines.count(""):
        print(f"WARNING: {len(lines)} answers downloaded, only {len(rows)} matched items",
              flush=True)
    actual = fb.batch_cost_usd(rows, rec["model"])
    prev = rec.get("actual_usd", 0.0) if rec["billed"] else 0.0
    if actual > prev + 1e-9:                   # never under-record: top up a short entry
        total = led.add(actual - prev, f"round {split} s{tag}: {len(rows)} answers"
                        + (" (correction)" if prev else ""))
        rec.update(billed=True, actual_usd=actual)
        rec_p.write_text(json.dumps(rec, indent=1))
    else:
        total = led.spent_inr
    (od / f"{split}_s{tag}.jsonl").write_text(
        "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
    vol.commit()
    res = vlmeval.score(rows) if rows else {"headline_real_only": {}}
    print(f"collected {len(rows)} of {len(ids)}; cost Rs {actual * led.fx:.2f}; ledger Rs "
          f"{total:.2f} of 800", flush=True)
    return {"answered": len(rows), "inr": actual * led.fx, "ledger_inr": total,
            "macro_f1": res["headline_real_only"].get("macro_f1")}


@app.function(volumes={"/data": vol}, timeout=900, secrets=[modal.Secret.from_name("gemini")])
def gemini_batches(cancel_running: bool = False):
    """Every batch job on the key (a free read), with its state and counts; with
    `cancel_running`, cancels any that are still pending or running."""
    import json
    import sys
    sys.path.insert(0, "/root")
    from drishti_vision import flagship_batch as fb
    body = json.loads(fb._req(f"{fb.API}/v1beta/batches?pageSize=100"))
    for b in body.get("operations", body.get("batches", [])):
        md = b.get("metadata", b)
        state = md.get("state")
        print(b.get("name"), md.get("displayName"), state, md.get("createTime"),
              json.dumps(md.get("batchStats", {})), flush=True)
        if cancel_running and state in ("BATCH_STATE_PENDING", "BATCH_STATE_RUNNING"):
            fb.cancel(b["name"])
            print("  cancelled", flush=True)


@app.function(volumes={"/data": vol}, timeout=900, secrets=[modal.Secret.from_name("gemini")])
def gemini_capcheck(model: str = "gemini-3.1-pro-preview", cap: int = 64):
    """Does maxOutputTokens bound the thinking too? One small Pro call that invites thinking,
    with a tiny cap; reserved at the model's full uncapped worst case (65,536 output tokens)."""
    import json
    import os
    import sys
    import urllib.request
    sys.path.insert(0, "/root")
    from drishti_vision import spend
    led = spend.Ledger(LEDGER, limit_inr=800)
    led.check(spend.usd(model, 200, 65536), "capcheck")
    body = {"contents": [{"role": "user", "parts": [{"text": (
        "Think step by step: how many prime numbers are there between 1 and 200? "
        "Reply with the number only.")}]}],
        "generationConfig": {"maxOutputTokens": cap, "temperature": 0}}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json",
                 "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    with urllib.request.urlopen(req, timeout=300) as r:      # noqa: S310
        out = json.loads(r.read().decode())
    u = out.get("usageMetadata", {})
    t_in, cand, th = (u.get("promptTokenCount", 0), u.get("candidatesTokenCount", 0),
                      u.get("thoughtsTokenCount", 0))
    cost = spend.usd(model, t_in, cand + th)
    total = led.add(cost, f"capcheck {model} cap {cap}: in {t_in} out {cand} thoughts {th}")
    vol.commit()
    fin = (out.get("candidates") or [{}])[0].get("finishReason")
    print(f"cap {cap}: answer tokens {cand} + thinking {th} = {cand + th} (finish {fin}); "
          f"{'BOUNDED' if cand + th <= cap else 'NOT BOUNDED'}; cost Rs "
          f"{cost * spend.INR_PER_USD:.4f}; ledger Rs {total:.4f}", flush=True)
    return {"bounded": cand + th <= cap, "thinking": th, "answer": cand}


@app.function(volumes={"/data": vol}, timeout=900, secrets=[modal.Secret.from_name("gemini")])
def gemini_check(ping: bool = True):
    """Free first: the state of every recorded batch job (status reads are not billed). Then, if
    `ping`, ONE tiny prompt (a few tokens on the cheapest priced model, output capped at 16
    tokens), priced at its worst case against the ledger before it is sent and recorded after."""
    import json
    import os
    import sys
    import urllib.error
    import urllib.request
    sys.path.insert(0, "/root")
    from drishti_vision import flagship_batch as fb
    from drishti_vision import spend
    for rec_p in sorted(Path("/data/runs").glob("gem_*batch/batch_*.json")):
        rec = json.loads(rec_p.read_text())
        for j in rec["jobs"]:
            try:
                st = fb.status(j["batch"])
                md = st.get("metadata", {})
                print(rec_p.parent.name, rec["split"], j["n"], md.get("state") or st.get("state"),
                      json.dumps(md.get("batchStats", {})), flush=True)
            except Exception as e:  # noqa: BLE001
                print(rec_p.parent.name, rec["split"], j["n"], "status error:", str(e)[:200],
                      flush=True)
    if not ping:
        return None
    led = spend.Ledger(LEDGER, limit_inr=800)
    model, cap = "gemini-3.8-flash", 16
    worst = spend.usd(model, 50, cap)
    led.check(worst, "ping")
    body = {"contents": [{"role": "user", "parts": [{"text": "Reply with the single word OK."}]}],
            "generationConfig": {"maxOutputTokens": cap, "temperature": 0,
                                 "thinkingConfig": {"thinkingLevel": "low"}}}
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        data=json.dumps(body).encode(), method="POST",
        headers={"Content-Type": "application/json",
                 "x-goog-api-key": os.environ["GEMINI_API_KEY"]})
    try:
        with urllib.request.urlopen(req, timeout=120) as r:      # noqa: S310
            out = json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        msg = e.read().decode(errors="replace")
        print("ping refused (not billed):", e.code, msg[:400], flush=True)
        return None
    u = out.get("usageMetadata", {})
    t_in = u.get("promptTokenCount", 0)
    t_out = u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)
    cost = spend.usd(model, t_in, t_out)
    total = led.add(cost, f"ping {model} in {t_in} out {t_out}")
    vol.commit()
    text = "".join(p.get("text", "") for p in out["candidates"][0]["content"]["parts"])
    print(f"ping OK: answer {text!r}; tokens in {t_in}, out {t_out}; cost ${cost:.6f} = "
          f"Rs {cost * spend.INR_PER_USD:.4f}; ledger total Rs {total:.4f} of 800", flush=True)
    return {"answer": text, "inr": cost * spend.INR_PER_USD, "ledger_inr": total}


def _score(adapter, out, items, split, base, limit, batch=8, real_only=False, max_side=512):
    import json
    import sys
    sys.path.insert(0, "/root")
    from drishti_vision import vlm, vlmeval
    from drishti_vision.vlmdata import read_items
    its = [i for i in read_items(items) if i.split == split and (i.real or not real_only)]
    its = its[:limit] if limit else its
    L = vlm.load(base, quant4=False, adapter=adapter or None, merge=True, max_side=max_side)
    Path(out).parent.mkdir(parents=True, exist_ok=True)

    # progress saved to the volume every few minutes, so a timeout or a stop keeps what was done
    rows = vlmeval.predict(L, its, Path("/data"), Path(out), log=_logger(), batch=batch)
    res = vlmeval.score(rows)
    Path(out.replace(".jsonl", "_score.json")).write_text(json.dumps(res, indent=1))
    vol.commit()
    return res["headline_real_only"]
