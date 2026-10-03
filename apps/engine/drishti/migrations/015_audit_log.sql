-- T060's audit trail: one append-only row per thing an officer did.
--
-- The chain exists so that a row cannot be quietly edited or removed later. Each
-- row carries the hash of the row before it, so changing any earlier row breaks
-- every hash after it and verify_chain() says so. That is the whole point: the
-- value of a trail is that you cannot rewrite it unnoticed.
--
-- Wording note: an entry records what was done to a *work record*, never a
-- judgement about anyone, and never an MP's name.

CREATE TABLE IF NOT EXISTS audit_log (
    entry_id  bigserial PRIMARY KEY,
    at        timestamptz NOT NULL DEFAULT now(),
    actor     text NOT NULL,
    role      text NOT NULL,
    action    text NOT NULL,
    entity    text NOT NULL,
    entity_id text NOT NULL,
    work_id   text,
    before    jsonb,
    after     jsonb,
    note      text,
    prev_hash text NOT NULL,
    hash      text NOT NULL
);

-- The chain is read in order and nothing updates a row, so these are the two
-- queries that matter: verify_chain() walks entry_id, and an officer's history
-- for one work reads work_id.
CREATE INDEX IF NOT EXISTS audit_log_work_idx ON audit_log (work_id, entry_id);
CREATE UNIQUE INDEX IF NOT EXISTS audit_log_hash_idx ON audit_log (hash);

-- One writer at a time. Without this, two officers acting at the same instant
-- would read the same prev_hash and the chain would fork.
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;