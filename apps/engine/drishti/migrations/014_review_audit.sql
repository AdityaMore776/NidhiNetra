-- Provenance for the review loop, so a work's page can say when each step happened
-- and who did it, instead of guessing. Additive only: no column here feeds a score.
--
-- Why a new migration rather than more of 013: a teammate may already have run 013
-- against their local database, and migrations that only ever get added to are the
-- ones that stay replayable.

-- who asked for the visit, and who is accountable for it
ALTER TABLE inspections ADD COLUMN IF NOT EXISTS requested_by text;
ALTER TABLE inspections ADD COLUMN IF NOT EXISTS assigned_by text;

-- the real moment each step was reached, filled in as it happens
ALTER TABLE inspections ADD COLUMN IF NOT EXISTS requested_at  timestamptz;
ALTER TABLE inspections ADD COLUMN IF NOT EXISTS assigned_at   timestamptz;
ALTER TABLE inspections ADD COLUMN IF NOT EXISTS verified_at   timestamptz;
ALTER TABLE inspections ADD COLUMN IF NOT EXISTS recorded_at   timestamptz;
ALTER TABLE inspections ADD COLUMN IF NOT EXISTS closed_at     timestamptz;

-- an officer may only re-open a visit if they say why
ALTER TABLE inspections ADD COLUMN IF NOT EXISTS history jsonb NOT NULL DEFAULT '[]'::jsonb;

-- the alert a visit was opened from, so the two screens can be tied together
ALTER TABLE inspections ADD COLUMN IF NOT EXISTS alert_id bigint REFERENCES alerts (alert_id);
CREATE INDEX IF NOT EXISTS inspections_alert_idx ON inspections (alert_id);