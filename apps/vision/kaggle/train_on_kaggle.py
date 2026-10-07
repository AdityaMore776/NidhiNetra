"""T148 on Kaggle's free GPU: the three model sizes of plan §7, each measured as plan §8 asks.

In a Kaggle notebook (GPU T4 x2 or P100, internet on for the first DINOv2 download):

  1. Add two private Kaggle datasets: this repo's apps/vision folder ("drishti-vision") and the
     tuned dataset made by `python -m drishti_vision build ...` ("drishti-progress-data").
  2. In a cell:
       !pip install -q -e /kaggle/input/drishti-vision
       !python /kaggle/input/drishti-vision/kaggle/train_on_kaggle.py \
            --data /kaggle/input/drishti-progress-data --out /kaggle/working/t148
  3. Download /kaggle/working/t148/results.json and put it in data/trial/results/ (T148).

Sizes (chosen on the calibration split, never on training data):
  probe   frozen DINOv2 + no attention between frames (a linear read-out of the features)
  head    frozen DINOv2 + the 2-layer joint-attention head (about 1.9 million weights)
  lora    the head + LoRA adapters on the backbone's last 4 blocks (about 0.1 million more)

Then the chosen size again for each leave-one-type-out fold (folds.json), tested on the held-out
material. Every run's train AUROC is kept beside its test AUROC: the gap is the overfitting measure.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import torch

from drishti_vision.stages import N_ALL
from drishti_vision.train import Store, TrainConfig, fit, measure

SIZES = {"probe": dict(layers=0, lora_blocks=0), "head": dict(layers=2, lora_blocks=0),
         "lora": dict(layers=2, lora_blocks=4)}


def run(name: str, data: str, out: Path, backbone: str, size, epochs: int, device: str,
        train_sites=None, eval_sites=None, test_split: str | None = "test", test_sites=None,
        **kw) -> dict:
    t0 = time.time()
    cfg = TrainConfig(data=data, out=str(out / name), backbone=backbone, size=size,
                      epochs=epochs, order_epochs=2, batch=32, lr=3e-4 if kw.get("lora_blocks")
                      else 1e-3, device=device, n_stages=N_ALL, workers=2,
                      train_sites=train_sites, eval_sites=eval_sites, **kw)
    model, info = fit(cfg)
    test = Store(data, sites=test_sites) if test_sites else Store(data, split=test_split)
    train = Store(data, sites=train_sites) if train_sites else Store(data, split="train")
    res = {"info": info, "test": measure(model, test, cfg),
           "train_auroc": measure(model, train, cfg, audits=False).get("auroc"),
           "minutes": round((time.time() - t0) / 60, 1)}
    res["gap"] = res["train_auroc"] - res["test"].get("auroc", float("nan"))
    print(name, json.dumps(res), flush=True)
    return res


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--backbone", default="dinov2_vitb14_reg")
    ap.add_argument("--size", default="224x308")
    ap.add_argument("--epochs", type=int, default=10)
    a = ap.parse_args()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    size = tuple(int(x) for x in a.size.split("x"))
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    results = {"backbone": a.backbone, "size": size, "device": device, "sizes": {}, "loto": {}}
    for name, kw in SIZES.items():
        results["sizes"][name] = run(name, a.data, out, a.backbone, size, a.epochs, device, **kw)
    best = max(results["sizes"],
               key=lambda n: results["sizes"][n]["info"].get("best_calib_auroc", 0))
    results["chosen"] = best
    folds = json.loads((Path(a.data) / "folds.json").read_text())["leave_one_type_out"]
    for material, f in folds.items():
        if not f["test"] or not f["train"]:
            continue
        cut = max(1, len(f["train"]) // 6)            # a sixth of training sites for calibration
        results["loto"][material] = run(
            f"loto-{material}", a.data, out, a.backbone, size, a.epochs, device,
            train_sites=f["train"][cut:], eval_sites=f["train"][:cut], test_sites=f["test"],
            **SIZES[best])
    (out / "results.json").write_text(json.dumps(results, indent=1, default=str))
    print(f"wrote {out / 'results.json'}")


if __name__ == "__main__":
    main()
