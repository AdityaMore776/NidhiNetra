-- DRISHTI core schema, M0.
--
-- Lean on purpose: the free database holds 500 MB and the real corpus is
-- about 2.1 lakh works. Only the engine reads these tables (RLS on, no
-- policies), so the public Supabase API cannot see any of them.

CREATE TABLE IF NOT EXISTS districts (
    district_lgd   text PRIMARY KEY,
    name           text NOT NULL,
    state_lgd      text,
    state_name     text
);

CREATE TABLE IF NOT EXISTS works (
    work_id                  text PRIMARY KEY,
    source                   text NOT NULL CHECK (source IN ('REAL', 'SCENARIO', 'LIVE')),
    house                    text,
    term                     text,
    state_lgd                text,
    state_name               text,
    district_lgd             text,
    district_name            text,
    constituency             text,
    mp_name                  text,
    agency_name              text,
    fy                       text,
    work_type_code           text,
    category                 text,
    description              text,
    amount                   numeric,
    recommended_date         date,
    completed_date           date,
    status                   text,
    quantity                 numeric,
    quantity_unit            text,
    is_outside_constituency  boolean NOT NULL DEFAULT false
);
CREATE INDEX IF NOT EXISTS works_district_idx ON works (district_lgd);
CREATE INDEX IF NOT EXISTS works_type_idx ON works (work_type_code);

-- Peer-cost bands, computed offline by data/build_stats.py.
-- level: type_district | type_state | type ; key: district_lgd | state_lgd | ''
CREATE TABLE IF NOT EXISTS cohort_stats (
    level           text NOT NULL,
    work_type_code  text NOT NULL,
    key             text NOT NULL,
    n               integer NOT NULL,
    p10             double precision NOT NULL,
    p50             double precision NOT NULL,
    p90             double precision NOT NULL,
    sd              double precision NOT NULL,
    PRIMARY KEY (level, work_type_code, key)
);

CREATE TABLE IF NOT EXISTS duration_stats (
    work_type_code  text PRIMARY KEY,
    n               integer NOT NULL,
    p50             double precision NOT NULL,
    p90             double precision NOT NULL,
    p98             double precision NOT NULL
);

CREATE TABLE IF NOT EXISTS unit_rate_models (
    work_type_code  text PRIMARY KEY,
    unit            text NOT NULL,
    n               integer NOT NULL,
    slope           double precision NOT NULL,
    intercept       double precision NOT NULL,
    resid_sd        double precision NOT NULL,
    anchor_low      double precision,
    anchor_high     double precision,
    anchor_label    text
);

-- The latest assessment of each work. Full agent evidence is kept here as
-- JSON; for the ~2 lakh real works this is small because unflagged works
-- carry a short result.
CREATE TABLE IF NOT EXISTS assessments (
    work_id      text PRIMARY KEY REFERENCES works (work_id) ON DELETE CASCADE,
    assessed_at  timestamptz NOT NULL DEFAULT now(),
    score        double precision NOT NULL,
    band         text NOT NULL CHECK (band IN ('HIGH', 'MEDIUM', 'LOW')),
    limited      boolean NOT NULL DEFAULT false,
    priority     double precision NOT NULL DEFAULT 0,
    parts        jsonb NOT NULL,
    validation   jsonb NOT NULL,
    agents       jsonb NOT NULL,
    versions     jsonb NOT NULL
);
CREATE INDEX IF NOT EXISTS assessments_band_idx ON assessments (band, priority DESC);

CREATE TABLE IF NOT EXISTS profiles (
    user_id       uuid PRIMARY KEY,
    role          text NOT NULL CHECK (role IN ('MINISTRY', 'DISTRICT', 'FIELD')),
    district_lgd  text,
    display_name  text
);

ALTER TABLE districts ENABLE ROW LEVEL SECURITY;
ALTER TABLE works ENABLE ROW LEVEL SECURITY;
ALTER TABLE cohort_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE duration_stats ENABLE ROW LEVEL SECURITY;
ALTER TABLE unit_rate_models ENABLE ROW LEVEL SECURITY;
ALTER TABLE assessments ENABLE ROW LEVEL SECURITY;
ALTER TABLE profiles ENABLE ROW LEVEL SECURITY;
