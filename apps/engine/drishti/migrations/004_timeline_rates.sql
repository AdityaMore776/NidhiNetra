-- How common "completed before recommended" was, per recommendation quarter and
-- per implementing office. Built by data/build_stats.py; read by validation/timeline.py.
CREATE TABLE IF NOT EXISTS timeline_quarters (
    quarter  text PRIMARY KEY,
    n        integer NOT NULL,
    bad      integer NOT NULL
);
CREATE TABLE IF NOT EXISTS timeline_agencies (
    agency_name  text PRIMARY KEY,
    completed    integer NOT NULL,
    bad          integer NOT NULL
);
ALTER TABLE timeline_quarters ENABLE ROW LEVEL SECURITY;
ALTER TABLE timeline_agencies ENABLE ROW LEVEL SECURITY;
