-- Risk score v2 (T050) has four bands: LOW / MEDIUM / HIGH / CRITICAL (fusion/fuse.py).
-- 001 allowed only three, so the first CRITICAL work failed to store (found loading the
-- full corpus into a local copy of the hosted schema, 30 Sept 2026).
ALTER TABLE assessments DROP CONSTRAINT IF EXISTS assessments_band_check;
ALTER TABLE assessments ADD CONSTRAINT assessments_band_check
    CHECK (band IN ('CRITICAL', 'HIGH', 'MEDIUM', 'LOW'));
