-- The automatic upload-to-Shorts pipeline. A run is the unit of work; its
-- stage is the last COMPLETED stage, so a killed run resumes from the next one.
-- Candidates keep their cheap and vision scores separately so the ranking is
-- auditable, and each candidate carries its own status so a partial stage
-- resumes per item rather than from scratch.
CREATE TABLE IF NOT EXISTS pipeline_runs (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    project_id     uuid NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    user_id        uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    recording_id   uuid REFERENCES studio_recordings(id) ON DELETE SET NULL,
    state          text NOT NULL DEFAULT 'queued',  -- queued|running|paused|done|failed
    stage          text NOT NULL DEFAULT 'ingest',
    progress       int  NOT NULL DEFAULT 0,
    action         text NOT NULL DEFAULT 'Waiting in the queue.',
    eta_seconds    int,
    remaining_seconds int,
    model_loaded   text NOT NULL DEFAULT '',
    top_n          int  NOT NULL DEFAULT 10,
    no_speech      boolean NOT NULL DEFAULT false,
    timestamps     jsonb NOT NULL DEFAULT '[]',
    stage_timings  jsonb NOT NULL DEFAULT '{}',
    rates          jsonb NOT NULL DEFAULT '{}',
    compute_path   text NOT NULL DEFAULT '',
    error          text,
    source_key     text,
    notes          jsonb NOT NULL DEFAULT '[]',
    memory         jsonb NOT NULL DEFAULT '{}',
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now(),
    started_at     timestamptz,
    finished_at    timestamptz
);

CREATE INDEX IF NOT EXISTS pipeline_runs_user_idx ON pipeline_runs (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS pipeline_runs_queue_idx ON pipeline_runs (created_at)
    WHERE state = 'queued';

CREATE TABLE IF NOT EXISTS pipeline_candidates (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    run_id        uuid NOT NULL REFERENCES pipeline_runs(id) ON DELETE CASCADE,
    start_seconds double precision NOT NULL,
    end_seconds   double precision NOT NULL,
    cheap_score   double precision NOT NULL DEFAULT 0,
    vision_score  double precision,
    final_score   double precision NOT NULL DEFAULT 0,
    reasons       jsonb NOT NULL DEFAULT '[]',
    vision_reason text,
    origin        text NOT NULL DEFAULT 'ai',        -- ai|user
    selected      boolean NOT NULL DEFAULT false,
    thumb_key     text,
    status        text NOT NULL DEFAULT 'candidate', -- candidate|cut|transcribed|rendered|failed
    cut_key       text,
    transcript    jsonb,
    clip_id       uuid REFERENCES clips(id) ON DELETE SET NULL,
    error         text,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS pipeline_candidates_run_idx
    ON pipeline_candidates (run_id, final_score DESC);
