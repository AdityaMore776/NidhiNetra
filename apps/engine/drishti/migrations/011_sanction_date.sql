-- The eSAKSHI dashboard tables carry each work's SANCTION DATE (the research export did not).
-- Guideline Compliance R14 (a construction recorded complete within a week of its sanction) and
-- Office Patterns read it. Empty for works loaded from the research export: R14 then says it
-- could not check, never that it passed.
ALTER TABLE works ADD COLUMN IF NOT EXISTS sanction_date date;
