-- Site visits: one row per filmed visit of a work (T123 capture page, T124 Site Progress v3;
-- plan docs/plans/T120-four-agents.md §9). The video goes to storage, is read once by the site
-- video job (data/build_site_visits.py) and then deleted: what stays is the capture log (no
-- video), the readings Site Progress judges, and the kept viewpoint frames (faces blurred).
CREATE TABLE IF NOT EXISTS site_visits (
    visit_id     text PRIMARY KEY,
    work_id      text NOT NULL REFERENCES works (work_id) ON DELETE CASCADE,
    kind         text NOT NULL CHECK (kind IN ('baseline', 'monthly', 'check', 'final')),
    status       text NOT NULL DEFAULT 'started'
                 CHECK (status IN ('started', 'uploaded', 'read', 'rejected')),
    claim        text,
    started_at   timestamptz NOT NULL DEFAULT now(),
    captured_at  timestamptz,
    uploaded_at  timestamptz,
    read_at      timestamptz,
    saved_by     text,
    video_path   text,
    video_sha256 text,
    log          jsonb,
    readings     jsonb,
    kept         jsonb,
    note         text
);
CREATE INDEX IF NOT EXISTS site_visits_work_idx ON site_visits (work_id, captured_at);
CREATE INDEX IF NOT EXISTS site_visits_uploaded_idx ON site_visits (uploaded_at)
    WHERE status = 'uploaded';
-- like every table: no direct client access, only through the engine's API (001_core.sql)
ALTER TABLE site_visits ENABLE ROW LEVEL SECURITY;
