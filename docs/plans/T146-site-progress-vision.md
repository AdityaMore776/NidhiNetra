# T146: Teaching a vision model to see real construction progress

**Owner (7 Oct 2026):** "Create a data ingestion pipeline of construction site videos, and create a tuned set of
data, and use techniques, specific augmentation of the data, ... combining it with architecture and then finally
fine tuning an existing vision model architecture, such that this architecture gets very good at identifying actual
construction progress." The owner's notes were ideas to judge, not instructions. This plan judges each one (§2),
keeps what works, and adds methods that work better (§3–§9).

## 1. Where it fits in DRISHTI

Site Progress compares each month's site video with last month's, at the same fixed viewpoints (T120 §9.4). Two of
its six checks need to see construction:

- **Check 5, "what changed since last month":** today `video/reader.change()` counts changed pixels after evening
  out the lighting. A worker, a parked truck, a pile of bricks or a shadow counts as "change" the same as a new wall.
- **Check 6, "does it show the claim?":** today this needs the optional Gemini reader (free tier, capped).

The model in this plan replaces check 5's pixel count with **"permanent structure added, and where"**. It also gives
check 6 a free, local **stage reading** ("walls up to lintel", "roof slab cast"). The model only produces readings;
the agent's rules (§9.5 of T120) still decide findings, and "can't tell" still never counts.

What it must survive, from the deployed setting:
- the phone is held by a person, so last month's and this month's views never line up exactly;
- the site can be dressed up for filming day: workers brought in, materials stacked (T120 §9.6);
- the works are Indian public works: CC roads, drains, community halls, boundary walls, hand pumps, solar lights.
  Internet timelapses are mostly towers and houses, often outside India.

## 2. The owner's notes, judged

| # | Idea | Verdict | Why | What we take |
|---|---|---|---|---|
| 1 | Learn from timelapses which parts are temporary; use "how slowly something is built" | **Keep the core; change the signal** | Speed is a weak signal. Some progress is fast (a slab is cast in a day, a precast panel goes up in an hour). Some temporary things stay for weeks (scaffolding, formwork, a crane). Weather and seasons are slow too. | **Irreversibility** (§5.1): a change is progress if the place **never goes back** to how it looked before. Scaffolding, stacked bricks, people and shadows all go back. A wall, and a tile laid over cement, never do. |
| 2 | Tune the number of parameters; if accuracy is low, find the common theme; if it is very high, it is overfit | **Keep the worry; change the remedy** | The worry is right: a model trained mostly on wooden houses judges only wooden houses. But parameter count is not the main lever, and high accuracy on sites the model never saw is not overfitting. **Overfitting means high on training sites and low on unseen sites.** | Freeze the big pretrained model and train only a small head (§7). Compare three sizes on held-out sites, never on training data. Report the train-vs-test gap (§8.2). Hold out a **whole construction type** at a time (leave-one-type-out) to test exactly the wooden-house worry. Finding "the common theme" becomes a slice report: error by type, distance, weather and time gap. |
| 3 | Remove humans with a person detector, so the model learns only the changing structure | **Keep, done differently** | Painting people out with an inpainting model invents structure that was never there, and the model would learn from those inventions. | **Ignore, never repaint.** In a fixed timelapse, take the median of a few neighbouring frames, which removes people and cars with no model at all. Where people stay put, a detector's mask marks those patches "don't learn here" in the loss, and drops them at inference (§4.4). |
| 4 | Text descriptions for as many day points as possible | **Keep, but as stages** | Free text for every day is costly, and noisy text teaches noise. Stages change only 5 to 10 times in a whole build. | A **stage list per work type** (§5.2), e.g. a building: site cleared, excavation, footing, plinth, columns, walls, roof slab, plaster, finishing. A labeller marks only the frames where a stage **begins** (about 10 clicks a video), and every frame inherits its stage. These stage names are also the words of the agency's claims. A vision-language model may draft the marks; a person confirms them. |
| 5 | Split by site, not by frames | **Keep, and tighten** | Correct and essential: frames of one video in both training and test only measure memory. | Also join **re-uploads and second cameras of the same project** into one site before splitting, using a picture match (§6). Keep one uploader's channel in one split, because a channel's camera, watermark and style are shortcuts. |
| 6 | Look at the final scene and walk backwards to judge what contributed to the final structure | **Keep the hindsight; change the test** | "Looks more like the final scene" fails on covered work, which the note itself noticed: tile over cement, plaster over brick, cladding over a frame, earth backfilled over a footing. | **Hindsight labels** (§5.1). The labeller sees the whole video and asks "did this place ever go back to how it was?", not "does it look like the end?". A **two-frame student** then learns to give the same answer from only two frames, which is all a monthly visit has. |
| 7 | Use human activity to judge what is progressing, instead of removing it | **Reject as a judge; keep as a check on labels** | Activity is not progress, and it is the easiest thing to stage on filming day. A model that learned "people working there means progress" would reward a crowd brought for the camera. | People are masked from the model's input. Where they worked is kept as **metadata only**: in a fixed timelapse, a permanent change with no activity before it points to a labelling error (§5.3). |
| 8 | Learn the tools and ways of working, then read progress from what people do | **Reject for this goal** | It needs large labelled activity datasets and a long chain (tool, then activity, then progress), and every step adds error. It still fails on a staged site. | Reuse what exists: the open SODA and MOCS datasets already label workers, machines, scaffolds and material stacks. They are good for the **mask** (§4.4), not as the judge. |

## 3. The design in one picture

```
 sources ─► manifest ─► fetch ─► shots ─► frames ─► align ─► masks ─► features
 (licensed)  (one row     (sha256)  (static   (daylight, (one view) (people, cars, (frozen
             a video)               camera)    sharp)               overlays)       backbone)
                                                                                      │
          ┌───────────────────────────────────────────────────────────────────────────┘
          ▼
   hindsight teacher ──► pairs (A,B) with labels ──► augment ──► splits by site ──► "tuned dataset"
   (sees the whole        progress / none / unknown,   (§4.5)       (§6)               (shards + JSONL)
    video)                per patch and per pair                                           │
          + stage marks (a person, §5.2)                                                   │
          + synthetic pairs (§5.4)                                                         ▼
                                                    student: two frames ─► progress map, progress yes/no,
                                                    (frozen backbone + small head, §7)    stage, "can't tell"
```

## 4. Data

### 4.1 Sources, best first

| Source | Why | Licence |
|---|---|---|
| **Our own phone videos** (T126 sites and teammates' local works, with permission) | The deployed setting itself: Indian public works, handheld, monthly | Ours. Faces blurred; never in git. |
| **Creative Commons timelapses on YouTube** (the Data API's `videoLicense=creativeCommon` search; queries in English and Hindi: "house construction timelapse", "CC road construction", "मकान निर्माण टाइमलैप्स") | Thousands of builds, many Indian | CC BY. **Downloading is the owner's decision** (YouTube's terms are separate from the CC licence), so it is off by default. |
| **Wikimedia Commons** and university construction cameras (Cambridge, Melbourne, UMass, Illinois publish their own building timelapses) | Free to download, licence stated per file | CC / public domain, per file |
| **iVISION-2DCD** (2026): synthetic image pairs rendered from LiDAR scans of real sites, with exact change maps | Exact change maps, across viewpoints | Check before use |
| **SODA, MOCS** | Training or choosing the mask model (workers, machines, scaffolds, materials) | Per dataset |

### 4.2 The manifest (what enters git)

Videos and frames **never** enter git (the repo is public, AGENTS.md rule 6). Git holds only `manifest.jsonl`, with
one row a video: source URL, licence, attribution, uploader channel, site id, work type, country, camera (fixed /
handheld / drone), and the sha256 of the file. It also holds the labels and the code. The frames live in the team
Drive and in a private Kaggle dataset. A row whose licence is not on the allow-list is refused by the code.

### 4.3 From video to clean frames

1. **Shots:** a timelapse posted online is edited: title cards, drone passes, zooms, cuts between cameras. A frame
   that cannot be aligned onto the one before it starts a new shot (light and passers-by never break that alignment;
   a cut, a title card or a knocked camera does). Only shots from a **still camera**, long enough to show change, are kept. Order
   within a shot is the only "time" used, so no dates are needed.
2. **Frames:** about 200 a shot, spread evenly; dark, blurred and night frames are dropped.
3. **Align:** every frame of a shot is matched onto one reference frame, which removes camera shake. Feature points
   are spread over the whole frame (so fresh brickwork cannot drown out the still background), and a still camera's
   shake is fitted as a shift, rotation and zoom (more reliable from few points than a full homography). A frame that
   cannot be aligned is dropped.
4. **Overlays:** dates, logos and watermarks burned into the picture would let the model **read the date** instead of
   seeing the building. They are found as places that stay pixel-identical, or flicker like digits, while the scene
   behind them changes. They are masked, and the corners are randomly blanked in training as well.

### 4.4 People, vehicles, machines: masked, never repainted

- **Median of neighbours:** a short temporal median removes anything that moves between frames, with no model.
- **Mask model:** a detector for people, vehicles and machines (COCO classes; or one trained on MOCS) marks what
  stays put. The masked patches are left out of the loss, and dropped at inference.
- The masks are kept as metadata: activity heatmaps used only to check labels (§5.3).

### 4.5 Augmentation, each with its reason

| Augmentation | Teaches the model |
|---|---|
| Different crop, zoom, small rotation and perspective for frame A and frame B | A handheld phone never stands in the same spot twice |
| Brightness, contrast, white balance, gamma; a shadow band pasted in; haze, rain streaks | Light and weather are not progress |
| Phone-like damage: JPEG, blur, noise, low resolution | Cheap phones and bad days |
| Corners and overlay boxes blanked | Never read the date |
| **People, vehicles, scaffolds and brick stacks pasted into frame B only (label: no progress)** | Dressing up the site is not progress (T120 §9.6) |
| A and B swapped (label flips) | Progress has a direction: the model must not just detect "different" |
| Short-gap pairs: neighbouring frames, which the teacher mostly finds unchanged (label: none) | Morning and evening differ; the building did not |

## 5. Labels

### 5.1 The hindsight teacher: irreversible change

The teacher is a fixed rule, not a model. It works on a grid of patches, using features from a frozen pretrained
backbone (DINOv2), which are steady under lighting changes. For frames `t1 < t2` and a patch `p`:

- **changed:** the patch at `t2` differs from `t1` by more than a threshold;
- **reverted:** at some later frame `t ≥ t2` the patch is again close to how it was at `t1`;
- **progress:** changed and never reverted;
- **temporary:** changed and reverted (scaffolding, stacked materials, a parked machine, a puddle);
- **unknown:** too close to the end of the shot to know whether it reverts, or masked in too many later frames.

Two thresholds, with a gap between "changed" and "back to how it was", so noise cannot flip a label. Both come from
each shot's own noise: `lo` is twice the 75th percentile of the distances between frames 3 to 5 apart (light, shadows
and small shifts; real work rarely shows in so short a gap), and `hi` is twice `lo`. On synthetic builds it comes
within 0.02 IoU of the best fixed value, and it adapts to a backbone or a camera without retuning.

A pair is a **progress pair** when its progress patches cover more than a small share of the visible view. It is a
**no-progress pair** when none do. Anything in between is left out.

Two known limits, measured on synthetic builds where the truth is known (§9):
- **Buried work:** a footing backfilled with earth can look like the ground it started as, so it reads "reverted".
  Stage marks (§5.2) overrule the pair label here. The monthly visit in the footing month still shows the footing.
- **Scaffolding with a wall behind it:** when the scaffold comes down a wall is there, so the scaffold's place reads
  as progress. That is mostly right (the building rose), with some noise at the edges.

### 5.2 Stages (the text labels)

A short list per work type, matched to how agencies word their claims:

| Work type | Stages |
|---|---|
| Building (community hall, school room, anganwadi) | cleared · excavated · footing · plinth · columns · walls to lintel · roof slab · plaster · finishing |
| CC road | cleared · earthwork · sub-base · base · concrete laid · joints and shoulders |
| Drain | excavated · bed concrete · walls · cover slabs |
| Boundary wall | foundation · wall · coping and plaster |

A labeller marks where each stage **begins** in each shot. The stage index can only go up, so a **later stage at `t2`
than at `t1` makes the pair a progress pair**, whatever the patches say (this covers buried work). The labelled stages
also train the stage head, which gives check 6 its stage reading.

### 5.3 Checking the labels

- Activity heatmaps: a permanent change in a fixed timelapse with no people or machines anywhere near it before it
  is suspicious, and those pairs are sent to a person.
- 50 pairs per construction type are checked by eye before training; the agreement is recorded.

### 5.4 Synthetic pairs

From "The Change You Want to See" (Sachdeva and Zisserman, WACV 2023): make pairs whose change is known exactly.

- **Progress with an exact mask:** take a later frame and remove one built element with an inpainting model, then use
  (inpainted, original) as (before, after). Inpainting is fine here, because it makes a training *input* whose label
  we know. What we never do is clean a real input.
- **Fake progress:** paste people, machines, material stacks and shadows into frame B only. Label: no progress.

## 6. Splits

1. **Join duplicates into sites:** shots from different videos that show the same place (re-uploads, a second
   camera on the same project) are found by matching their frames. They are joined into one site.
2. **Group by site and by channel:** a site, and all sites of one uploader, are in one split only.
3. **Folds:** about 70 / 15 / 15 of sites for train / calibration / test, balanced by work type.
4. **Leave-one-type-out:** train on every type but one, then test on that type (wood, RCC frame, masonry, steel, road).

## 7. The model

- **Backbone, frozen:** DINOv2 ViT-B/14 with registers (Apache-2.0). Its patch features already separate materials and
  shapes well, and they hold steady under lighting. DINOv3 (2025, its own licence) is the first alternative to try.
- **Head, trained (about 1.9 million weights on DINOv2-B):** both frames' patch features, with their positions, go
  through 2 joint-attention layers, so each patch of B can find its matching patch in A even when the phone moved.
  Each patch of B also gets its difference from A's patch at the same place, the strongest cue once aligned.
- **Outputs:**
  1. a **progress map**: for each patch, permanent structure added;
  2. **progress yes / no** for the pair, with a calibrated probability, leaning on the map (a soft maximum over its
     patches), so every "yes" points at where;
  3. a **build-up score** for each frame (higher means more built), trained by ordering;
  4. the **stage** of each frame;
  5. **can't tell**, when the views barely overlap, the alignment is weak or the probability is in the middle band.
- **Training, in four steps:**
  1. **Ordering, with no labels** ("Made to Order", Yang, Xie and Zisserman, ECCV 2024): shuffle 4 frames of a shot
     and ask for their order. Only changes that grow with time make ordering possible; light cycles and passers-by
     cannot. This is the owner's "how slowly something is built" idea, made precise.
  2. **Hindsight:** the student, seeing only two frames, learns the teacher's progress map and pair label.
  3. **Synthetic pairs** mixed in, about one in four.
  4. **Stages**, on the labelled set; temperature calibration on the calibration split.
- **Size, chosen by measurement:** (a) a probe on frozen features (no attention between frames, 0.34 million
  weights); (b) the small head; (c) the head plus LoRA adapters on the backbone's last 4 blocks (about 0.1 million
  more weights). The winner is chosen on held-out sites.

## 8. Measuring it

### 8.1 Numbers to report (each on held-out sites)

| What | Measure | Target to ship |
|---|---|---|
| Progress yes / no | AUROC; accuracy where it answers; how often it answers | AUROC ≥ 0.90 |
| Where | IoU of progress maps, on a hand-masked subset | reported |
| Build-up over a shot | Kendall's tau between the score and frame order | ≥ 0.8 |
| Stage | macro-F1 | reported |
| Lighting only (same-day pairs) | share called progress | ≤ 2% |
| Dressed-up site (pasted people, machines, stacks) | share called progress | ≤ 2% |
| Swapped pairs | share where both directions are called progress | ≤ 1% |
| Leave-one-type-out | AUROC on the held-out type | within 0.05 of the in-type AUROC |

### 8.2 Overfitting, measured

- **Train vs held-out gap:** the same metric on training sites and held-out sites. A large gap means memorising.
- **The held-out type:** the test of whether it learned "construction" or "wooden houses".
- **Shortcut tests:** with the corners blanked, with B's colours shifted, and with the time gap randomised, the score
  must not move. If it does, the model is reading the date, the season or the camera.

### 8.3 The real test: DRISHTI's own visits (T126)

The internet set trains it; **only real monthly visits of Indian works decide whether it ships** (AGENTS.md rule 4):
each planted trick caught 9 in 10, and a finding on at most 1 in 30 honest visits. Until then the model's readings are
stored and shown to officers as notes, and never counted.

## 9. Built in this task (T146), and what follows

**T146 (this task):** the pipeline and its tests, `apps/vision/`:
- manifest with a licence allow-list; fetching with sha256;
- shots, frames, alignment, overlay masks;
- the hindsight teacher; pairs; site-grouped and leave-one-type-out splits; augmentation;
- a **synthetic timelapse generator** with exact ground truth (five construction types, people, machines, scaffolds,
  material stacks, light and shadows, camera shake, date overlays, covered work and buried work);
- the model and training code (PyTorch), the evaluation with every audit in §8, and a Kaggle runner.

It is measured on synthetic builds only. That measures whether the **teacher's labels** are right where the truth is
known, and whether the training code learns. It says nothing yet about real-world accuracy.

Not built in T146, and why:
- **Progress pairs made by inpainting** (§5.4, first kind): they need an inpainting model, which runs on the GPU (T148).
  The "fake progress" kind (pasted people, machines, scaffolds, stacks) is built (`augment.paste_transients`).
- **Temperature calibration:** the calibration error is measured (`ece`); fitting the temperature waits for real
  calibration sites (T148).
- **"Can't tell" from weak alignment or small overlap:** the probability band is built (`evaluate.selective`); the
  alignment and overlap checks join when the model is wired into Site Progress (T149).

**Next:**
- **T147, collect (human-task, owner decision on sources):** about 300 shots from about 150 sites, at least 30 Indian
  public works, and 5+ work types. Stage marks for the calibration and test sites.
- **T148, train on Kaggle's free GPU** (about 30 hours a week): the three sizes, every §8 number, the result files.
- **T149, wire into Site Progress** behind a switch, as check 5's reading and check 6's stage. It stays off until
  T126's real visits meet §8.3.

**Compute and cost:** CPU for steps up to the features. Kaggle's free GPU for feature caching and training: a frozen
backbone means each frame is encoded once, so training reads cached features and runs in minutes. No paid service.

## 10. References

- Sachdeva, R. and Zisserman, A. "The Change You Want to See." WACV 2023. Synthetic change pairs by inpainting.
- Yang, C., Xie, W. and Zisserman, A. "Made to Order: Discovering monotonic temporal changes via self-supervised video
  ordering." ECCV 2024. Ordering finds changes that grow with time and ignores cyclic and random ones.
- Oquab, M. et al. "DINOv2: Learning Robust Visual Features without Supervision." 2023. The frozen backbone.
- iVISION-2DCD: a long-term change detection dataset for construction monitoring (2026).
- SODA (Site Object Detection dAtaset) and MOCS (Moving Objects in Construction Sites): open construction detection
  sets, for the masks.
- OpenConstruction: a catalogue of 51 open construction datasets (Xiong et al., 2026).
