-- Summary columns so the dashboard and queue never scan agent JSON.
ALTER TABLE assessments ADD COLUMN IF NOT EXISTS alerts text[] NOT NULL DEFAULT '{}';
ALTER TABLE assessments ADD COLUMN IF NOT EXISTS headline text;
CREATE INDEX IF NOT EXISTS assessments_alerts_idx ON assessments USING gin (alerts);
