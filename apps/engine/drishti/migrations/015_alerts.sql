-- Alerts, their lifecycle and the audit log (T060).
--
-- Every review-queue case (one per case, migration 012) is an alert. A case with no row here is
-- simply New: the row is written on its first move, so a batch never has to create alerts and a
-- reload of the works (load_db truncates them) never loses a case's history. No foreign key to
-- works for the same reason; work_id and district_lgd are copied from the queue at the first move.
--
-- New -> Triaged -> In plan -> Inspected -> Issue confirmed / Cleared -> Closed
-- (drishti/alerts.py holds the moves and who may make each.)
CREATE TABLE IF NOT EXISTS alerts (
    alert_id      text PRIMARY KEY,                 -- the queue's case key: case_id, else work_id
    work_id       text NOT NULL,                    -- the case's lead work at the first move
    district_lgd  text,
    state         text NOT NULL DEFAULT 'NEW'
                  CHECK (state IN ('NEW', 'TRIAGED', 'IN_PLAN', 'INSPECTED', 'ISSUE_CONFIRMED',
                                   'CLEARED', 'CLOSED')),
    opened_at     timestamptz NOT NULL DEFAULT now(),
    updated_at    timestamptz NOT NULL DEFAULT now(),
    updated_by    text,
    note          text                              -- the latest move's note
);
CREATE INDEX IF NOT EXISTS alerts_district_idx ON alerts (district_lgd, state);

-- One row per change, never edited: each row carries the hash of the row before it, so changing
-- or removing any past row breaks every hash after it (drishti/alerts.py verify_chain).
CREATE TABLE IF NOT EXISTS audit_log (
    seq         bigint PRIMARY KEY,
    at          timestamptz NOT NULL,
    alert_id    text NOT NULL,
    actor_id    text NOT NULL,
    actor_role  text NOT NULL,
    actor_name  text,
    action      text NOT NULL CHECK (action IN ('open', 'move')),
    from_state  text,
    to_state    text NOT NULL,
    note        text,
    prev_hash   text NOT NULL,
    hash        text NOT NULL UNIQUE
);
CREATE INDEX IF NOT EXISTS audit_log_alert_idx ON audit_log (alert_id, seq);

-- append-only: the database itself refuses to change or delete a past row
CREATE OR REPLACE FUNCTION audit_log_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only';
END
$$;
DROP TRIGGER IF EXISTS audit_log_no_change ON audit_log;
CREATE TRIGGER audit_log_no_change BEFORE UPDATE OR DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION audit_log_append_only();
DROP TRIGGER IF EXISTS audit_log_no_truncate ON audit_log;
CREATE TRIGGER audit_log_no_truncate BEFORE TRUNCATE ON audit_log
    FOR EACH STATEMENT EXECUTE FUNCTION audit_log_append_only();

-- like every table: no direct client access, only through the engine's API (001_core.sql)
ALTER TABLE alerts ENABLE ROW LEVEL SECURITY;
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
