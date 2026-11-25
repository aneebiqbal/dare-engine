-- A project is one stream/recording moving through the clip pipeline.
-- The stage is derived from real artifacts on read (see api/app/projects.py),
-- so it can never drift from the clips, jobs and exports that produced it.
CREATE TABLE IF NOT EXISTS projects (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    name         text NOT NULL,
    game_id      uuid REFERENCES games(id) ON DELETE SET NULL,
    recording_id uuid REFERENCES studio_recordings(id) ON DELETE SET NULL,
    stream_id    uuid REFERENCES streams(id) ON DELETE SET NULL,
    vision       boolean NOT NULL DEFAULT false,
    stage_note   text,
    queued_at    timestamptz,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS projects_user_idx ON projects (user_id, created_at DESC);
-- The queue is FIFO by queued_at; the partial index keeps the head lookup cheap.
CREATE INDEX IF NOT EXISTS projects_queue_idx ON projects (queued_at) WHERE queued_at IS NOT NULL;
