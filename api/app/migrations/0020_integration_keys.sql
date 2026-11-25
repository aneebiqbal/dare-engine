-- Integration keys, encrypted at rest. `value_encrypted` is NULL when the key
-- comes from the environment, so a status can still be recorded for env keys.
CREATE TABLE IF NOT EXISTS integration_keys (
    name            text PRIMARY KEY,
    value_encrypted text,
    status          text NOT NULL DEFAULT 'untested',
    status_detail   text,
    tested_at       timestamptz,
    updated_at      timestamptz NOT NULL DEFAULT now()
);
