# data/ — offline jobs

Scripts that build the corpus, load and assess it, draw the maps, harvest real eSAKSHI evidence, and run the
real-data trial of every agent. Full description, sources, privacy rules and known traps:
[`docs/DATA.md`](../docs/DATA.md).

| Folder / script | Purpose |
|---|---|
| `build_corpus.py` → `build_stats.py` → `load_db.py` → `batch_assess.py` | the main pipeline, in order |
| `seed_users.py` | demo accounts (passwords printed once) |
| `boundaries.py` → `district_crosswalk.py` | LGD map outlines + Census↔LGD code match |
| `dry_run.py` | assess without a database |
| `with_env.py <script>` | run a script against the hosted DB without printing secrets |
| `harvest/esakshi_evidence.py` | polite downloader for eSAKSHI attachments (1 request / 1.5 s) |
| `trial/*_trial.py` | one script per agent; results in `trial/results/`; write-up in `docs/trial/FINDINGS.md` |
| `esakshi_dashboard.py` | loads the eSAKSHI dashboard's own CSV tables (Recommended, Sanctioned, Completed, Allocated limits; downloaded 2 Oct 2026 into `raw/esakshi_dashboard/`) as work records: 40,935 works with real sanction dates |
| `trial/dashboard_trial.py` | every engine on those 40,935 unseen works (statistics and price model rebuilt from them); `--tag` names the run; by-eye labels in `trial/dashboard_labels.py` |
| `trial/synthetic_eval.py` | every engine on made-up countries with planted, labelled problems (`apps/engine/drishti/evaluation/`): the only recall measurement; `--seeds 11 12 13` |
| `trial/dup_split_rescore.py` | the team's 159 labelled repeat pairs, re-read by main's matcher and the working copy |
| `build_site_observations.py` → `trial/site_progress_trial.py` | Site Progress v2 (T510): read every pilot photo once with free local models (what it shows; the MPLADS plaque and its dates), then run the engine and write the sample to label for its go/no-go |
| `trial/ocr_pages.py` | local OCR of the downloaded evidence |
| `trial/sanitize_results.py` | mask phone/account numbers — run before committing results |

Gitignored (never commit): `raw/`, `build/`, `cache/`, `evidence/`, `trial/cache/`.
