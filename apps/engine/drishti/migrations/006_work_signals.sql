-- Per-work facts computed offline by an engine's data job, read with the work by
-- drishti/batch.py as work["signals"][engine]. Engines that need heavy libraries (the
-- cost model, the delay model, text matching) run offline and store their result here;
-- the engine itself only compares stored values. A work without a row is judged
-- without that input, never as if it had passed.
--   cost_model  {q10, q50, q90}  expected cost range, log10 rupees (data/build_cost_model.py)
CREATE TABLE IF NOT EXISTS work_signals (
    work_id  text NOT NULL REFERENCES works (work_id) ON DELETE CASCADE,
    engine   text NOT NULL,
    data     jsonb NOT NULL,
    version  text NOT NULL,
    PRIMARY KEY (work_id, engine)
);
ALTER TABLE work_signals ENABLE ROW LEVEL SECURITY;
