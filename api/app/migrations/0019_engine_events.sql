-- The engine's own activity log: model loads/unloads, job stages and cleanups.
-- Shown on the admin overview so the user can see what ran and that nothing is
-- left resident.
CREATE TABLE IF NOT EXISTS engine_events (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    kind       text NOT NULL,
    detail     text,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS engine_events_recent_idx ON engine_events (created_at DESC);
