# T147–T148 on your own PC, with Claude Code

**Owner (7 Oct 2026):** "if I had to run this on my PC instead of this cloud session, would it be better, write a plan
for if this was run on my pc using claude code, with access to all things it gives, if it's better."

## 1. Is it better? Yes for the data; for training only with an NVIDIA GPU

| | The cloud session (7 Oct) | Your PC with Claude Code |
|---|---|---|
| Internet | YouTube, Wikimedia, Hugging Face, Kaggle and the PyTorch download site were refused (they can be allowed in the environment's settings) | whatever your connection reaches |
| GPU | none | yours, if it is NVIDIA |
| Disk | about 20 GB, wiped when the session ends | your own disk; plan for 50–100 GB |
| Long runs | the session can end; everything must be pushed first | can run overnight |
| Your own phone videos | must be uploaded somewhere first | copied straight from the phone |
| Shell | Linux | Windows + PowerShell (AGENTS.md §9 traps apply) |

**Verdict, part by part:**

| Part | Best place | Why |
|---|---|---|
| T147, collecting and building the dataset | **your PC** | open internet, room for the videos, your phone's footage, nothing wiped |
| T148, training | **your PC if it has an NVIDIA GPU**, else **Kaggle** (free, 16 GB GPU, about 30 h a week) | a CPU trains the DINOv2 model far too slowly; AMD and Intel GPUs are not used by this code |
| Writing and changing code | either | the cloud session did all of T146 |

The rest of this plan assumes your PC for T147, and your GPU or Kaggle for T148.

## 2. Before you start

**Decisions only you can make** (the code refuses these until you do; plan T146 §4.1):
1. **YouTube:** may Creative Commons (CC BY) videos be downloaded? YouTube's own terms are separate from the CC
   licence. If yes, `fetch` is run with `--allow-youtube`.
2. **Non-commercial and no-derivatives licences** (CC BY-NC, CC BY-ND): allowed or not.
3. **Filming real works:** which teammates film which local works each month, with the site's permission.

**On the PC** (check each with the command beside it, in PowerShell):

| Need | Check |
|---|---|
| Windows 10 or 11, Git for Windows | `git --version` |
| Python 3.11 or 3.12 | `py -3.12 --version` |
| Claude Code | install: `irm https://claude.ai/install.ps1 \| iex`, then `claude --version` |
| 50–100 GB free, **not** inside a OneDrive-synced folder (syncing gigabytes of video slows everything) | `Get-PSDrive C` |
| An NVIDIA GPU (optional) | `nvidia-smi` (shows the GPU and its memory; "not recognized" means none) |
| A Kaggle account, phone-verified (needed for its free GPU) | kaggle.com → Settings |
| A YouTube Data API key (only for searching YouTube; free: 10,000 units a day, a search costs 100, so about 100 searches a day) | Google Cloud console → APIs → YouTube Data API v3 → Credentials |

## 3. The steps

Start Claude Code in the repo folder (`claude`) and give it this plan: "Follow docs/plans/T147-run-on-your-pc.md, step
by step. Stop and ask me at every step marked YOU." Claude Code reads AGENTS.md itself (`/start` runs the usual
session start).

### Step 0: set up (Claude Code, about 20 minutes)

```powershell
git checkout main; git pull
git checkout -b <your-github-user>/T147-collect-videos
cd apps\vision
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -e ".[dev]"
```

Then PyTorch:
- **With an NVIDIA GPU:** use the install command that pytorch.org's "Get started" page gives for Windows + pip +
  CUDA.
- **Without one:** `.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu`.

Check:

```powershell
.venv\Scripts\python.exe -m pytest -q       # 53 tests, as in the cloud
.venv\Scripts\python.exe -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'CPU')"
```

### Step 1: prove the machine end to end on synthetic data (Claude Code, under an hour)

```powershell
.venv\Scripts\python.exe ..\..\data\trial\vision_synth_trial.py --seeds 4 --epochs 2
```

Its numbers should look like `data/trial/results/vision_synth_trial.txt` (a smaller run, so a little lower). With a
GPU, Claude Code also runs one epoch with the real backbone, to download DINOv2 and **measure the GPU memory** it
needs (`torch.cuda.max_memory_allocated()`): that number, not a guess, decides the batch size and whether LoRA fits.

### Step 2: the list of videos (YOU decide, Claude Code does the legwork)

The goal (T147):
- about 150 sites, at least 30 of them Indian public works;
- 5+ work types, with at least 20 roads or drains (the synthetic trial found roads the hardest type);
- only still-camera timelapses, or the team's own fixed-viewpoint monthly films.

| Source | Claude Code does | You do |
|---|---|---|
| Your team's own films | copies them from the phones into `apps\vision\videos\`, writes manifest rows (`licence: own`) | film monthly from fixed spots; get each site's permission |
| YouTube CC (if you allowed it) | `$env:YOUTUBE_API_KEY="..."; .venv\Scripts\python.exe -m drishti_vision search "house construction timelapse" --max 50`, in English and Hindi ("मकान निर्माण टाइमलैप्स", "CC road construction timelapse", "drain construction timelapse"); keeps the candidates in a file | open each candidate for 30 seconds: real construction, a still camera, the work type and material right; keep or drop |
| Wikimedia Commons, university cameras | finds them and writes rows with the licence each page states | check the licence |

Every kept row goes into `apps\vision\manifest.jsonl`, the one data file that enters git. Then:

```powershell
.venv\Scripts\python.exe -m drishti_vision check manifest.jsonl     # must say 0 with problems
```

### Step 3: download and build the dataset (Claude Code; hours, can run overnight)

```powershell
.venv\Scripts\python.exe -m drishti_vision fetch manifest.jsonl --dest videos   # add --allow-youtube only if you said yes
.venv\Scripts\python.exe -m drishti_vision build manifest.jsonl --videos videos --out data --device cuda   # or --device cpu
```

Notes:
- **Speed:** `build` uses DINOv2 for the teacher. On a GPU that takes minutes; on a CPU, hours. With no GPU,
  `--backbone handcrafted` is a weaker but quick fallback.
- **Sleep:** set Windows not to sleep while plugged in, for long runs.
- **Results:** `data\card.md` (pairs by split and type, licences, thresholds) goes into the PR. The frames stay out
  of git (`apps/vision/data/` and `videos/` are in .gitignore).

### Step 4: check the labels by eye (Claude Code builds a viewer; YOU look)

Not built yet:
- **The pair viewer:** Claude Code writes a small script that makes an HTML page per work type. It shows 50 random
  pairs with the teacher's progress patches outlined.
- **Your part:** go through them and mark each right or wrong. The share right is recorded in FINDINGS (plan T146
  §5.3). If a type falls below about 9 in 10, stop and fix that type before training.
- **The stage page:** the same viewer shows every 10th frame of a test shot with its number. You note the frame
  where each stage begins, into `marks.jsonl`, and `build` is re-run with `--marks marks.jsonl`.

### Step 5: train (your GPU, or Kaggle)

**With an NVIDIA GPU** (Claude Code; use the batch size step 1 measured):

```powershell
.venv\Scripts\python.exe kaggle\train_on_kaggle.py --data data --out runs\t148
```

The script runs anywhere; it uses the GPU when it finds one.

**Without one:** Claude Code zips `apps\vision` and `data`. YOU upload both to Kaggle as two private datasets and run
the notebook cell written at the top of `kaggle/train_on_kaggle.py`. Then download `results.json`.

Optional, for a CPU-only PC: Claude Code can add **feature caching** to `train.py` (the backbone is frozen, so each
frame's features can be computed once, with a few augmented copies). The head then trains in minutes even on a CPU.
That is a new task to add to TASKS first.

### Step 6: record and share (Claude Code)

- `results.json` goes into `data/trial/results/`.
- **FINDINGS "T148":** the plan T146 §8.1 table against its targets, the train-vs-test gaps, and the
  leave-one-type-out folds.
- A log entry, then a PR (AGENTS.md §5–6).

## 4. Working with Claude Code on the PC

- **Permissions:**
  - let it run Python, git and the pipeline's commands without asking each time;
  - keep asking for anything that downloads in bulk, deletes, or pushes.
- **Long runs:** ask it to run them in the background and report when they finish. It reads the log rather than
  waiting.
- **Never in git:**
  - videos, frames, the built dataset;
  - API keys (keep them in `$env:` variables, never in a file in the repo);
  - faces from your own films. The engine's `video/reader.blur_faces` blurs them before any frame is kept outside
    the PC.
- **Windows traps** (AGENTS.md §9):
  - PowerShell `$env:VAR="value"`, not `VAR=value`;
  - `.venv\Scripts\python.exe`;
  - never patch code through a shell heredoc.
- **One task at a time:** claim T147 on GitHub before starting (AGENTS.md §3). It is a `human-task`: your part is
  the decisions in §2, the checks in step 2 and the looking in step 4.

## 5. What it costs

Nothing but time and disk: the YouTube API's free quota, Kaggle's free GPU, and open-source code and models. A paid
GPU or a paid API would be the owner's decision (AGENTS.md rule 10).

## 6. What could go wrong

| Risk | What to do |
|---|---|
| Few still-camera timelapses survive (`build` drops moving shots) | look for "fixed camera", "site camera", "webcam timelapse"; film your own |
| Too few Indian works | start filming now: monthly footage takes months to show change |
| The GPU runs out of memory | the batch size from step 1's measurement; drop LoRA; or Kaggle |
| A type scores far below the others | more of that type before training (the synthetic trial's road result) |
| Licences unclear on a video | leave it out; the manifest refuses anything not on the allow-list |
