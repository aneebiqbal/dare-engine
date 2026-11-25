-- The single-project lane as a self-expiring lease, not a session advisory
-- lock. A killed worker's session can outlive its process on a managed
-- database and hold an advisory lock forever; a lease whose heartbeat is stale
-- is taken over after LEASE_SECONDS, so recovery never needs manual cleanup.
CREATE TABLE IF NOT EXISTS pipeline_lane (
    id        integer PRIMARY KEY DEFAULT 1,
    owner     text,
    acquired_at timestamptz,
    heartbeat timestamptz
);
INSERT INTO pipeline_lane (id) VALUES (1) ON CONFLICT (id) DO NOTHING;
