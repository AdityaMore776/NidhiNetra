-- The officer-facing review workflow: alerts, the inspection planner, and what the
-- field officer saw. Additive only; nothing here changes an assessment or a score.
--
-- 1. profiles      a STATE role, scoped to one state instead of all of India
-- 2. alerts        one open alert per work in the review queue (T060)
-- 3. inspections   the planner (T062): one row per work asked to be visited
-- 4. results       what the field officer recorded (feeds T070's learning loop)
--
-- Wording note: an alert is a *request to look*. The states below say what has
-- happened to that request. None of them is a judgement about anyone.

-- 1. the STATE role ---------------------------------------------------------
ALTER TABLE profiles DROP CONSTRAINT IF EXISTS profiles_role_check;
ALTER TABLE profiles
    ADD CONSTRAINT profiles_role_check
    CHECK (role IN ('MINISTRY', 'STATE', 'DISTRICT', 'FIELD'));
ALTER TABLE profiles ADD COLUMN IF NOT EXISTS state_lgd text;

-- 2. alerts -----------------------------------------------------------------
-- Opened by data/batch_assess.py when a work's band is CRITICAL or HIGH, and
-- closed when the work leaves the queue on a later run. One open alert per work,
-- so re-assessing never multiplies an officer's list.
CREATE TABLE IF NOT EXISTS alerts (
    alert_id    bigserial PRIMARY KEY,
    work_id     text NOT NULL REFERENCES works (work_id) ON DELETE CASCADE,
    code        text NOT NULL,
    engine      text,
    state       text NOT NULL DEFAULT 'NEW'
                CHECK (state IN ('NEW', 'ACKNOWLEDGED', 'INVESTIGATING', 'RESOLVED')),
    opened_at   timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now(),
    closed_at   timestamptz,
    actor       text,
    note        text
);
CREATE UNIQUE INDEX IF NOT EXISTS alerts_one_open_per_work
    ON alerts (work_id) WHERE state <> 'RESOLVED';
CREATE INDEX IF NOT EXISTS alerts_state_idx ON alerts (state, opened_at DESC);

-- 3. inspections ------------------------------------------------------------
-- The six steps of the operational loop:
--   REVIEW -> INSPECTION_REQUIRED -> ASSIGNED -> FIELD_VERIFIED
--          -> RESULT_RECORDED -> CLOSED
-- A work may be asked to be inspected without an alert being opened (an officer
-- may choose any work), so this table stands on its own.
CREATE TABLE IF NOT EXISTS inspections (
    inspection_id bigserial PRIMARY KEY,
    work_id       text NOT NULL REFERENCES works (work_id) ON DELETE CASCADE,
    district_lgd  text,
    state_lgd     text,
    band          text CHECK (band IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW')),
    state         text NOT NULL DEFAULT 'REVIEW'
                  CHECK (state IN ('REVIEW', 'INSPECTION_REQUIRED', 'ASSIGNED',
                                   'FIELD_VERIFIED', 'RESULT_RECORDED', 'CLOSED')),
    assigned_to   text,
    due_date      date,
    priority      double precision,
    note          text,
    created_at    timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now()
);
CREATE UNIQUE INDEX IF NOT EXISTS inspections_one_per_work ON inspections (work_id);
CREATE INDEX IF NOT EXISTS inspections_state_idx
    ON inspections (state, priority DESC NULLS LAST);
CREATE INDEX IF NOT EXISTS inspections_district_idx ON inspections (district_lgd);

-- 4. field results ----------------------------------------------------------
-- The four answers a field officer may give. UNABLE_TO_VERIFY is a real answer
-- and carries no finding either way, exactly like NOT_ASSESSABLE in an engine.
CREATE TABLE IF NOT EXISTS inspection_results (
    result_id     bigserial PRIMARY KEY,
    inspection_id bigint NOT NULL REFERENCES inspections (inspection_id) ON DELETE CASCADE,
    outcome       text NOT NULL CHECK (outcome IN ('OBSERVED', 'NOT_OBSERVED',
                                                  'PARTIALLY_OBSERVED', 'UNABLE_TO_VERIFY')),
    observed      text,
    lat           double precision,
    lon           double precision,
    gps_source    text,
    evidence      jsonb,
    recorded_by   text,
    recorded_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS inspection_results_idx ON inspection_results (inspection_id);

ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE inspections ENABLE ROW LEVEL SECURITY;
ALTER TABLE inspection_results ENABLE ROW LEVEL SECURITY;
