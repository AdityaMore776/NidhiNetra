# T173: NidhiLens on photos alone, and a data-leak check first

**The owner, 21 Oct 2026:** "If they are allowed to write a prompt, there are ways for it to be prompt injected."
Next session: test whether NidhiLens can judge progress **from the before and after photos alone**, with no text
written by the agency anywhere in its prompt. **Before any new number:** check for a data leak: the model must not
have seen the test construction-site photos, or their answers, before.

Why: today (T172) the agency's free-text claim goes into NidhiLens's prompt word for word. T172 blocks known
instruction words (`readers.instructs_reader`), but a word list only stops tricks someone thought of; any free text
in a prompt can be injected (registry `M-SITE-8`). Photos alone remove the channel.

Order: **part 1 (leak) first, then part 2.** If part 1 finds a leak, every NidhiLens figure so far (macro-F1 0.935 on
883, T168, T172) is re-scored without the leaked checks, and FINDINGS says so plainly.

## Where the data is (this PC, D:)

| What | Path | Size |
|---|---|---|
| The adapter (NidhiLens) | `D:\nidhinetra-data\models\q4b\final` | LoRA r16 on Qwen/Qwen3-VL-4B-Instruct |
| Its training run | `D:\nidhinetra-data\models\q4b\train_info.json` | `items` = `/data/vlm/v6/items_eye.jsonl` (Kaggle path), `real_only`, 2,924 items, 731 steps, 2 epochs; loss 0.02 by step 70 |
| The training file | `D:\nidhinetra-data\vlm\v6\items_eye.jsonl` | 5,733 lines: split train 4,663, calib 155, test 915 |
| The test set | `D:\nidhinetra-data\release\siteclaim_test_v1\items_test.jsonl` | 883 (850 geomgnrega, 33 timelapse) |
| Fresh and probe | `...\items_fresh.jsonl`, `...\items_probe.jsonl` | 785 geomgnrega, 93 |
| Photos | `...\siteclaim_test_v1\images\`, `D:\nidhinetra-data\vlm\` (v1-v7, pilot, cutouts) | |
| Split code | `apps/vision/drishti_vision/splits.py` | by site, channel and district (plan T150 §6, H4, H6, H10) |

Each item has `site`, `district`, `source`, `image_a`, `image_b`, `claim`, `label` and `reference_answer`
(`same_place`, `stage_A`, `stage_B`, `permanent_change`, `verdict`, `reason`).

## Part 1: has the model seen the test photos or their answers? (CPU, then a short GPU run)

1. **Which training items were really used.** Re-derive the 2,924 from `items_eye.jsonl` with the training script's
   own filter (split train, `real_only`; find the script in `apps/vision/` or the Kaggle notebook). Every check below is
   between those 2,924 and the 883 + 785 + 93 test items.
2. **The same photo, the same site.** Count test items whose `site` or `district` is also in training (the plan says
   districts never overlap: verify), and whose image file path is in training.
3. **The same picture under another name.** Perceptual hash (pHash) every training and test photo; count pairs within
   Hamming distance 8. Then image embeddings (the split code's signature, cosine >= 0.9 = `splits.SAME_PLACE`) to catch
   crops, resizes and re-uploads. Look at the closest 30 pairs by eye.
4. **The answers.** Did any test `reference_answer` or label also appear as a training target (the same site and
   claim, or text copied word for word)? Were any training labels made by a model (Gemini, `gem_queue.jsonl`) on photos
   that are also in test? Test labels must come from people only (plan T150).
5. **The test set never online.** Not in git (check `git log --all -- '*siteclaim_test*'`), not public on Kaggle,
   not uploaded anywhere but the judged API runs (`release\predictions\`).
6. **Did the base model see them before us?** geomgnrega photos are public government pages, so Qwen3-VL's own
   training may have seen them. We cannot prove it did not; we can test it:
   - the base model with no adapter, same prompt, on the 883 (if it already scores near NidhiLens, the photos may be
     familiar, or the task is easy; either way say so);
   - photos that cannot have been online before Qwen3-VL was released: uploads dated after its release (check
     `items_fresh`'s dates), or the team's own new site photos;
   - memorisation: a training photo pair with its claim removed or the photos swapped; if the model still gives the
     training answer word for word, it memorised.
7. Save to `data/trial/results/t173_leak_check.txt`; FINDINGS "T173". A leak found is reported with the re-scored
   numbers, never hidden.

## Part 2: progress from the photos alone (GPU, ~7-8 s a check, ~2 h for 883)

1. **A prompt with no agency text:** "Photo A is the last visit, photo B this visit. Same place? What stage is the
   work in A, and in B? Any permanent change?" The fine-tuned model already answers these fields (`same_place`,
   `stage_A`, `stage_B`, `permanent_change`) before its verdict, so it may work without retraining: measure first.
   Only the work type (a fixed list from the form's dropdown, never typed) may enter the prompt.
2. **Score on the 883 and the fresh 785** against the people's labels: same-place accuracy, stage accuracy
   (`stage_B` labels: unknown 739, not started 478, complete 451 across test + fresh), change found or not, and the
   verdict the code derives from them. Compare with claim mode (macro-F1 0.907 on the T168 300, 0.935 on 883).
3. **How the agency's claim is then checked without the model reading it:** the agency picks the stage reached from a
   fixed list on the form (no free text to the model); code compares that pick with the model's `stage_B` and
   `permanent_change`. A written note can stay for the officer to read; it never reaches the model.
4. **Re-run the T168/T172 altered photos** in photo-only mode (`data/eval/nidhilens/run.py`): clean, dark, blur,
   swap, same, the sign (with and without greying), chalk. A sign is still a way in through the photo, so the greying
   stays.
5. **Ask the owner before switching the engine** to photo-only (the rule: ask before swapping an agent's whole method),
   with the two modes' numbers side by side.

**Done when:** [ ] leak check saved, any leak re-scored and in FINDINGS · [ ] base model and memorisation probes run
· [ ] photo-only scored on 883 + fresh · [ ] altered photos re-run · [ ] owner's decision on the switch · [ ] registry
(`M-SITE-8`) updated, `check.py` run · [ ] FINDINGS "T173", log
