r"""Read the uploaded site videos once, keep the readings, delete the videos (T124).

Runs on a machine with OpenCV (data/requirements-video.txt), never on the live engine:

    python -m venv .venv-video
    .venv-video\Scripts\pip install -r data\requirements-video.txt -e apps\engine
    .venv-video\Scripts\python.exe data\with_env.py build_site_visits.py

Needs DATABASE_URL, SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY (storage). GEMINI_API_KEY
(optional, the owner's free key) lets the claims be judged; without it they stay "not judged".
--store DIR reads videos from, and writes frames to, a local folder instead (trials only: never
put real videos in the repository). Each work with a newly read visit is re-assessed.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import psycopg
from psycopg.rows import dict_row

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "engine"))
from drishti import batch, capture, config  # noqa: E402
from drishti.agents.statistical.cohort import StatsStore  # noqa: E402
from drishti.pipeline.orchestrator import Context  # noqa: E402
from drishti.video import job  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--store", help="a local folder instead of Supabase Storage (trials)")
    ap.add_argument("--limit", type=int, default=200)
    ap.add_argument("--cap", type=int, default=200, help="claim reader calls a day")
    args = ap.parse_args()
    store = capture.LocalStore(args.store) if args.store else capture.SupabaseStore()
    judge = None
    try:
        # the fine-tuned claim judge (T156) when DRISHTI_VLM_ADAPTER names one, else Gemini
        from drishti.agents.site_progress.readers import GeminiReader, VLMReader
        try:
            judge = VLMReader().judge
        except ValueError:
            judge = GeminiReader(daily_cap=args.cap,
                                 ledger=ROOT / "data" / "build" / "gemini_ledger.json").judge
    except ValueError:
        print("no DRISHTI_VLM_ADAPTER or GEMINI_API_KEY: claims stay 'not judged'; every other "
              "reading is made")
    url = config.database_url()
    with psycopg.connect(url, row_factory=dict_row, prepare_threshold=None) as con:
        done = job.process(con, store, judge, args.limit)
        ctx = Context(stats=StatsStore.load(url), as_of=config.snapshot_date())
        for work_id in sorted({d["work_id"] for d in done if d["status"] == "read"}):
            batch.assess_one(con, work_id, ctx)
        con.commit()
    for d in done:
        print(f"{d['visit_id']}  {d['work_id']}  {d['status']}  {d['note'] or ''}")
    print(f"{len(done)} visits: {sum(d['status'] == 'read' for d in done)} read, "
          f"{sum(d['status'] == 'rejected' for d in done)} rejected")


if __name__ == "__main__":
    main()
