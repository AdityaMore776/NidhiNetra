-- Saved dashboard answers (summary, districts, offices) per scope. Aggregating 2.1 lakh
-- works took 4-9 s per request on the hosted database, so the page sat on "Loading".
-- Filled on first request; emptied whenever works are re-assessed (drishti/batch.py).
CREATE TABLE IF NOT EXISTS dashboard_cache (
    key          text PRIMARY KEY,
    payload      jsonb NOT NULL,
    computed_at  timestamptz NOT NULL DEFAULT now()
);
ALTER TABLE dashboard_cache ENABLE ROW LEVEL SECURITY;
