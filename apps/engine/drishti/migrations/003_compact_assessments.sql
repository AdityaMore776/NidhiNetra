-- A LOW work with nothing to show keeps only its summary; the full agent
-- detail is rebuilt when someone opens it. Measured 2026-09-25: storing full
-- detail for all 209,993 real works took the database to 489 MB of the free
-- tier's 500.
ALTER TABLE assessments ADD COLUMN IF NOT EXISTS compact boolean NOT NULL DEFAULT false;
