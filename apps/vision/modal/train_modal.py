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
       focus: str = "", real_only: bool = False):
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
        chosen = vlmrl.hard_prompts(rows, chosen)
    elif focus:
        chosen = vlmrl.focus_prompts(chosen, tuple(focus.split(",")))

    def log(s):                                # every 25 prompts: print and save to the volume
        print(s, flush=True)
        vol.commit()
    info = vlmrl.rl_fit(cfg, prompts=chosen, log=log)
    vol.commit()
    return {k: info[k] for k in ("prompts", "skipped_flat_groups", "minutes", "peak_gpu_gb")}


@app.function(gpu=GPU, volumes={"/data": vol}, timeout=3600)
def score(adapter: str = "", out: str = "/data/runs/base/test.jsonl",
          items: str = "/data/vlm/v1/items.jsonl", split: str = "test",
          base: str = "Qwen/Qwen3-VL-4B-Instruct", limit: int = 0, batch: int = 8,
          real_only: bool = False):
    return _score(adapter, out, items, split, base, limit, batch, real_only)


@app.function(gpu="L4", volumes={"/data": vol}, timeout=3 * 3600)
def score_l4(adapter: str = "", out: str = "/data/runs/base/test.jsonl",
             items: str = "/data/vlm/v1/items.jsonl", split: str = "test",
             base: str = "Qwen/Qwen3-VL-4B-Instruct", limit: int = 0, batch: int = 8,
             real_only: bool = False):
    """The same scoring on an L4 (24 GB, about a third of the A100's price an hour): scoring is
    one answer at a time, so the big card mostly waits. Resumable, like score."""
    return _score(adapter, out, items, split, base, limit, batch, real_only)


def _score(adapter, out, items, split, base, limit, batch=8, real_only=False):
    import json
    import sys
    sys.path.insert(0, "/root")
    from drishti_vision import vlm, vlmeval
    from drishti_vision.vlmdata import read_items
    its = [i for i in read_items(items) if i.split == split and (i.real or not real_only)]
    its = its[:limit] if limit else its
    L = vlm.load(base, quant4=False, adapter=adapter or None, merge=True)
    Path(out).parent.mkdir(parents=True, exist_ok=True)

    def log(s):                     # every 25 answers: print and save to the volume, so a timeout
        print(s, flush=True)        # or a stop keeps what was done (predict resumes from it)
        vol.commit()
    rows = vlmeval.predict(L, its, Path("/data"), Path(out), log=log, batch=batch)
    res = vlmeval.score(rows)
    Path(out.replace(".jsonl", "_score.json")).write_text(json.dumps(res, indent=1))
    vol.commit()
    return res["headline_real_only"]
