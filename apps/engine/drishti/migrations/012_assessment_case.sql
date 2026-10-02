-- One problem, one case (2 Oct 2026). A purchase filed as 11 works, or one road split into 4
-- pieces, is one question for an officer, not 11 queue items: on the eSAKSHI dashboard tables
-- 11 of 40 random queue works were one Rs 1.53 crore street-light purchase. The batch stores
-- the Duplicate & Split group a work belongs to; the review queue shows one row per case.
ALTER TABLE assessments ADD COLUMN IF NOT EXISTS case_id text;
ALTER TABLE assessments ADD COLUMN IF NOT EXISTS case_size integer;
CREATE INDEX IF NOT EXISTS assessments_case_idx ON assessments (case_id);
