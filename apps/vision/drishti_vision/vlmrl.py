"""GRPO with checkable rewards for the claim judge (plan T150 §6.5, block I3; task T154).

After fine-tuning (vlm.fit) the model tries G answers per question; each answer is scored by rules
(no reward model, nothing to game):

    R = 0.1 x format + 0.7 x verdict + 0.2 x stage

    verdict reward          answer: shown   not_shown   cant_tell
      truth shown                   +1      -1          -0.2
      truth not_shown               -1 *    +1          -0.2       * -1.5 on a no-progress pair
      truth cant_tell               -1      -0.5        +1           (being fooled costs most)
    stage   = share of stage_A / stage_B named right (where the truth names one)
    format  = 1 if the answer is readable JSON with a verdict

Each answer's advantage is its reward minus the group's mean, over the group's spread (GRPO). The
update is on-policy (one step per group), so the probability ratio is 1 and no clipping is needed;
no KL term (as in DAPO), a small learning rate instead. Groups whose answers all score the same
carry
no signal and are skipped. Prompts come from the TRAINING split only, preferring items the
fine-tuned
model gets wrong or is unsure of (H3).
"""

from __future__ import annotations

import json
import math
import random
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from drishti_vision import vlm
from drishti_vision.vlmdata import NO_PROGRESS_TRICKS

VERDICT_REWARD = {
    "shown": {"shown": 1.0, "not_shown": -1.0, "cant_tell": -0.2},
    "not_shown": {"shown": -1.0, "not_shown": 1.0, "cant_tell": -0.2},
    "cant_tell": {"shown": -1.0, "not_shown": -0.5, "cant_tell": 1.0},
}
FOOLED = -1.5


def reward(text: str, item: dict) -> dict:
    a = vlm.parse(text)
    t = item["target"]
    if a is None:
        return {"total": -1.0, "format": 0.0, "verdict": -1.0, "stage": 0.0}
    v = VERDICT_REWARD[t["verdict"]][a["verdict"]]
    fooled = (t["verdict"] == "not_shown" and a["verdict"] == "shown"
              and item["trick"] in NO_PROGRESS_TRICKS)
    if fooled:
        v = FOOLED
    named = [k for k in ("stage_A", "stage_B") if t.get(k) not in (None, "unknown")]
    right = sum(str(a.get(k, "")).strip().lower() == t[k] for k in named)
    st = right / len(named) if named else 0.0
    w_stage = 0.2 if named else 0.0
    total = 0.1 * 1.0 + (0.7 + 0.2 - w_stage) * v + w_stage * st
    return {"total": total, "format": 1.0, "verdict": v, "stage": st}


@dataclass
class RLConfig:
    base: str
    adapter: str                 # the fine-tuned (SFT) adapter to start from
    items: str
    root: str
    out: str
    quant4: bool = True
    group: int = 4
    temperature: float = 0.9
    lr: float = 5e-6
    prompts: int = 1500
    max_new_tokens: int = 160
    seed: int = 0
    edited_share: float = 0.2
    save_every: int = 250


def rl_fit(cfg: RLConfig, prompts: list[dict] | None = None, log=print) -> dict:
    import torch
    from peft import PeftModel
    torch.manual_seed(cfg.seed)
    rng = random.Random(cfg.seed)
    L = vlm.load(cfg.base, quant4=cfg.quant4)
    model = PeftModel.from_pretrained(L.model, cfg.adapter, is_trainable=True)
    model.gradient_checkpointing_enable()
    model.enable_input_require_grads()
    L.model = model
    if prompts is None:
        tc = vlm.TrainConfig(base=cfg.base, items=cfg.items, root=cfg.root, out=cfg.out,
                             edited_share=cfg.edited_share, seed=cfg.seed)
        prompts = vlm.training_items(cfg.items, tc)
    rng.shuffle(prompts)
    prompts = prompts[: cfg.prompts]
    opt = torch.optim.AdamW([p for p in model.parameters() if p.requires_grad], lr=cfg.lr)
    root, out = Path(cfg.root), Path(cfg.out)
    out.mkdir(parents=True, exist_ok=True)
    hist, t0, skipped = [], time.time(), 0
    dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
    for k, item in enumerate(prompts):
        model.eval()
        enc, _ = vlm._inputs(L, item, root)
        enc = {kk: v.to(model.device) for kk, v in enc.items()}
        n0 = enc["input_ids"].shape[1]
        with torch.no_grad():
            gen = model.generate(**enc, do_sample=True, temperature=cfg.temperature, top_p=0.95,
                                 max_new_tokens=cfg.max_new_tokens,
                                 num_return_sequences=cfg.group)
        texts = [L.processor.decode(g[n0:], skip_special_tokens=True) for g in gen]
        rs = [reward(t, item) for t in texts]
        r = np.array([x["total"] for x in rs])
        flat = r.std() < 1e-6
        hist.append({"prompt": k, "mean_reward": float(r.mean()), "flat": bool(flat),
                     "verdict_right": float(np.mean([x["verdict"] > 0 for x in rs]))})
        if flat:                    # every try scored the same: nothing to learn from this one
            skipped += 1
        else:
            _update(model, L, enc, gen, n0, r, cfg, opt, dtype)
        # progress and checkpoints on schedule, whether or not this prompt was skipped (a
        # well-tuned model skips most prompts; logging only after updates left a run silent)
        if (k + 1) % 25 == 0:
            last = hist[-25:]
            log(f"{k + 1}/{len(prompts)} reward {np.mean([h['mean_reward'] for h in last]):.3f} "
                f"verdict right {np.mean([h['verdict_right'] for h in last]):.2f} "
                f"skipped {skipped} ({(time.time() - t0) / 60:.1f} min, "
                f"peak {torch.cuda.max_memory_allocated() / 2**30:.2f} GB)")
        if (k + 1) % cfg.save_every == 0:
            model.save_pretrained(out / f"rl{k + 1}")
    model.save_pretrained(out / "final")
    info = {"config": cfg.__dict__, "prompts": len(prompts), "skipped_flat_groups": skipped,
            "minutes": round((time.time() - t0) / 60, 1), "history": hist[-200:],
            "peak_gpu_gb": round(torch.cuda.max_memory_allocated() / 2**30, 2)}
    (out / "rl_info.json").write_text(json.dumps(info, indent=1))
    return info


def _update(model, L, enc, gen, n0, r, cfg, opt, dtype) -> None:
    """One GRPO step on a group: each try's log-probability pushed by its advantage."""
    import torch
    adv = (r - r.mean()) / (r.std() + 1e-4)
    model.train()
    opt.zero_grad(set_to_none=True)
    for g, a in zip(gen, adv, strict=True):
        comp = g[n0:]
        comp = comp[comp != L.processor.tokenizer.pad_token_id]
        if comp.numel() == 0:
            continue
        ids = torch.cat([enc["input_ids"][0], comp])[None]
        kw = {}
        for kk, v in enc.items():
            if kk in ("input_ids", "attention_mask"):
                continue
            if torch.is_tensor(v) and v.dim() == 2 and v.shape[1] == n0:
                v = torch.cat([v, torch.zeros((1, comp.numel()), dtype=v.dtype,
                                              device=v.device)], 1)
            kw[kk] = v
        with torch.autocast("cuda", dtype=dtype):
            logits = model(input_ids=ids, attention_mask=torch.ones_like(ids), **kw).logits
        lp = torch.log_softmax(logits[0, n0 - 1:-1].float(), -1)
        tok_lp = lp.gather(1, comp[:, None]).squeeze(1)
        loss = -(float(a) * tok_lp.mean()) / cfg.group
        loss.backward()
    torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
    opt.step()


def focus_prompts(items: list[dict], tricks: tuple[str, ...], keep_other: float = 0.3,
                  seed: int = 0) -> list[dict]:
    """Training items of the tricks the test showed to be weak (all of them), plus `keep_other`
    as many of the rest so the model does not forget them; shuffled. A cheap stand-in for
    hard_prompts when scoring the whole training split is not worth its cost."""
    rng = random.Random(seed)
    focus = [r for r in items if r["trick"] in tricks]
    rest = [r for r in items if r["trick"] not in tricks]
    rng.shuffle(rest)
    out = focus + rest[: math.ceil(keep_other * len(focus))]
    rng.shuffle(out)
    return out


def hard_prompts(pred_rows: list[dict], items: list[dict], keep_easy: float = 0.2,
                 seed: int = 0) -> list[dict]:
    """H3: the training items the fine-tuned model got wrong or was unsure of (conf < 0.8), plus a
    share of easy ones so the model does not forget them."""
    by = {r["id"]: r for r in pred_rows}
    hard, easy = [], []
    for it in items:
        r = by.get(it["id"])
        if r is None:
            continue
        wrong = r["pred"] != r["truth"]
        unsure = (r.get("conf") or 0) < 0.8
        (hard if wrong or unsure else easy).append(it)
    rng = random.Random(seed)
    rng.shuffle(easy)
    return hard + easy[: math.ceil(keep_easy * len(hard))]
