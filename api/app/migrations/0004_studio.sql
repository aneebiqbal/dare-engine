-- Sprint 7: the admin clip studio. A recording, its auto-detected candidate
-- windows, and the compute path that produced them.
CREATE TABLE IF NOT EXISTS studio_recordings (
    id                   uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id              uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename             text NOT NULL,
    storage_key          text NOT NULL,
    duration_seconds     double precision NOT NULL DEFAULT 0,
    width                integer NOT NULL DEFAULT 0,
    height               integer NOT NULL DEFAULT 0,
    whisper_device       text,
    whisper_compute_type text,
    encoder              text,
    created_at           timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS studio_candidates (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    recording_id  uuid NOT NULL REFERENCES studio_recordings(id) ON DELETE CASCADE,
    start_seconds double precision NOT NULL,
    end_seconds   double precision NOT NULL,
    score         double precision NOT NULL,
    reasons       jsonb NOT NULL DEFAULT '[]',
    state         text NOT NULL DEFAULT 'pending',
    template_id   text,
    clip_id       uuid,
    created_at    timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS studio_candidates_recording_idx ON studio_candidates (recording_id);
