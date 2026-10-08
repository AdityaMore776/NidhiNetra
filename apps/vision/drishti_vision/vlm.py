"""The claim judge: Qwen3-VL with LoRA, its prompt, its answers, and its fine-tuning (T154).

One prompt is shared by training, measuring (vlmeval.py) and the engine's reader (T156), so what the
model learnt is exactly what it is asked. The answer is short JSON (vlmdata module docstring); the
verdict's probabilities come from the model's own next-token scores at the verdict's place, so they
can be calibrated and turned into "can't tell" when the model is unsure (plan T150 I10).

Fine-tuning: LoRA on the language model's linear layers, the vision encoder frozen (plan T150
I1/I7),
loss on the answer's tokens only. Runs on the owner's RTX 3070 Ti (8 GB): bf16 for 2B, 4-bit (QLoRA)
for 4B; the same code runs on a rented GPU (Modal) for bigger settings.
"""

from __future__ import annotations

import json
import math
import random
import re
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from drishti_vision.vlmdata import SYSTEM, VERDICTS, Item, user_prompt

MAX_SIDE = 512              # each photo is shrunk to this before the processor (<= 256 tokens)
ANSWER_KEYS = ("same_place", "stage_A", "stage_B", "permanent_change", "verdict", "reason")


def load_image(path: Path, max_side: int = MAX_SIDE):
    from PIL import Image
    im = Image.open(path).convert("RGB")
    w, h = im.size
    s = max_side / max(w, h)
    if s < 1:
        im = im.resize((max(32, round(w * s)), max(32, round(h * s))), Image.BICUBIC)
    return im


def jitter(im, rng: random.Random, p: float = 0.7):
    """Training only, every answer alike (plan T150 D1, D3): each photo on its own gets a random
    crop (70-100% of the side), a small rotation and a JPEG quality, as a hand-held phone would.
    Two photos of one moment are then never pixel-identical, so "identical photos" cannot stand in
    for "nothing was built"; the label never changes, as nothing is added or removed."""
    import io

    from PIL import Image
    if rng.random() > p:
        return im
    w, h = im.size
    s = rng.uniform(0.7, 1.0)
    cw, ch = int(w * s), int(h * s)
    x0, y0 = rng.randint(0, w - cw), rng.randint(0, h - ch)
    im = im.crop((x0, y0, x0 + cw, y0 + ch)).rotate(rng.uniform(-4, 4), resample=Image.BICUBIC,
                                                    expand=False)
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=rng.randint(55, 95))
    return Image.open(io.BytesIO(buf.getvalue())).convert("RGB")


def messages(item: Item | dict, answer: dict | None = None) -> list[dict]:
    it = item if isinstance(item, dict) else item.__dict__
    user = [{"type": "text", "text": "Photo A (last visit):"}, {"type": "image"},
            {"type": "text", "text": "Photo B (this visit):"}, {"type": "image"},
            {"type": "text", "text": user_prompt(it["work_type"], it["claim"], it["claim_kind"])}]
    out = [{"role": "system", "content": [{"type": "text", "text": SYSTEM}]},
           {"role": "user", "content": user}]
    if answer is not None:
        out.append({"role": "assistant",
                    "content": [{"type": "text", "text": json.dumps(answer, ensure_ascii=False)}]})
    return out


def answer_of(item: Item | dict) -> dict:
    t = (item if isinstance(item, dict) else item.__dict__)["target"]
    return {k: t[k] for k in ANSWER_KEYS}


_JSON = re.compile(r"\{.*\}", re.S)


def parse(text: str) -> dict | None:
    """The model's JSON answer, forgiving code fences and trailing words; None if unreadable."""
    m = _JSON.search(text)
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    v = str(d.get("verdict", "")).strip().lower().replace(" ", "_").replace("'", "")
    v = {"not_shown": "not_shown", "notshown": "not_shown", "cant_tell": "cant_tell",
         "can_tell": "cant_tell", "cannot_tell": "cant_tell", "shown": "shown"}.get(v)
    if v is None:
        return None
    d["verdict"] = v
    return d


@dataclass
class Loaded:
    model: object
    processor: object
    name: str
    device: str
    max_side: int = MAX_SIDE        # photos are shrunk to this (training used MAX_SIDE)


def load(name: str, quant4: bool = False, adapter: str | None = None,
         device: str = "cuda", merge: bool = False, max_side: int = MAX_SIDE) -> Loaded:
    """`merge`: fold the LoRA adapter into the weights (scoring only; same answers, about half the
    time a check, as the adapter's extra layers no longer run separately). Not for 4-bit."""
    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor
    kw = {"dtype": torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16}
    if quant4:
        from transformers import BitsAndBytesConfig
        kw["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=kw["dtype"])
        kw["device_map"] = {"": 0}
    model = AutoModelForImageTextToText.from_pretrained(name, **kw)
    if not quant4:
        model.to(device)
    proc = AutoProcessor.from_pretrained(name)
    proc.image_processor.size = {"shortest_edge": 64 * 64, "longest_edge": max_side * max_side}
    if adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, adapter)
        if merge and not quant4:
            model = model.merge_and_unload()
    model.eval()
    return Loaded(model, proc, name + (f"+{Path(adapter).name}" if adapter else "")
                  + (f"@{max_side}px" if max_side != MAX_SIDE else ""), device, max_side)


def _inputs(L: Loaded, item, root: Path | None, answer: dict | None = None, imgs=None):
    it = item if isinstance(item, dict) else item.__dict__
    if imgs is None:
        imgs = [load_image(root / it["image_a"], L.max_side),
                load_image(root / it["image_b"], L.max_side)]
    msgs = messages(item, answer)
    text = L.processor.apply_chat_template(msgs, tokenize=False,
                                           add_generation_prompt=answer is None)
    enc = L.processor(text=[text], images=imgs, return_tensors="pt")
    return enc, text


def shrink(im, max_side: int = MAX_SIDE):
    w, h = im.size
    s = max_side / max(w, h)
    if s < 1:
        from PIL import Image
        im = im.resize((max(32, round(w * s)), max(32, round(h * s))), Image.BICUBIC)
    return im


def judge_images(L: Loaded, img_a, img_b, work_type: str, claim: str, claim_kind: str = "reached",
                 max_new_tokens: int = 220) -> dict:
    """The same judgement on two PIL images (the engine's reader, T156)."""
    item = {"work_type": work_type, "claim": claim, "claim_kind": claim_kind}
    return judge(L, item, None, max_new_tokens,
                 imgs=[shrink(img_a.convert("RGB")), shrink(img_b.convert("RGB"))])


def judge(L: Loaded, item, root: Path | None, max_new_tokens: int = 220, imgs=None) -> dict:
    """Greedy answer + the verdict's probabilities at its place in the answer."""
    import torch
    enc, _ = _inputs(L, item, root, imgs=imgs)
    enc = enc.to(L.model.device)
    t0 = time.perf_counter()
    with torch.no_grad():
        out = L.model.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False)
    gen = out[0, enc["input_ids"].shape[1]:]
    text = L.processor.decode(gen, skip_special_tokens=True)
    secs = time.perf_counter() - t0
    ans = parse(text)
    probs = verdict_probs(L, enc, text) if ans is not None else None
    return {"text": text, "answer": ans, "probs": probs, "seconds": round(secs, 3),
            "new_tokens": int(gen.shape[0])}


def judge_batch(L: Loaded, items: list, root: Path, max_new_tokens: int = 220) -> list[dict]:
    """judge() for several items at once (left-padded, one generate call), so the GPU is not left
    waiting between the words of one answer. Greedy, as judge(); `seconds` is the batch's time
    shared out evenly. The verdict's probabilities come from each item's own prompt, as in
    judge()."""
    import torch
    tok = L.processor.tokenizer
    side = tok.padding_side
    imgs, texts = [], []
    for it in items:
        d = it if isinstance(it, dict) else it.__dict__
        imgs.append([load_image(root / d["image_a"], L.max_side),
                     load_image(root / d["image_b"], L.max_side)])
        texts.append(L.processor.apply_chat_template(messages(it), tokenize=False,
                                                     add_generation_prompt=True))
    tok.padding_side = "left"
    try:
        enc = L.processor(text=texts, images=imgs, return_tensors="pt", padding=True)
    finally:
        tok.padding_side = side
    enc = enc.to(L.model.device)
    t0 = time.perf_counter()
    with torch.no_grad():
        out = L.model.generate(**enc, max_new_tokens=max_new_tokens, do_sample=False)
    secs = (time.perf_counter() - t0) / len(items)
    n0 = enc["input_ids"].shape[1]
    res = []
    for k, it in enumerate(items):
        gen = out[k, n0:]
        text = L.processor.decode(gen, skip_special_tokens=True)
        ans = parse(text)
        probs = None
        if ans is not None:
            one, _ = _inputs(L, it, root, imgs=imgs[k])
            probs = verdict_probs(L, one.to(L.model.device), text)
        res.append({"text": text, "answer": ans, "probs": probs, "seconds": round(secs, 3),
                    "new_tokens": int((gen != tok.pad_token_id).sum())})
    return res


def _first_tokens(L: Loaded) -> dict[str, int]:
    tok = L.processor.tokenizer
    out = {}
    for v in VERDICTS:
        ids = tok.encode(v, add_special_tokens=False)
        out[v] = ids[0]
    if len(set(out.values())) != len(out):           # "not_shown" and "shown" must differ at once
        raise RuntimeError(f"verdict words share a first token: {out}")
    return out


def verdict_probs(L: Loaded, enc, generated: str) -> dict | None:
    """P(verdict) from the next-token scores right after '"verdict": "' in the model's own
    answer."""
    import torch
    cut = generated.find('"verdict"')
    if cut < 0:
        return None
    q = generated.find('"', generated.find(":", cut) + 1)
    if q < 0:
        return None
    prefix = generated[: q + 1]
    tok = L.processor.tokenizer
    pre_ids = torch.tensor([tok.encode(prefix, add_special_tokens=False)],
                           device=enc["input_ids"].device)
    n0 = enc["input_ids"].shape[1]
    ids = torch.cat([enc["input_ids"], pre_ids], 1)
    att = torch.ones_like(ids)
    kw = {}
    for k, v in enc.items():
        if k in ("input_ids", "attention_mask"):
            continue
        if torch.is_tensor(v) and v.dim() == 2 and v.shape[1] == n0:   # per-token types: text = 0
            v = torch.cat([v, torch.zeros_like(pre_ids, dtype=v.dtype)], 1)
        kw[k] = v
    with torch.no_grad():
        logits = L.model(input_ids=ids, attention_mask=att, **kw).logits[0, -1].float()
    first = _first_tokens(L)
    sel = torch.stack([logits[first[v]] for v in VERDICTS])
    p = torch.softmax(sel, 0).cpu().numpy()
    return {v: float(x) for v, x in zip(VERDICTS, p, strict=True)}


# ---- fine-tuning --------------------------------------------------------------------------------

@dataclass
class TrainConfig:
    base: str
    items: str
    root: str
    out: str
    quant4: bool = False
    rank: int = 16
    alpha: int = 32
    dropout: float = 0.05
    lr: float = 1e-4
    epochs: float = 2.0
    accum: int = 8
    warmup: float = 0.05
    max_items: int = 0
    seed: int = 0
    edited_share: float = 0.2       # at most this share of training items may be edited (owner)
    jitter: bool = True             # each photo cropped / turned / re-saved on its own (jitter())
    real_only: bool = False
    eval_every: int = 200
    grad_ckpt: bool = True          # recompute activations (needed on 8 GB; off on a 40 GB card)


def training_items(path: str, cfg: TrainConfig) -> list[dict]:
    """Training split only, edited items capped at `edited_share` (owner's rule)."""
    rows = [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines()
            if line.strip()]
    rows = [r for r in rows if r["split"] == "train"]
    rng = random.Random(cfg.seed)
    real = [r for r in rows if r.get("real", True)]
    edited = [] if cfg.real_only else [r for r in rows if not r.get("real", True)]
    cap = (int(cfg.edited_share / (1 - cfg.edited_share) * len(real))
           if cfg.edited_share < 1 else 10**9)
    rng.shuffle(edited)
    chosen = real + edited[:cap]
    rng.shuffle(chosen)
    if cfg.max_items:
        chosen = chosen[: cfg.max_items]
    return chosen


def fit(cfg: TrainConfig, log=print) -> dict:
    import torch
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    torch.manual_seed(cfg.seed)
    random.seed(cfg.seed)
    jit_rng = random.Random(cfg.seed + 1)
    L = load(cfg.base, quant4=cfg.quant4)
    model = L.model
    if cfg.quant4:
        model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=cfg.grad_ckpt)
    elif cfg.grad_ckpt:
        model.gradient_checkpointing_enable()
        model.enable_input_require_grads()
    targets = r"^(?!.*visual).*\.(q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)$"
    model = get_peft_model(model, LoraConfig(r=cfg.rank, lora_alpha=cfg.alpha,
                                             lora_dropout=cfg.dropout, target_modules=targets,
                                             task_type="CAUSAL_LM"))
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    rows = training_items(cfg.items, cfg)
    root = Path(cfg.root)
    steps = math.ceil(len(rows) * cfg.epochs / cfg.accum)
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=cfg.lr,
                            weight_decay=0.0)
    warm = max(1, int(cfg.warmup * steps))
    def lr_at(s: int) -> float:
        return min(1.0, (s + 1) / warm) * 0.5 * (1 + math.cos(math.pi * min(1.0, s / steps)))

    sched = torch.optim.lr_scheduler.LambdaLR(opt, lr_at)
    log(f"{len(rows)} training items ({sum(not r.get('real', True) for r in rows)} edited), "
        f"{steps} optimiser steps, {trainable / 1e6:.2f} M trainable weights")
    model.train()
    out = Path(cfg.out)
    out.mkdir(parents=True, exist_ok=True)
    history, step, seen, t0, run = [], 0, 0, time.time(), []
    order = []
    while len(order) < steps * cfg.accum:
        o = rows[:]
        random.shuffle(o)
        order += o
    order = order[: steps * cfg.accum]
    for i, r in enumerate(order):
        imgs = [load_image(root / r["image_a"]), load_image(root / r["image_b"])]
        if cfg.jitter:
            imgs = [jitter(im, jit_rng) for im in imgs]
        prompt_text = L.processor.apply_chat_template(messages(r), tokenize=False,
                                                      add_generation_prompt=True)
        full_text = L.processor.apply_chat_template(messages(r, answer_of(r)), tokenize=False,
                                                    add_generation_prompt=False)
        enc = L.processor(text=[full_text], images=imgs, return_tensors="pt")
        n_prompt = len(L.processor(text=[prompt_text], images=imgs,
                                   return_tensors="pt")["input_ids"][0])
        labels = enc["input_ids"].clone()
        labels[:, :n_prompt] = -100
        enc = {k: v.to(model.device) for k, v in enc.items()}
        with torch.autocast("cuda", dtype=torch.bfloat16 if torch.cuda.is_bf16_supported()
                            else torch.float16):
            loss = model(**enc, labels=labels.to(model.device)).loss / cfg.accum
        loss.backward()
        run.append(loss.item() * cfg.accum)
        seen += 1
        if (i + 1) % cfg.accum == 0:
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            opt.step()
            sched.step()
            opt.zero_grad(set_to_none=True)
            step += 1
            if step % 10 == 0 or step == steps:
                avg = float(np.mean(run[-cfg.accum * 10:]))
                history.append({"step": step, "loss": round(avg, 4),
                                "lr": sched.get_last_lr()[0],
                                "minutes": round((time.time() - t0) / 60, 1)})
                log(f"step {step}/{steps} loss {avg:.4f} "
                    f"({(time.time() - t0) / 60:.1f} min, peak GPU "
                    f"{torch.cuda.max_memory_allocated() / 2**30:.2f} GB)")
            if step % cfg.eval_every == 0:
                model.save_pretrained(out / f"step{step}")
    model.save_pretrained(out / "final")
    info = {"config": cfg.__dict__, "items": len(rows), "steps": steps, "history": history,
            "minutes": round((time.time() - t0) / 60, 1),
            "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2),
            "trainable_m": round(trainable / 1e6, 2)}
    (out / "train_info.json").write_text(json.dumps(info, indent=1))
    return info
