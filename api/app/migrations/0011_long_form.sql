-- Long-form builder: one video assembled from a session's clips.
CREATE TABLE IF NOT EXISTS long_forms (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    title      text NOT NULL,
    state      text NOT NULL DEFAULT 'queued',  -- queued | building | ready | failed
    file_key   text,
    clip_ids   jsonb NOT NULL,
    error      text,
    created_at timestamptz NOT NULL DEFAULT now()
);
