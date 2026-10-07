# T150: A small vision-language model that can't be fooled about site progress

**Owner (7 Oct 2026):** "read the MPLADS hackathon project repo … look at everything related to fine tuning a vision
language model for site progress … read research papers from Arxiv like ProgressLM, LLaVA, Qwen and similar … plan
data ingestion … find data augmentation, or rather techniques we can use to create a highly curated dataset … a small,
rich dataset … give me the building blocks of choices … along with your own highly researched and optimized data set
creation plan … it becomes a fine tuned model that beats the benchmark against top flagship models on something …
small research paper worthy."

**Decisions the owner made on 7 Oct 2026 (do not re-ask):**

| Question | Answer |
|---|---|
| What must the model be best at? | **Track A, now:** not fooled by staged sites, light or camera angle, and nearly free. **Track B, next:** the same accuracy as flagship models at 1/100 of the cost. |
| Compute | **Free only for now:** the owner's RTX 3070 Ti (8 GB) and Kaggle's free GPU. A big GPU may come later. |
| Sources allowed | Government stage photos (MGNREGA, PMAY-G, PMGSY), **YouTube Creative Commons (CC BY) timelapses**, open datasets, Wikimedia, Kaggle, GitHub and anywhere else with a clear licence. The team's own monthly films are not part of this round. |
| Deliverable | This document, plus a private web page for mixing and matching the building blocks. |

This answers T147's open question for YouTube: **CC BY may be downloaded.** Non-commercial (NC) and no-derivatives (ND)
licences stay refused until the owner says otherwise.

**About AGENTS.md rule 8 ("no competitor talk").** The flagship models here are **benchmark baselines**, the way any
model paper reports them. They are not rival teams. This is an internal planning document. Anything judges see (deck,
README, app) follows rule 8 as before: the comparison appears only on the deck's final References slide.

**About rule 3 ("only measured numbers").** Every figure below is one of three things:
- a published result, with its paper linked;
- a fact measured in this repo (named with its file);
- a **target or rough estimate**, labelled as such.

Nothing here is a DRISHTI result yet.

**The owner's data rules (7 Oct 2026, after approving this plan; these override anything below):**
1. **The test set is real, unedited photos only**, from districts never used in training. No synthetic, pasted,
   relit, darkened or blocked image ever counts in a headline number; edited items are scored apart.
2. **"Progress" only where progress is certain.** The work must add visible structure (roads, buildings, drains,
   walls, dug ponds; never playgrounds, levelling or plantation). The before → after photos must also differ more than
   the asset's own two same-moment photos do, and by at least a fixed floor (`apps/vision/drishti_vision/change.py`;
   margins set by eye on real assets).
3. **Hard examples on purpose:** real "busy site, no progress" pairs (the two photos of one moment during the work,
   often with workers), the same work claimed twice, photos in reverse order, and a clearly different place.
4. **Synthetic edits only in training, and kept honest:**
   - at most 20% of training items;
   - every edit goes into both answers (pasted people and new light also go into real progress pairs labelled
     "shown"), so an edit can never give the answer away;
   - no drawn or rendered 2D/3D scenes (T146's `synth.py`) at all;
   - an edit block stays only if switching it off makes the model worse on the real test set (ablation, T154).

These are enforced in code and tested (`apps/vision/tests/test_vlm_data.py`).

## Status (8 Oct 2026)

| Task | State |
|---|---|
| T151 source probes | **Done.** See the list below. |
| T152 collect | **Running:** MGNREGA, polite pace (~50 assets an hour); 250 timelapses downloading |
| T153 label and curate | Built: `vlmdata.py` (claim ladder, certainty, planted tricks), `change.py`, `cutouts.py`. Pilot card: 154 items from 12 assets. |
| T154 train | Built and smoke-tested on the RTX 3070 Ti: `vlm.py` (LoRA fine-tuning: 2B in bf16 at 5.7 GB, 4B in 4-bit at 6.3 GB), `vlmrl.py` (GRPO), `modal/train_modal.py` (the owner's Modal credit, hard timeouts) |
| T155 benchmark | Built: `vlmeval.py`. Headline on real photos only, with bootstrap intervals by asset. |
| T156 reader | Built: `VLMReader` in `site_progress/readers.py`, behind `DRISHTI_VLM_ADAPTER`, 8 engine tests |

**What T151 found:**
- **S1 GeoMGNREGA works.** The public map (Bhuvan BHUGRAM) answers WMS GetFeatureInfo with asset records. The asset
  page (`get_details.php`) lists two photos for each stage: 1 before, 2 during, 3 after. In the 12-asset pilot (Jaunpur),
  12 of 12 had all three stages.
- **Bulk export is switched off** (WFS disabled), and the compressed photo copies answer 403. So only the clicks the
  public page makes are used: about one asset a minute.
- **Stage labels need the certainty check.** One "before" photo already showed a (different) building, and the
  during photos often look finished.
- **S3 PMGSY** (`omms.nic.in`) does not answer from the owner's PC.
- **S5 YouTube:** 250 CC BY timelapses found with 20 queries, each licence read from its own watch page. AI-made,
  miniature and game titles are dropped.

---

## 0. In plain words

- **What we build:** a small open model (Qwen3-VL, 4 billion parameters) taught one job. It looks at last month's and this month's
  photo of the same spot, reads the agency's claim ("walls up to lintel level"), and says **shown / not shown / can't
  tell**, with a short reason and where it looked.
- **What it must be best at:** **not being fooled.** Big models like a busy-looking site. Bring in workers, a mixer and
  a pile of bricks on filming day, and they tend to say "progress". Our model is trained on exactly those tricks, with
  labels that come from **what happened later** (did that place ever go back to how it was?), never from how busy it looks.
- **Why a small model can win:** published work shows it again and again on narrow jobs:
  - a 3B model beat GPT-5 at judging task progress (ProgressLM);
  - a fine-tuned 7B model beat GPT-4o and Gemini on before/after satellite questions (TEOChat);
  - flagship models are near chance at telling which way time runs.
- **What it costs:** the data and training use free tools and free GPUs. Each check then runs on the owner's PC for about ₹0.
- **How we prove it:** a test set of about 800 photo pairs from sites and districts the model never saw, labelled by people,
  with separate scores for each trick. The rules for "we won" and "we stop" are written down **before** training (§7).
- **What is not certain:**
  - whether the government photo portals let us download their photos (to be probed first);
  - whether free GPUs are enough for the second training stage (kept small on purpose).

---

## 1. Where it fits

- **Site Progress** (T120 §9.4) runs six checks on each monthly video. Only **check 6, "does it show the claim?"**, needs a
  vision-language model.
  - Today check 6 uses `GeminiReader` (Gemini free tier, capped at 200 calls a day) or the CLIP `ZeroShotReader`.
  - CLIP names things but "cannot count, measure or read a sentence like 'roof slab cast'" (`readers.py`).
- **T146** (`apps/vision/`, [plan](T146-site-progress-vision.md), in PR #120 until it merges) is a DINOv2 "hindsight
  teacher → two-frame student" pipeline. It answers **check 5** ("what changed, and where"), and is measured on synthetic
  sites only.
- **This model complements T146; it does not replace it:**
  - T146's code becomes the **data engine**: still-camera shots, alignment, date-stamp and people masks, the hindsight
    labels, and splits by site;
  - T146's DINOv2 student stays the cheap **"where did it change" map**;
  - the new model is the **claim judge** for check 6. It replaces the Gemini dependency, and it speaks: verdict, stage,
    reason, can't tell.
- **The output plugs in as a new reader.** It uses `readers.py`'s own vocabulary (`VERDICTS = ("shown", "not_shown", "cant_tell")`):
  - it is run offline, cached by photo hash;
  - it stays a note, never counted, until real visits pass T120 §14 (AGENTS.md rule 4).

---

## 2. What the research says

| Paper | What it found | What we take |
|---|---|---|
| **ProgressLM** (ACL 2026) [arXiv 2601.15224](https://arxiv.org/abs/2601.15224) | Qwen2.5-VL-3B; LoRA rank 8 SFT on 25K examples whose reasoning was written by a 72B model **given the right answer**; then GRPO on 20K more (reward weights format 1 : step 6 : score 3). It beat GPT-5 (score error 13.8% vs 18.9%; rank correlation 90.1 vs 89.4). Flagships collapse to a few anchor values, degrade badly when the camera moves (Qwen2.5-VL-32B error 21% → 46%), and handle "unanswerable" poorly. Unanswerable cases were made with an image-editing model; people kept 23.5% of the edits. | The whole recipe shape: small model, reasoning written given the answer, then reinforcement learning with checkable rewards. Build unanswerable cases on purpose. Report how often the model refuses answerable items. |
| **GVL**, "VLMs are in-context value learners" (ICLR 2025) [2411.04549](https://arxiv.org/abs/2411.04549) | Asking a model to put **shuffled** frames in order gives far better progress estimates than asking frame by frame | A shuffled-frame ordering task in the mix |
| **VLAC** [2509.15937](https://arxiv.org/abs/2509.15937) | A **pairwise** "progress delta" between any two frames works from any starting point | Our basic input is a pair: last visit, this visit |
| **TEOChat** (ICLR 2025) [2410.06234](https://arxiv.org/abs/2410.06234) | A Video-LLaVA tuned on a before/after instruction set for satellite images beat GPT-4o and Gemini 1.5 Pro on several temporal tasks | A domain before/after instruction set is enough to beat flagships |
| **Visual-RFT** [2503.01785](https://arxiv.org/abs/2503.01785), **Video-R1** (NeurIPS 2025) [2503.21776](https://arxiv.org/abs/2503.21776) | Reinforcement learning with rule-checked rewards (GRPO) beats plain fine-tuning with few examples (+24% with about 100 examples). Video-R1's T-GRPO rewards an answer only when it is right more often on ordered frames than on shuffled ones; Video-R1-7B beat GPT-4o on VSI-Bench. | Short, checkable answers. Order and swap consistency as a reward. |
| **LLaVA** (NeurIPS 2023) [2304.08485](https://arxiv.org/abs/2304.08485), **LLaVA-1.5** [2310.03744](https://arxiv.org/abs/2310.03744) | Instruction data written by a teacher model works. A random 50% of the data keeps over 98% of the result. | Small and curated beats big and noisy |
| **Qwen3-VL** [2511.21631](https://arxiv.org/abs/2511.21631) | Dense 2B / 4B / 8B / 32B and MoE models, strong at several images and video, open weights | Base model **Qwen3-VL-4B-Instruct**; 2B for Track B |
| **Arrow of time** [2510.26241](https://arxiv.org/abs/2510.26241), **TemporalVQA** [2501.10674](https://arxiv.org/abs/2501.10674) | Most models are near chance at telling forward from backward, worst on **irreversible** processes. GPT-4o got 49.1% on ordering frames. | Before vs after, and "did it ever go back?", is where flagships are weakest |
| **All-Angles Bench** [2504.15280](https://arxiv.org/abs/2504.15280) | 27 models, GPT-4o and Gemini included, fail at matching the same place across viewpoints | A moved phone camera is a known weak spot: train for it |
| **Made to Order** (ECCV 2024) [2404.16828](https://arxiv.org/abs/2404.16828) | Ordering shuffled frames finds changes that only grow with time, and ignores light cycles and passers-by | Time order is a free label (already T146 §7) |
| **Look for the Change** (CVPR 2022) [2203.11637](https://arxiv.org/abs/2203.11637) | "Initial state → action → end state" order in web videos labels object states with almost no human work | Web timelapses label themselves |
| **The Change You Want to See** (WACV 2023) [2209.14341](https://arxiv.org/abs/2209.14341), **Img-Diff** (CVPR 2025) [2408.04594](https://arxiv.org/abs/2408.04594) | Synthetic change pairs (paint an object out, or swap it) train change finders that work on real photos. Img-Diff's tuned model beat GPT-4V and Gemini on MMVP. | Counterfactual pairs whose answer is known exactly |
| **RLAIF-V** (CVPR 2025) [2405.17220](https://arxiv.org/abs/2405.17220) | Preference training on open-model feedback cut made-up objects by 80.7% | Optional: prefer "not fooled" answers over "fooled" ones |
| **ConstructionSite-10k** [2508.11011](https://arxiv.org/abs/2508.11011) | 10,013 site images with captions, rule-violation Q&A and grounding. Flagships generalise somewhat, but need training for real sites. | Vocabulary and single-image stage data |
| **iVISION-2DCD** (2026) [2607.03553](https://arxiv.org/abs/2607.03553) | Construction change pairs rendered from LiDAR, aligned to the pixel, over a year | Viewpoint-robust change with exact maps |
| **OpenConstruction** [2508.11482](https://arxiv.org/abs/2508.11482) | A catalogue of 51 open construction datasets, with licence, size and labels | Where to look first |
| **Smart Cities field study** (2026) [doi 10.3390/smartcities9070114](https://doi.org/10.3390/smartcities9070114) | Gemini, ChatGPT and Copilot on 1,186 images from 17 real sites: good at **describing** activity and progress, weak at **judgement** | Judge claims, do not caption |
| **AVA-VLM** (2026) [2607.05859](https://arxiv.org/abs/2607.05859) | Zooming into far regions only when needed raised F1 on far objects from 16 to 64, with 31% of the image tokens | High-resolution crops for far parts of a site |

**Why our win is plausible.** Flagship models are good at saying what is in a photo. They are weak at three things:
- which way time runs;
- matching one place across two camera positions;
- telling a busy site from a built one.

Our job is exactly those three. Our labels come from hindsight (T146 §5.1) and from the stage order, so the model is
never taught "busy means progress".

---

## 3. The task: what the model sees and says

**Input:**
- **frames A and B**: the same viewpoint, last visit and this visit (1–2 frames each, about 512 px);
- **the work type** (building, CC road, drain, boundary wall, …) and **its stage list** (T146 `stages.py`);
- **the agency's one-line claim**, in English, Hindi or Hinglish.

**Output** (short JSON, so reinforcement learning is cheap):

```json
{"same_place": "yes", "stage_A": 3, "stage_B": 5, "permanent_change": "yes",
 "verdict": "shown", "where": [[0.42, 0.30, 0.71, 0.66]],
 "reason": "Brick walls now stand to window height in the left half; last visit showed only the plinth."}
```

| Field | Values |
|---|---|
| `same_place` | yes / no / unsure |
| `permanent_change` | yes / no / cant_tell |
| `verdict` | shown / not_shown / cant_tell |
| `where` | boxes, scaled 0 to 1 |
| `reason` | at most 25 words, about what is visible, never accusing anyone |

**Two kinds of claim** (both come straight from Site Progress):
- **"Stage reached":** for example "walls up to lintel level". Judged on B.
- **"Done this month":** for example "roof slab cast this month". Judged on A and B together.

  "Already there last visit" makes it **not shown**. That catches the same work being claimed twice.

---

## 4. Getting the data (ingestion)

### 4.1 Sources, best first

| # | Source | Why | How we get it | Licence and risk | Role |
|---|---|---|---|---|---|
| **S1** | **GeoMGNREGA** ([portal](https://bhuvan-app2.nrsc.gov.in/mgnrega/mgnrega_phase2.php)): every asset geotagged with photos **before, during and after** the work; over 5.74 crore assets public on ISRO's Bhuvan | **Real Indian public works** (ponds, roads, drains, buildings), on phones, already **in time order**: the closest thing to MPLADS on the internet | Probe (§4.3): the portal answers from this PC (it redirects to `/bhugram/bhugram.php`, which mentions "Photographs"); find how a photo is fetched, as was done for eSAKSHI. Then a polite pilot: 1.5 s between requests, a few thousand assets. | Public portal; read its disclaimer first; blur faces; never redistribute | Training **and** the Indian part of the test set |
| **S2** | **PMAY-G (AwaasApp)** stage photos: not started, foundation, lintel, roof, completed, each geotagged within 5 days of the stage | **Stage labels already attached**, for small buildings | Same as S1 (Bhuvan / AwaasSoft public reports) | Same | Stage training, test |
| **S3** | **PMGSY (OMMAS)** quality-monitor photos: at least 10 per inspection, at the initial, middle and final stages | Road stages, from inspectors | OMMAS public pages ([omms.nic.in](https://omms.nic.in); it did not answer from the owner's PC on 7 Oct 2026, so try another connection) | Same | Road stages |
| **S4** | **eSAKSHI attachments**: 323 photos already in `data/evidence/` (gitignored); the public endpoints are in [`docs/DATA.md`](../DATA.md) | MPLADS itself: completion photos with GPS stamps; claims from the work's own description | Already harvested | Existing pilot rules | "Complete" claims; test |
| **S5** | **YouTube CC BY timelapses** | Long still-camera builds, where hindsight labels come for free | T146 `python -m drishti_vision search` (`videoLicense=creativeCommon`; queries in English and Hindi), then `yt-dlp` with the licence re-checked on the video page | CC BY allowed (7 Oct); NC/ND refused; credit each uploader in the card | Hindsight pairs, ordering |
| **S6** | **Wikimedia Commons** (timelapse and "under construction in India" categories) and **Mapillary** street-level photos over time in India ([API](https://www.mapillary.com/developer/api-documentation), CC BY-SA, free token) | Real handheld photos and viewpoint shifts | APIs | Licence per file | View-shift pairs (Mapillary is exploratory: low yield expected) |
| **S7** | **Open datasets:** [ConstructionSite-10k](https://huggingface.co/datasets/LouisChen15/ConstructionSite) (gated), [IITU 12-month fixed-view sequence](https://data.mendeley.com/datasets/ww7rt2rnk6), ConSLAM (ECCV-W 2022), the construction-activity caption set (13,000 images, 65,000 captions), [VL-Con](https://www.iaarc.org/publications/2024_proceedings_of_the_41st_isarc_lille_france/vl-con_vision-language_dataset_for_deep_learning-based_construction_monitoring_applications.html), iVISION-2DCD, SODA, MOCS, the [ChangeIt videos](https://data.ciirc.cvut.cz/public/projects/2022LookForTheChange), the OpenConstruction catalogue; also Kaggle, Zenodo and Roboflow Universe searches ("construction stage", "building under construction", "construction timelapse") | Vocabulary, single-image stages, viewpoint-robust change, and cut-outs of people and machines for planted tricks | Download each; record it in the manifest | Per dataset; the allow-list refuses unclear licences | Mostly support; IITU and ConSLAM give real sequences |
| **S8** | **Synthetic:** T146 `synth.py` (five building types with exact truth), plus the counterfactual edits (blocks E1–E6) | The answer is known exactly | Local or Kaggle | Ours | Hard negatives; pipeline tests |

### 4.2 Rules (from T146 and AGENTS.md)

- **Nothing heavy in git:** no video, frame or built dataset. Git holds the manifest, licence ledger, code, labels'
  code and measured numbers.
- **Where the data lives:** on **`D:\nidhinetra-data`**. The owner's C: drive has only 6.5 GB free; D: has 94 GB. Copies of
  the built dataset go to the team Drive and a private Kaggle dataset.
- **Leak-proof splits:** by site, uploader channel **and district**. The test set comes only from districts never used in training.
- **Faces:** blurred before any frame leaves the PC (`video/reader.blur_faces`).

### 4.3 Probe each source before bulk work (task T151)

| Source | Probe (about 1 hour each) | Go on if | Stop if |
|---|---|---|---|
| S1 GeoMGNREGA | Open the portal in a browser; find the photo request in the network tab; read the disclaimer; fetch 50 assets of MPLADS-like types in 2 districts | Photos come without login, and at least 30% of assets have all three stages | Login is needed, or the terms forbid reuse |
| S2 PMAY-G | Same, through Bhuvan / AwaasSoft public reports | Stage photos are visible publicly | Same |
| S3 PMGSY | Find inspection photos on OMMAS public pages | Photos carry the stage | Same |
| S5 YouTube | 20 searches in English and Hindi, 10 downloads, `drishti_vision build` | At least 1 in 4 videos gives a usable still-camera shot | Under 1 in 10: lean on S1, S2 and S7 instead |
| S6 Mapillary | 5 Indian towns, sequences spanning more than 6 months | Any construction seen twice | Nothing: drop it |
| S7 open sets | Licence check for each; download the small ones | The licence is clear | It is not: skip that set |

---

## 5. The building-block menu

Every block below can be mixed with the others. ★ marks the blocks in my recipe (§6).

**The failures each block guards against** (the picker page totals these):

| Code | Failure |
|---|---|
| `STAGED` | A site dressed up for filming day (workers, machines, stacked materials) called progress |
| `LIGHT` | Light, shadow, weather or season called progress |
| `VIEW` | A phone held in a different spot: misalignment called change, or real change missed |
| `COVERED` | Covered or buried work (plaster over brick, a backfilled footing) read as no change, or as going backwards |
| `SHORTCUT` | Reading the date stamp, watermark, camera style or time gap instead of the building |
| `ABSTAIN` | Answering when the photos cannot decide, or refusing when they can |
| `DOMAIN` | Indian public works (CC roads, drains, hand pumps, solar lights) look unlike internet towers |
| `LANG` | Claims in Hindi or Hinglish, with engineering terms and typos |
| `NOISE` | Wrong labels teaching the wrong thing |
| `LEAK` | The same site in training and test: a fake high score |
| `PLACE` | A different place passed off as this site |
| `GROUND` | "Shown" with no pointer to where, or a made-up reason |

Effort and GPU times are rough estimates for this project's size. "You" means a person; "AI" means Claude Code doing it.

### A · Sources

| ID | Block | Guards against | Effort | Compute |
|---|---|---|---|---|
| A1 ★ | S1 GeoMGNREGA before / during / after | DOMAIN, VIEW | Probe 1 h AI + pilot run overnight | CPU |
| A2 ★ | S2 PMAY-G stage photos | DOMAIN | Same | CPU |
| A3 | S3 PMGSY inspection photos | DOMAIN (roads) | Same | CPU |
| A4 ★ | S4 eSAKSHI photos (already here) | DOMAIN | 1 h AI | CPU |
| A5 ★ | S5 YouTube CC BY timelapses | COVERED, STAGED (real temporaries) | 3 h you (keep or drop each candidate) + AI | CPU, disk |
| A6 | S6 Wikimedia + Mapillary | VIEW, DOMAIN | 2 h AI | CPU |
| A7 ★ | S7 open datasets (SODA, MOCS, IITU, ConstructionSite-10k, …) | STAGED (cut-outs), LANG (captions) | 2 h AI | CPU |
| A8 ★ | S8 synthetic sites (T146 `synth.py`) | COVERED, STAGED, SHORTCUT | Built already | CPU |

### B · Cleaning

| ID | Block | What it does | Guards against | Effort | Compute | Source |
|---|---|---|---|---|---|---|
| B1 ★ | Still-camera shot split | Cuts edited timelapses into shots that can be aligned; drops drone passes and title cards | VIEW, NOISE | Built (T146 `shots.py`) | CPU | T146 §4.3 |
| B2 ★ | Quality filter | Drops dark, blurred and night frames | ABSTAIN, NOISE | Built (`frames.py`) | CPU | T146 |
| B3 ★ | Alignment | Matches each frame onto a reference (shift, rotation, zoom) | VIEW | Built (`register.py`) | CPU | T146 |
| B3b | 3D re-render | Rebuilds the site in 3D from a walk-around and renders the exact same viewpoint each month (VGGT or MASt3R; check their licences) | VIEW | 1 day AI | GPU | [VGGT 2503.11651](https://arxiv.org/abs/2503.11651) |
| B4 ★ | Date-stamp and watermark masks | Finds burned-in text that stays fixed while the scene changes | SHORTCUT | Built (`overlays.py`) | CPU | T146 |
| B5 ★ | Temporal median | A median of nearby frames removes passers-by with no model at all | STAGED | Built (`register.py`) | CPU | T146 §4.4 |
| B6 ★ | Open-vocabulary masks | **SAM 3** finds every "person", "scaffolding", "brick stack", "formwork", "excavator" by name. They are masked, never painted over in a real input. YOLO on COCO classes is the lighter fallback. | STAGED | 3 h AI | 3070 Ti | [SAM 3](https://github.com/facebookresearch/sam3) (check its licence) |
| B7 ★ | Face blur | Privacy, before any frame leaves the PC | (privacy) | Built (`video/reader.blur_faces`) | CPU | AGENTS.md |
| B8 ★ | Same-site joining | Re-uploads and second cameras of one project become one site before splitting | LEAK | Built (`splits.py`) | CPU | T146 §6 |
| B9 | Sky and vegetation masks | Leaves out what changes with the season | LIGHT | 2 h AI | GPU | SAM 3 / segmentation |
| B10 ★ | Embedding de-duplication | Removes near-identical frames, so each example adds something new | NOISE | 1 h AI | GPU (DINOv2) | — |

### C · Labelling: where the truth comes from

| ID | Block | What it does | Guards against | Effort | Compute | Source |
|---|---|---|---|---|---|---|
| C1 ★ | **Hindsight teacher** | A change is progress only if that place **never goes back** to how it was. Scaffolds, stacks, people and shadows all go back. Gives labels for each patch and each pair. | STAGED, LIGHT | Built (`hindsight.py`) | GPU (DINOv2 features) | T146 §5.1 |
| C2 ★ | Stage-onset marks | A person marks the frame where each stage begins (about 10 clicks a shot); every frame inherits its stage; stages only go up | COVERED | ~8 h you for 250 shots (share it) | — | T146 §5.2 |
| C3 ★ | Stage from government metadata | PMAY-G and GeoMGNREGA photos carry their stage (before / during / after; foundation / lintel / roof) | DOMAIN | Free once probed | — | §4.1 |
| C4 ★ | Time order as a label | A later frame of a still shot is never less built | COVERED, SHORTCUT | Free | — | Made to Order, GVL |
| C5 | Big-model pre-labels | A large model drafts labels; a person accepts or fixes them (about 5 s each) | NOISE | 2 h you per 1,000 | Gemini free tier or a local 8B model | LLaVA |
| C6 | Model consensus | Three models label; Dawid–Skene weighs them; disagreements go to a person | NOISE | 1 h AI | API or local | Dawid & Skene 1979 |
| C7 ★ | **Answer-given reasons** | A teacher writes the 25-word reason **knowing the right answer**. A second model must reach the same verdict from that reason alone, or the reason is dropped. | GROUND, NOISE | 4 h AI + GPU time | Local Qwen3-VL-8B (4-bit) or Gemini free tier | ProgressLM §3 |
| C8 | Self-taught reasons | The student writes reasons; only those that end at the right answer are kept | GROUND | — | GPU | [STaR 2203.14465](https://arxiv.org/abs/2203.14465) |
| C9 ★ | Label where models disagree | People label first where the teacher, the student and a flagship disagree | NOISE | Part of C11's time | — | Active learning |
| C10 ★ | Noisy-label finder | Cross-validated predictions flag labels that are probably wrong, for a second look | NOISE | 1 h AI | CPU | [Confident learning 1911.00068](https://arxiv.org/abs/1911.00068) |
| C11 ★ | Two labellers on 10% | Agreement (Cohen's κ) is measured and recorded in the dataset card | NOISE | ~3 h you | — | — |
| C12 | Activity check | A permanent change that no person or machine was ever near is suspicious, and goes to a person | NOISE | Built (masks) | CPU | T146 §5.3 |
| C13 ★ | **Claim ladder** | Turns each pair's stage indices into several claims with **exact** labels: earlier or same stage → shown; two or more stages ahead → not shown; "this month" for work already there last visit → not shown; the stage boundary itself is left out (§6.3) | STAGED, LANG, COVERED | 3 h AI | CPU | New here; builds on ProgressLM and T146 |
| C14 ★ | "Where" boxes | Boxes drawn round the hindsight progress map | GROUND | 1 h AI | CPU | T146 |
| C15 | "Which is later?" pairs | Pairwise order labels, for a ranking score | COVERED | Free | — | VLAC |
| C16 ★ | Unanswerable on purpose | B from another site, too dark, no overlap, or a heavy occlusion → can't tell | ABSTAIN, PLACE | 2 h AI | CPU | ProgressLM |
| C17 | Counts | For countable claims ("120 solar lights"): count with a detector, then check by eye | GROUND | 3 h AI + 1 h you | GPU | — |

### D · Pixel changes that keep the label

| ID | Block | Teaches | Guards against | Effort | Compute |
|---|---|---|---|---|---|
| D1 ★ | A different crop, zoom, small rotation and perspective for A and for B | A handheld phone never stands in the same spot twice | VIEW | Built (`augment.py`) | CPU |
| D2 ★ | Brightness, white balance, gamma, a shadow band, haze, rain | Light and weather are not progress | LIGHT | Built | CPU |
| D3 ★ | JPEG, blur, noise, low resolution | Cheap phones | DOMAIN | Built | CPU |
| D4 ★ | Blank corners and overlay boxes | Never read the date | SHORTCUT | Built | CPU |
| D5 ★ | **Paste people, machines, scaffolds and brick stacks into B only (label: no progress)**, using real cut-outs from SODA, MOCS or SAM 3 rather than drawn shapes | Dressing up the site is not progress | STAGED | 3 h AI (cut-out library) | CPU |
| D6 ★ | Swap A and B (the label flips) | Progress has a direction | SHORTCUT | Built | CPU |
| D7 ★ | Pairs a few frames apart (label: none) | Morning and evening differ; the building did not | LIGHT | Built | CPU |
| D8 | Monsoon or dusk look, by an image-editing model | Seasons are not progress | LIGHT | 3 h AI | Kaggle GPU |
| D9 | Depth-warp viewpoint shift (Depth Anything V2 Small, Apache-2.0) | Bigger viewpoint changes than a crop can make | VIEW | 3 h AI | 3070 Ti |
| D10 ★ | Occlusion and cut-out | When most of the view is blocked, say can't tell | ABSTAIN | 1 h AI | CPU |
| D11 ★ | Portrait and landscape; different aspect ratios | Phones are held both ways | SHORTCUT | 1 h AI | CPU |

### E · Made-up pairs whose answer is known

| ID | Block | What it does | Guards against | Effort | Compute | Source |
|---|---|---|---|---|---|---|
| E1 ★ | Paint out a built element | Remove a wall or slab from a real later frame (LaMa, Apache-2.0) to make an exact "before". Allowed because it creates a training input whose label we know; never used to clean a real input (T146 §5.4). | COVERED, GROUND | 4 h AI | 3070 Ti | [The Change You Want to See](https://arxiv.org/abs/2209.14341), [LaMa 2109.07161](https://arxiv.org/abs/2109.07161) |
| E2 | Instruction edits | "Add workers and cement bags" (staged) or "remove the roof slab" (earlier stage) with Qwen-Image-Edit; a person keeps only good edits (ProgressLM kept 23.5%) | STAGED, COVERED | 4 h AI + 2 h you | Kaggle GPU (large model) | ProgressLM, [Qwen-Image 2508.02324](https://arxiv.org/abs/2508.02324) |
| E3 | Backward edits | Keep a claimed element missing, for "not shown" | STAGED | Part of E2 | Kaggle | — |
| E4 ★ | Procedural sites | T146's synthetic builds, with exact truth | COVERED, SHORTCUT | Built | CPU | T146 §9 |
| E5 ★ | Another site's photo as B | "Not the same place" → can't tell | PLACE | 1 h AI | CPU | — |
| E6 ★ | The wrong kind of claim | A road claim on a building pair → not shown or can't tell | LANG | 1 h AI | CPU | — |

### F · Claim text

| ID | Block | Guards against | Effort |
|---|---|---|---|
| F1 ★ | Paraphrases in English, Hindi and Hinglish (an LLM drafts them, a person checks 50) | LANG | 2 h AI + 1 h you |
| F2 ★ | Stage-ladder claims, worded the way agencies word them | LANG | Part of C13 |
| F3 | Zone and quantity claims ("in zones 2–6", "120 m laid") | GROUND | 2 h AI |
| F4 ★ | Negations and contradictions ("roof not yet cast") | LANG | 1 h AI |
| F5 ★ | Typos and transliteration, the way eSAKSHI is written ("lintal", "C.C. rd") | LANG | 1 h AI |
| F6 ★ | Engineering terms: lintel, RCC, PCC, WBM, plinth beam, interlocking tiles, coping | LANG, DOMAIN | 1 h AI |

### G · Tasks: one pair, many questions

| ID | Task | Share in my mix |
|---|---|---|
| G1 ★ | Claim verdict: shown / not shown / can't tell, with a reason | 45% |
| G2 ★ | Permanent change yes / no, and where | 15% |
| G3 ★ | The stage of each frame | 15% |
| G4 ★ | Put 3–4 shuffled frames in order | 10% |
| G5 | Progress percentage (ProgressLM style) | — |
| G6 ★ | Describe the permanent work added | 5% |
| G7 | Is this object temporary or permanent? | — |
| G8 ★ | Same place? | 5% (G8 and G9 together: 10%) |
| G9 ★ | Can these photos answer the claim? | 5% |
| G10 | Count the claimed items | — |

### H · Curation: keeping it small and rich

| ID | Block | What it does | Guards against |
|---|---|---|---|
| H1 ★ | Stratified quotas | Fill a grid: work type × stage × source × light × viewpoint gap × trick, so no cell dominates | DOMAIN, STAGED |
| H2 ★ | Diversity core-set | Pick examples spread across the DINOv2 embedding space, not 50 frames of one site | NOISE |
| H3 ★ | Hard-example mining | Keep what the base model gets wrong or is unsure of; keep some easy ones for calibration | (efficiency) |
| H4 ★ | Near-duplicate removal | Perceptual hash plus embeddings | LEAK, NOISE |
| H5 ★ | Balanced verdicts | About 35% shown / 40% not shown / 25% can't tell, so "shown" is never a safe guess | STAGED, ABSTAIN |
| H6 ★ | Leak control | Split by site, channel and district; the test set comes from districts never used in training | LEAK |
| H7 ★ | Shortcut audits | With corners blanked, colours shifted or the time gap randomised, the score must not move | SHORTCUT |
| H8 ★ | Dataset card and licence ledger | Counts per cell, licences, credits, labeller agreement | (paper, licences) |
| H9 | Easy-to-hard order | Curriculum during fine-tuning | — |
| H10 ★ | The test set is never online | Not in git, not on Kaggle public, not sent to any API before the final run | LEAK |

### I · Training

| ID | Block | What it does | Compute |
|---|---|---|---|
| I1 ★ | QLoRA fine-tuning | 4-bit base model, LoRA rank 16 on the language layers | T4 (Kaggle) or 3070 Ti |
| I2 ★ | Reasons as a cold start | Fine-tune on C7's answer-given reasons first | Same |
| I3 ★ | **GRPO with checkable rewards** | The model tries 4 answers; the ones that score higher are reinforced (rewards in §6.5) | Kaggle T4 (slow but free) |
| I4 | Swap and shuffle consistency | Reward only when the answer for (A, B) agrees with (B, A), or when ordered frames beat shuffled ones | Kaggle |
| I5 | Preference training (DPO) | Prefer "not shown: workers present, no new structure" over "shown" on staged pairs | Kaggle |
| I6 ★ | Task-mix ratios | §5 G column | — |
| I7 ★ | Frozen vision part, about 512 px a frame | Fits 8–16 GB and keeps the vision part's general knowledge | — |
| I8 | Distil from an open giant | Match a 235B model's answer probabilities | Needs a big GPU (later) |
| I9 | Average LoRA checkpoints | Often steadier than any single checkpoint | CPU |
| I10 ★ | Calibration | Temperature on the calibration split; thresholds for "can't tell" | CPU |
| I11 | DINOv2 change map as an extra input | T146's map drawn over B, as a hint | GPU |
| I12 | Test-time voting | Sample 3–5 answers and vote; check swap consistency | ×3–5 inference time |

### J · Proving it

| ID | Block |
|---|---|
| J1 ★ | SiteClaim-Bench (§7) |
| J2 ★ | A separate score for each trick (staged, light, view shift, unanswerable, real Indian works) |
| J3 ★ | Flagship baselines, each given its best of three prompts (plain, few-shot, step-by-step) |
| J4 ★ | Metrics: macro-F1, fooled rate, accuracy against how often it answers, stage error, calibration error, cost per 1,000 checks, speed, works offline |
| J5 | A civil engineer labels 100 items, as a human baseline |
| J6 ★ | Bootstrap 95% confidence intervals; McNemar's test against each flagship |
| J7 ★ | Ablations: each block switched off in turn (what does D5 buy? what does C1 buy?) |

---

## 6. My recipe: the Hindsight Claim Ladder (HCL)

**The idea in two sentences.** The timelapses and the government stage photos tell us, with no human judgement about
appearance, **what really got built and in which order**. The claim ladder turns each such pair into several claims with
exact answers, and the planted tricks teach the model that a busy site is not a built one.

### 6.1 The steps

1. **Probe** S1, S5, S6 and S7 (§4.3). Write `manifest.jsonl` and the licence ledger. Data on `D:\nidhinetra-data`.
2. **Clean:** B1–B5, B7, B8 and B10 (T146 code), plus B6 (SAM 3 masks).
3. **Label with no judgement calls:**
   - timelapses: C1 (hindsight, per patch) and C4 (time order);
   - government photos: C3 (stage from metadata);
   - people: C2 on about 250 shots (about 8 hours, shared out) and C11 (two labellers on 10%).
4. **Multiply with the claim ladder (C13)**, worded with F1, F2, F4, F5 and F6: about 4 claims a pair.
5. **Plant the tricks** (this is what wins Track A):
   - D5: staged pastes, from real cut-outs;
   - D2 and D7: light-only pairs;
   - D1: view shifts;
   - D6: swaps;
   - E5: another site;
   - C16: unanswerable;
   - E1: painted-out "before" frames.

   E2 (generative edits) only if time allows.
6. **Reasons (C7):** a 25-word reason written given the right label, by a local Qwen3-VL-8B (4-bit) or Gemini's free tier. Kept
   only if a second model reaches the same verdict from it.
7. **Curate** with H1–H8 and H10, down to:

   | Set | Size | What is in it |
   |---|---|---|
   | Fine-tuning examples | **~6,000** | Task mix from §5 G; verdicts about 35 / 40 / 25 |
   | RL prompts | **~1,500** | H3: where the base model is wrong or unsure |
   | Calibration | **~300** | |
   | Test (SiteClaim-Bench) | **~800** | Human-labelled, unseen districts |

8. **Train on free compute (§8):** I1 + I2, then I3, then I10. Repeat with the 2B model for Track B.
9. **Measure (§7):** J1–J4, J6 and J7. Write the paper (§9).

### 6.2 Where the examples come from (targets)

| Source | Raw | Kept for training | Kept for test |
|---|---|---|---|
| Government stage photos (S1–S3) | 3,000–10,000 assets, if the probe passes | ~2,000 pairs | ~300 pairs (unseen districts) |
| Timelapses (S5, S7 sequences, S6) | 200–300 still-camera shots | ~2,500 pairs | ~150 pairs |
| eSAKSHI photos (S4) | 323 | ~150 | ~100 |
| Planted tricks (D5, E1, E5, C16, D2) | Generated | ~1,200 | ~250, reported apart from the real ones |
| Synthetic sites (S8) | Generated | ~300 | None (the test set is real or planted-on-real) |

### 6.3 The claim ladder, exactly

For a work type with stages `0 … K-1`, a pair (A, B) with stage indices `a ≤ b`, and the hindsight label for B:

| Claim | Label |
|---|---|
| "Stage k reached", `k ≤ b` | **shown** (for `k < b`, the reason says it is implied by a later stage) |
| "Stage k reached", `k ≥ b + 2` | **not shown** |
| "Stage k reached", `k = b + 1` | left out: too close to call from a photo |
| "Stage k done this month", `a < k ≤ b`, and hindsight shows permanent change | **shown** |
| "Stage k done this month", `k ≤ a` | **not shown** ("already there last visit": the double-claim trick) |
| "Stage k done this month", `k > b` | **not shown** |
| Any claim, with B from another site, too dark, or no overlap | **can't tell** |
| Any claim, on a staged pair (D5) where `a = b` | the same as the unstaged pair: **never shown** for "done this month" |

Buried work (a backfilled footing) is the case hindsight gets wrong (T146 measured 16.9% of buried patches called
progress). The stage marks overrule it: a later stage at B always makes "done this month" possible.

### 6.4 Data mix check before training

The dataset card (H8) must show all of these, or we fix the gap first:
- every work type has at least 300 examples;
- every trick has at least 150;
- verdicts within 5 points of 35 / 40 / 25;
- 0 sites shared across splits.

### 6.5 Rewards for the reinforcement stage (GRPO)

`R = 0.1 × format + 0.6 × verdict + 0.2 × stage + 0.1 × where` (where-reward only on pairs with a hindsight map; otherwise its
weight is spread over the others).

| Truth \ answer | shown | not shown | can't tell |
|---|---|---|---|
| shown | +1 | −1 | −0.2 |
| not shown | −1 (**−1.5** on a staged, light-only or swapped pair: being fooled costs most) | +1 | −0.2 |
| can't tell | −1 | −0.5 | +1 |

- **stage** = 1 − min(|error|, K)/K, averaged over A and B;
- **where** = IoU with the hindsight box;
- **format** = valid JSON with every field.

The −0.2 for an unneeded "can't tell" stops the model hiding behind it. ProgressLM's flagships showed that trade-off:
high unanswerable detection came with up to 37% of answerable items refused.

---

## 7. SiteClaim-Bench: how we prove it (fixed before training)

### 7.1 The test set

About 800 items, all labelled by people (two labellers, a third breaks ties), from **sites and districts never used in
training**, and never posted online or sent to any API before the final run.

| Subset | Items | What |
|---|---|---|
| Real Indian works | ~300 | Government stage photos (S1–S3) + eSAKSHI (S4) |
| Real timelapse pairs | ~150 | S5, S7 sequences |
| Staged site | ~150 | Real "temporary only" pairs found by hindsight (crowds, stacks, scaffolds with no new structure), plus planted pastes. **The two are reported separately.** |
| Light or season only | ~75 | |
| View shift | ~75 | |
| Unanswerable | ~75 | Other site, too dark, no overlap |

### 7.2 What is measured

| Measure | In plain words |
|---|---|
| Macro-F1 of the verdict | How right the verdicts are, with the three answers weighted equally |
| **Fooled rate** | Of the pairs with no real progress (staged, light-only, swapped), the share called progress or "shown" |
| Answered accuracy and coverage | How right it is when it answers, and how often it answers; also answerable items wrongly refused, and unanswerable items caught (as in ProgressLM) |
| Stage error, rank correlation | How far off the stage is; whether the order is right |
| Calibration error (ECE) | Whether "90% sure" means right 9 times in 10 |
| **Cost per 1,000 checks** (₹ and $), speed, offline | API price at run time, against electricity on the owner's PC |

### 7.3 Who it is compared with

- **Flagship models through their APIs:**
  - Gemini, on the owner's free-tier key;
  - the newest GPT and Claude flagships, which need about $10–30 of API calls in total. **This is the owner's decision.** Until
    then, Gemini plus large open models.
- **Each flagship gets its best of three prompts:** today's `readers.PROMPT`, a few-shot version, and a step-by-step version.
- **Other baselines:**
  - base Qwen3-VL-4B with no tuning (to show what the tuning bought);
  - the CLIP reader;
  - T146's DINOv2 student.

### 7.4 Success and stop rules

**Track A succeeds if all three hold:**
1. **Fooled rate on the staged subset** is at most half the best flagship's, and at most 5%.
2. **Macro-F1 on the real subsets** is at least the best flagship's minus 3 points.
3. **Cost** is about ₹0 a check at the margin (runs on the owner's PC).

**Stop rule:** after fine-tuning, reinforcement learning and one round of fixing the data, if the fooled rate is still not
below the best flagship's, we **do not claim** Track A. We report it honestly and switch to Track B.

**Track B succeeds if** macro-F1 is within 2 points of the best flagship's at 1/100 of its cost or less (2B or 4B, 4-bit).

Every number comes with a 95% bootstrap interval. A difference counts only if McNemar's test agrees.

**Deck rule:** in the SIH deck, the comparison chart goes **only** on the final References slide. The paper compares
normally, because that is what a benchmark is for.

---

## 8. Training on free compute

| | Owner's PC | Kaggle (free) |
|---|---|---|
| GPU | RTX 3070 Ti, 8 GB, bf16 | T4 16 GB (fp16) or P100; about 30 GPU-hours a week; sessions end, so save every 30 minutes |
| Best for | Building the data: DINOv2 features, SAM 3 masks, LaMa; inference; 2B fine-tuning | 4B fine-tuning and GRPO |
| Software | Windows: use **WSL2 (Ubuntu)** for the training stack (bitsandbytes and fast generation work best on Linux) | Linux already |

**The model.**
- **Main:** Qwen3-VL-4B-Instruct, loaded in 4 bits. LoRA rank 16 on the language layers; vision part frozen.
- **Inputs:** 2–4 frames of about 512 px (a few hundred image tokens each); answers under 100 tokens.
- **Cross-check** (optional, for comparability with ProgressLM): Qwen2.5-VL-3B.
- **Track B:** Qwen3-VL-2B.
- **Libraries:** TRL + PEFT, or Unsloth (less memory). Check the current docs at T154 time; both have changed quickly.

**Rough times** (estimates, to be replaced by measured numbers):

| Stage | Time |
|---|---|
| Fine-tuning: 6,000 examples × 2 passes on a T4 | ~3–6 h |
| GRPO: 1,500 prompts × 4 tries, short answers on a T4 | ~8–15 h, over 2–3 Kaggle sessions |
| One check on the 3070 Ti (4-bit) | ~1–2 s |

**If money comes later:**
- Qwen3-VL-8B;
- full ProgressLM-style rewards and longer reasons;
- distillation from a 235B model (I8);
- larger GRPO groups (8–16 tries).

---

## 9. The paper

**Working title:** *Hindsight supervision teaches a small vision-language model not to be fooled by staged construction progress.*

**Contributions:**
1. **SiteClaim-Bench:** before/after claim checking on Indian public works, with a separate score for each trick.
2. **The Hindsight Claim Ladder:** labels from irreversibility and stage order, multiplied into exact claims, plus planted
   tricks.
3. **A 4B model** that we test against flagships on being fooled, at about ₹0 a check (with Track B's cost result).
4. **An analysis** of why flagships fail: busy sites, a moved camera, the direction of time.

**Outline:**
1. Introduction (public-works audits; the MPLADS setting).
2. Related work: progress estimation (GVL, ProgressLM, VLAC), temporal benchmarks, change detection, construction vision-language models.
3. Data engine and labels.
4. Training.
5. Benchmark.
6. Results: main table, subsets, ablations (J7), cost.
7. Limits and ethics: never accusing anyone; privacy; licences; the model's readings stay notes until field-tested.

**Where:** an arXiv preprint first; then a workshop (computer vision for social good, or in-the-wild vision) or a
construction-computing venue (ISARC, *Automation in Construction*, ASCE *Journal of Computing in Civil Engineering*).

---

## 10. Other ready-made mixes (presets on the picker page)

| Preset | Blocks | When |
|---|---|---|
| **HCL (recommended)** | Every ★ above | The paper and the hackathon |
| **One-week hackathon** | A4, A5 (small), A7, A8; B1–B4, B6 (YOLO), B7; C1, C2 (60 shots), C4, C13, C16; D1–D7; E4, E5; F1, F2, F6; G1, G3, G8; H1, H4, H6, H10; I1, I10; J1 (300 items), J3 (Gemini only), J4 | A demo and one honest number quickly; no RL |
| **Maximum robustness** | HCL + B3b, B9, C5, C6, C12, D8, D9, E2, E3, I4, I5, I11, I12, J5 | If the staged or view-shift scores fall short |
| **Track B: same accuracy, 1/100 cost** | HCL data + I8 (when a big GPU exists), I9; 2B model, 4-bit; cost-focused J4 | After Track A |

---

## 11. Risks, honestly

| Risk | What we do |
|---|---|
| The government photo portals do not give photos without a login | Probe first (T151). Without them, the Indian test set is eSAKSHI photos plus Mapillary, and the team's own monthly films become necessary. |
| Few still-camera timelapses survive cleaning | Search "fixed camera", "site camera", "webcam timelapse"; lean on IITU, ConSLAM and the government photos |
| Free GPUs are slow for GRPO | Keep answers short and prompts few (1,500); fine-tuning alone is the fallback (the one-week preset) |
| Flagships turn out good at staged scenes | The stop rule (§7.4); Track B |
| Labels from one model leak into the benchmark | Test labels come from people only. Flagships never label anything they are tested on. |
| The win does not carry over to real monthly visits | Readings stay notes, never counted, until T126's real visits pass T120 §14 (AGENTS.md rule 4) |
| Licences | The manifest refuses anything not on the allow-list. Credits go in the dataset card. NC and ND stay refused. |

---

## 12. Proposed follow-up tasks (owner's go-ahead needed)

| Task | What | Size |
|---|---|---|
| T151 | Probe the sources (§4.3); write the manifest and licence ledger | S, **human-task** (browser looking) |
| T152 | Collect and clean (blocks A, B) on `D:\nidhinetra-data` | M |
| T153 | Label and curate (blocks C–H); the dataset card; label the 800 test items | L, **human-task** (stage marks, test labels) |
| T154 | Train: fine-tuning, GRPO, calibration (block I), on Kaggle and the 3070 Ti | M |
| T155 | SiteClaim-Bench run against flagships (block J); FINDINGS; paper draft | M |
| T156 | `VLMReader` in `readers.py`, behind a switch, with readings stored as notes | S |

T147–T149 (T146's DINOv2 path) carry on alongside. T152's clean frames and T153's hindsight labels serve both.

---

## 13. References

- Zhang et al. (Northwestern University). *ProgressLM: Towards Progress Reasoning in Vision-Language Models.* ACL 2026. [arXiv 2601.15224](https://arxiv.org/abs/2601.15224)
- Ma et al. *Vision Language Models are In-Context Value Learners.* ICLR 2025. [arXiv 2411.04549](https://arxiv.org/abs/2411.04549)
- *A Vision-Language-Action-Critic Model for Robotic Real-World Reinforcement Learning.* [arXiv 2509.15937](https://arxiv.org/abs/2509.15937)
- Irvin et al. *TEOChat.* ICLR 2025. [arXiv 2410.06234](https://arxiv.org/abs/2410.06234)
- Liu et al. *Visual-RFT.* [arXiv 2503.01785](https://arxiv.org/abs/2503.01785) · Feng et al. *Video-R1.* NeurIPS 2025. [arXiv 2503.21776](https://arxiv.org/abs/2503.21776) · Shao et al. *DeepSeekMath (GRPO).* [arXiv 2402.03300](https://arxiv.org/abs/2402.03300)
- Liu et al. *Visual Instruction Tuning (LLaVA).* NeurIPS 2023. [arXiv 2304.08485](https://arxiv.org/abs/2304.08485) · *Improved Baselines (LLaVA-1.5).* [arXiv 2310.03744](https://arxiv.org/abs/2310.03744)
- Qwen Team. *Qwen3-VL Technical Report.* [arXiv 2511.21631](https://arxiv.org/abs/2511.21631)
- *Which Way Does Time Flow?* [arXiv 2510.26241](https://arxiv.org/abs/2510.26241) · *Can Multimodal LLMs do Visual Temporal Understanding and Reasoning?* [arXiv 2501.10674](https://arxiv.org/abs/2501.10674) · *Seeing from Another Perspective (All-Angles Bench).* [arXiv 2504.15280](https://arxiv.org/abs/2504.15280)
- Yang, Xie, Zisserman. *Made to Order.* ECCV 2024. [arXiv 2404.16828](https://arxiv.org/abs/2404.16828) · Souček et al. *Look for the Change.* CVPR 2022. [arXiv 2203.11637](https://arxiv.org/abs/2203.11637)
- Sachdeva, Zisserman. *The Change You Want to See.* WACV 2023. [arXiv 2209.14341](https://arxiv.org/abs/2209.14341) · Jiao et al. *Img-Diff.* CVPR 2025. [arXiv 2408.04594](https://arxiv.org/abs/2408.04594)
- Yu et al. *RLAIF-V.* CVPR 2025. [arXiv 2405.17220](https://arxiv.org/abs/2405.17220) · Rafailov et al. *DPO.* [arXiv 2305.18290](https://arxiv.org/abs/2305.18290)
- Zelikman et al. *STaR.* [arXiv 2203.14465](https://arxiv.org/abs/2203.14465) · Northcutt et al. *Confident Learning.* [arXiv 1911.00068](https://arxiv.org/abs/1911.00068) · Dawid & Skene (1979), *Applied Statistics* 28(1).
- Chen, Zou. *ConstructionSite 10k.* [arXiv 2508.11011](https://arxiv.org/abs/2508.11011) · Mao et al. *iVISION-2DCD.* [arXiv 2607.03553](https://arxiv.org/abs/2607.03553) · Xiong et al. *OpenConstruction.* [arXiv 2508.11482](https://arxiv.org/abs/2508.11482) · *AVA-VLM.* [arXiv 2607.05859](https://arxiv.org/abs/2607.05859) · Urlainis et al. *Multimodal Generative AI for Construction-Site Management and Monitoring.* Smart Cities 9(7):114, 2026.
- Oquab et al. *DINOv2.* [arXiv 2304.07193](https://arxiv.org/abs/2304.07193) · Meta. *SAM 3.* [github.com/facebookresearch/sam3](https://github.com/facebookresearch/sam3) · Suvorov et al. *LaMa.* [arXiv 2109.07161](https://arxiv.org/abs/2109.07161) · Yang et al. *Depth Anything V2.* [arXiv 2406.09414](https://arxiv.org/abs/2406.09414) · Wang et al. *VGGT.* [arXiv 2503.11651](https://arxiv.org/abs/2503.11651) · Qwen Team. *Qwen-Image.* [arXiv 2508.02324](https://arxiv.org/abs/2508.02324)
- Government sources:
  - GeoMGNREGA on Bhuvan: [bhuvan-app2.nrsc.gov.in/mgnrega](https://bhuvan-app2.nrsc.gov.in/mgnrega/mgnrega_phase2.php) (5.74 crore assets geotagged and public, CAG 2025);
  - PMAY-G stage geotagging (AwaasApp; stages not started, foundation, lintel, roof, completed);
  - PMGSY OMMAS ([omms.nic.in](https://omms.nic.in)): stage-wise quality inspections with geotagged photos.
