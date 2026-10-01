-- Facts read from each work's attached papers and photos by the engines' own readers (T110
-- Paperwork, T310 Photo Evidence), one JSON per work: {"files": [{id, ext, sha256, pages,
-- kinds, readable, certificates: [...], certification_pages: [...]}, ...]}. Built by
-- data/build_evidence.py. Derived facts only: never file bytes, OCR text, vendor names, bank
-- accounts or phone numbers.
CREATE TABLE IF NOT EXISTS evidence_facts (
    work_id  text PRIMARY KEY REFERENCES works (work_id) ON DELETE CASCADE,
    data     jsonb NOT NULL,
    version  text NOT NULL
);
ALTER TABLE evidence_facts ENABLE ROW LEVEL SECURITY;
