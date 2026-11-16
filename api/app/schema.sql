-- Clipdesk Missions data model. Thirteen domain tables plus the job queue.

CREATE TABLE IF NOT EXISTS users (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    google_subject text UNIQUE NOT NULL,
    email         text,
    display_name  text,
    role          text NOT NULL DEFAULT 'creator',
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS channels (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id            uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    youtube_channel_id text NOT NULL UNIQUE,
    title              text,
    created_at         timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS oauth_tokens (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    channel_id uuid NOT NULL REFERENCES channels(id) ON DELETE CASCADE,
    ciphertext bytea NOT NULL,
    scopes     text[] NOT NULL DEFAULT '{}',
    updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS missions (
    id         text PRIMARY KEY,
    card       jsonb NOT NULL,
    score      double precision NOT NULL DEFAULT 0,
    status     text NOT NULL DEFAULT 'unverified',
    type       text,
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS daily_sets (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    date             date NOT NULL UNIQUE,
    daily_mission_id text REFERENCES missions(id),
    pool             jsonb NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS assignments (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    mission_id text NOT NULL REFERENCES missions(id),
    date       date NOT NULL,
    state      text NOT NULL DEFAULT 'accepted',
    created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS streams (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id        uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    stream_key_hash text NOT NULL,
    started_at     timestamptz NOT NULL DEFAULT now(),
    ended_at       timestamptz,
    storage_prefix text
);

CREATE TABLE IF NOT EXISTS marks (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id uuid REFERENCES assignments(id) ON DELETE SET NULL,
    stream_id     uuid NOT NULL REFERENCES streams(id) ON DELETE CASCADE,
    kind          text NOT NULL,
    stream_time   double precision NOT NULL,
    result        text,
    created_at    timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS clips (
    id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    assignment_id    uuid REFERENCES assignments(id) ON DELETE SET NULL,
    file_key         text,
    title            text,
    state            text NOT NULL DEFAULT 'rendering',
    template         text,
    duration_seconds double precision,
    created_at       timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS posts (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    clip_id    uuid NOT NULL REFERENCES clips(id) ON DELETE CASCADE,
    platform   text NOT NULL DEFAULT 'youtube',
    remote_id  text,
    posted_at  timestamptz,
    state      text NOT NULL DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS metrics (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    post_id             uuid NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
    views               integer NOT NULL DEFAULT 0,
    avg_view_percentage double precision,
    watch_time_seconds  double precision,
    collected_at        timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS attempts (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id   text NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    user_id      uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    result_value double precision,
    clip_id      uuid REFERENCES clips(id) ON DELETE SET NULL,
    created_at   timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS templates (
    id     text PRIMARY KEY,
    config jsonb NOT NULL,
    weight integer NOT NULL DEFAULT 1
);

-- Job queue. Row locking replaces Redis/Celery.
CREATE TABLE IF NOT EXISTS jobs (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    kind         text NOT NULL,
    payload      jsonb NOT NULL DEFAULT '{}',
    state        text NOT NULL DEFAULT 'queued',
    attempts     integer NOT NULL DEFAULT 0,
    available_at timestamptz NOT NULL DEFAULT now(),
    locked_by    text,
    created_at   timestamptz NOT NULL DEFAULT now(),
    updated_at   timestamptz NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS jobs_claim_idx ON jobs (state, available_at);
CREATE INDEX IF NOT EXISTS assignments_user_date_idx ON assignments (user_id, date);
CREATE INDEX IF NOT EXISTS marks_stream_idx ON marks (stream_id, stream_time);
CREATE INDEX IF NOT EXISTS clips_assignment_idx ON clips (assignment_id);
