-- The implementing agency's cost estimate form, one per work (T099, the storage half of T094;
-- the fields: reference/cost_form.yaml, docs/specs/2026-10-03-cost-estimate-form.md).
-- A draft can be saved at any time; a form is "submitted" only when its checks pass (ready).
-- The batch and the API read a submitted form as work["cost_form"], so the Cost check and the
-- Duplicate check (map pins, declared continuations) run on it.
CREATE TABLE IF NOT EXISTS cost_forms (
    work_id      text PRIMARY KEY REFERENCES works (work_id) ON DELETE CASCADE,
    status       text NOT NULL CHECK (status IN ('draft', 'submitted')),
    form         jsonb NOT NULL,
    ready        boolean NOT NULL DEFAULT false,
    saved_by     text,
    saved_at     timestamptz NOT NULL DEFAULT now(),
    submitted_at timestamptz
);
CREATE INDEX IF NOT EXISTS cost_forms_submitted_idx ON cost_forms (work_id)
    WHERE status = 'submitted';
