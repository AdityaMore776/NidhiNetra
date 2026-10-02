# T510 · Site Progress v2: free local photo readers, the record's own words, off until measured (2 Oct 2026)

**Asked (owner, 2 Oct 2026):** "explore and create the site progress agent architecture".
**The question it answers:** *do this work's photos show what its record says was built?*
Answers are **shown / not shown / can't tell**, judged on the record's and the officer's own words, never a
fixed checklist (AGENTS.md section 8). "Can't tell" is never a finding.

## 1. Why v1 never ran

v1 (T510 frame, 1 Oct 2026) had the right rules but one reader slot, for a paid AI vision key. With no key it
said "cannot be assessed" on every work with photos, so T053 removed it. FINDINGS B1 said "nothing in the free
local toolset judges *does this photo show a finished road*". That is no longer true: open CLIP-family models
name what a photo shows, run on a CPU, and cost nothing. They cannot count, measure or read a sentence like "roof
slab cast", so v2 uses each reader only for what it can do.

## 2. The design

```
 OFFLINE, once per photo (cached by SHA-256)            LIVE, in the engine, for any work
 data/build_site_observations.py                        agents/site_progress/agent.py
 ┌──────────────────────────────────────────┐          ┌───────────────────────────────────────────┐
 │ ZeroShotReader (open CLIP, CPU, free)     │ reading  │ claims.py: the record's own words          │
 │   scores the photo against every line of  │────────► │   asset   (completed work: type + quoted   │
 │   reference/site_concepts.yaml            │ stored   │            description)                    │
 │ RapidOCR on the whole photo -> plaque.py  │ in       │   length / count (as described)            │
 │   scheme named? start / completion dates  │ evidence │   field   (the officer's notes, T063)      │
 │ GeminiReader (optional, owner's free key) │ facts    │ Photo Evidence's facts void photos that    │
 │   judges each claim: shown / not / can't  │          │   are reused, outside the district, or     │
 └──────────────────────────────────────────┘          │   stamped before the recommendation        │
   keeps readings only: no picture, no text,            │ judge: shown / not shown / can't tell      │
   no names                                             │ findings -> AgentResult (weight 0, off)    │
                                                        └───────────────────────────────────────────┘
```

Why offline readers: a model is too big and too slow for the live API (Vercel), and T051's rule holds. The job
stores what a photo *shows* (scores for every kind of asset, independent of the work it is attached to). The
engine decides what that means for a work, live. A work whose type is corrected later is judged again against
the same readings.

## 3. Readers, and what each may say

| Reader | Free? | Can say | Cannot say |
|---|---|---|---|
| **Zero-shot** (`readers.ZeroShotReader`, open_clip ViT-B-32 / LAION-2B by default) | yes, local CPU | which kind of thing a photo shows: a finished CC road vs a dirt track, a roofed building vs an empty plot or bare walls, a pond vs dry land; "a document / a meeting / a map" (not a site photo) | counts, lengths, "roof slab cast", quality |
| **Plaque text** (`plaque.py` over RapidOCR of the whole photo) | yes, local | the MPLADS plaque is in the photo; its start / completion dates | Hindi plaques (RapidOCR reads Latin script only); amounts (not kept) |
| **Vision-language** (`readers.GeminiReader`, T501) | free tier, **owner's key** | any claim in words: "roof slab cast" → not shown, with a reason | nothing without a key: it is simply not run |

The concept lines are data (`reference/site_concepts.yaml`), not code. For lights, pumps, goods and grounds the
asset may just be out of frame. Those groups have no "not built" lines, so a photo there can only show the asset
or leave it "can't tell".

## 4. The rules (`agent.py`)

| Answer | When | Finding |
|---|---|---|
| asset **shown** | any usable photo reads "shows" (the asset takes ≥ 50% of the photo's score) | none |
| asset **not shown** | recorded complete; ≥ 2 usable photos read "not built" (unbuilt site ≥ 70%, asset ≤ 15%); none shows it; neither is a progress photo stamped 30+ days before completion; the group can be absent in a photo | `ASSET_NOT_SHOWN` 0.40: "Recorded complete, but none of the N usable site photos shows the community hall; 2 read as an unbuilt site. Needs a site check before the work is closed." |
| claim **not shown** | a vision-language reader judged the claim "not shown" | `CLAIM_NOT_SHOWN` 0.40, with the reader's reason (dropped if it is not plain language) |
| plaque dated early | a plaque naming the scheme gives a start or completion date 7+ days before the recommendation (the Chittaurgarh wall in FINDINGS B3) | `PLAQUE_DATED_BEFORE_RECOMMENDATION` 0.40 |
| no plaque seen | no usable photo shows one | a fact in the headline ("ask for one at inspection"), never a finding |
| photo voided | Photo Evidence's facts: same file / picture on another work, GPS stamp 5+ km outside the district, stamped 7+ days before the recommendation | none here (Photo Evidence reports it); the photo confirms nothing and counts against nothing |
| statuses | no photo → NOT_APPLICABLE; photos never read → NOT_ASSESSABLE; both say "not a clean chit" | |

The cut-offs (50% / 70% / 15%, 2 photos, 30 days) are set by design and are measured below before anything is
switched on.

## 5. Proof before launch: the go / no-go

`data/trial/site_progress_trial.py` runs the engine on every pilot work (837 works; 321 photos in the pilot)
and writes a sample to label by eye: every photo of a work with a finding, plus 20 random photos per reading. It
also writes a one-page contact sheet (`data/build/site_progress_sheet.html`, gitignored). A person labels each
photo (`data/trial/site_progress_labels.py`): shows / not built / can't tell, and each finding: worth a site
check yes / no. Then:

- **GO** when "not built" readings are right ≥ 80% (≥ 20 labelled), "shows" right ≥ 80% (≥ 20), and findings
  worth a site check ≥ 70% (≥ 10 works). Then `DRISHTI_SITE_PROGRESS=on` in the batch; still weight 0 (shown,
  not counted) until officer verdicts (T070) give it a measured hit rate in `reliability.json`.
- **NO-GO** otherwise. The trial prints a sweep of the "not built" cut-off to show whether another cut-off would
  pass, and FINDINGS says why it stays off.

The decisive test from T503 ("roof slab cast" with walls and no roof → not shown) is a unit test with a stand-in
vision-language reader. On real photos it needs field notes (T063) or the owner's key.

## 6. What was checked in this session (2 Oct 2026)

- 34 unit tests (`tests/agents/site_progress/`): the stored reading, the per-photo reading, claims, plaque text
  (including RapidOCR's own glued output, "MPLADS2023-24 … DATEOFCOMPLETION:31/12/2023"), every rule above, the
  void rules, the decisive test, the engine off by default, and the Gemini reader's cache, daily cap and key
  handling (a fake transport; the key travels in a header, never in a URL).
- A smoke test of the whole offline path in a scratch venv: real RapidOCR on a drawn plaque, a stand-in for the
  CLIP model, the job writing readings into `evidence_facts.parquet`, the engine raising
  `PLAQUE_DATED_BEFORE_RECOMMENDATION`, and the trial writing its sample and sheet. That run found the glued-OCR
  bug, now fixed and covered by a test.
- **Not measured: no real photo was read.** The pilot photos are in the owner's data pack, and this session's
  network blocks the model hub (huggingface.co), so the CLIP weights could not be fetched here. Nothing on the
  live site changes: the engine is off.

## 7. How to run it (owner's machine, PowerShell, from the `drishti` folder)

```powershell
# once: the model and OCR libraries in the trial venv (a few hundred MB; CPU only)
.venv-trial\Scripts\python.exe -m pip install open_clip_torch torch rapidocr_onnxruntime
# 1. read every pilot photo (minutes on a laptop; cached, so re-runs are quick). --limit 20 for a first try
.venv-trial\Scripts\python.exe data\build_site_observations.py
# 2. run the engine on the pilot and write the sample to label
apps\engine\.venv\Scripts\python.exe data\trial\site_progress_trial.py
# 3. open data\build\site_progress_sheet.html, fill data\trial\site_progress_labels.py, run step 2 again
# optional, with the owner's free-tier Gemini key (T501): judge the claims in words too
$env:GEMINI_API_KEY="<key>"; .venv-trial\Scripts\python.exe data\build_site_observations.py --vlm --cap 200
```

## 8. Open

- **Model choice:** ViT-B-32 / LAION-2B is small and runs anywhere. A SigLIP model (`--model ViT-B-16-SigLIP
  --pretrained webli`) is usually better at zero-shot; compare both on the labelled sample.
- **Hindi plaques:** RapidOCR's bundled models read Latin script. A Devanagari OCR, or the Gemini reader, is
  needed for "सांसद निधि" plaques.
- **Photo sheets inside PDFs** (several photos printed on one page) are not read yet; only photo files are.
- **Field notes** (T063 field app) are the claims T503 had in mind: the engine already reads `work["field_notes"]`.
- **Satellite (B5)** stays a separate go/no-go (T604): v1's eligibility gate is not carried over until that test
  exists.
