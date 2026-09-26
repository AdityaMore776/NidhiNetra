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
| `trial/ocr_pages.py` | local OCR of the downloaded evidence |
| `trial/sanitize_results.py` | mask phone/account numbers — run before committing results |

Gitignored (never commit): `raw/`, `build/`, `cache/`, `evidence/`, `trial/cache/`.
