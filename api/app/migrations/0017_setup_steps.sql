-- First-run wizard progress, so a returning user skips completed steps.
CREATE TABLE IF NOT EXISTS setup_steps (
    user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    step       text NOT NULL,
    status     text NOT NULL DEFAULT 'pending',  -- pending | done | failed
    detail     text,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, step)
);
