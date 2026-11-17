-- Sprint 6: email/password accounts, roles, invites, lockout, reset, audit,
-- tours, AI usage, exports, voice-over and job backoff.

-- --- users ---------------------------------------------------------------
ALTER TABLE users ALTER COLUMN google_subject DROP NOT NULL;
ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash text;
ALTER TABLE users ADD COLUMN IF NOT EXISTS failed_logins integer NOT NULL DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS locked_until timestamptz;
ALTER TABLE users ADD COLUMN IF NOT EXISTS last_login_at timestamptz;
ALTER TABLE users ADD COLUMN IF NOT EXISTS created_by_invite uuid;
CREATE UNIQUE INDEX IF NOT EXISTS users_email_lower_idx ON users (lower(email));

-- --- invites -------------------------------------------------------------
CREATE TABLE IF NOT EXISTS invites (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    code       text NOT NULL UNIQUE,
    email      text,
    created_by uuid REFERENCES users(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL DEFAULT now() + interval '7 days',
    used_by    uuid REFERENCES users(id) ON DELETE SET NULL,
    used_at    timestamptz,
    revoked_at timestamptz
);
CREATE INDEX IF NOT EXISTS invites_code_idx ON invites (code);

-- --- password resets (admin-issued one-time links; no email service) ------
CREATE TABLE IF NOT EXISTS password_resets (
    token_hash text PRIMARY KEY,
    user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    created_by uuid REFERENCES users(id) ON DELETE SET NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    expires_at timestamptz NOT NULL DEFAULT now() + interval '1 hour',
    used_at    timestamptz
);

-- --- login rate limiting / lockout ---------------------------------------
CREATE TABLE IF NOT EXISTS login_attempts (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email      text NOT NULL,
    ip         text,
    ok         boolean NOT NULL DEFAULT false,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS login_attempts_email_idx ON login_attempts (email, created_at);

-- --- audit log of admin actions ------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    actor_id    uuid REFERENCES users(id) ON DELETE SET NULL,
    action      text NOT NULL,
    target_type text,
    target_id   text,
    meta        jsonb NOT NULL DEFAULT '{}',
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS audit_log_created_idx ON audit_log (created_at DESC);

-- --- tour progress per user ----------------------------------------------
CREATE TABLE IF NOT EXISTS tour_progress (
    user_id    uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    tour_id    text NOT NULL,
    step_index integer NOT NULL DEFAULT 0,
    completed  boolean NOT NULL DEFAULT false,
    skipped    boolean NOT NULL DEFAULT false,
    updated_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (user_id, tour_id)
);

-- --- AI usage: tokens and latency per call -------------------------------
CREATE TABLE IF NOT EXISTS ai_usage (
    id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id           uuid REFERENCES users(id) ON DELETE SET NULL,
    page              text NOT NULL,
    kind              text NOT NULL,
    provider          text NOT NULL,
    model             text NOT NULL,
    prompt_tokens     integer NOT NULL DEFAULT 0,
    completion_tokens integer NOT NULL DEFAULT 0,
    latency_ms        integer NOT NULL DEFAULT 0,
    fallback          boolean NOT NULL DEFAULT false,
    created_at        timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ai_usage_created_idx ON ai_usage (created_at DESC);

-- --- per-user preferences ------------------------------------------------
CREATE TABLE IF NOT EXISTS user_settings (
    user_id            uuid PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    caption_style      text NOT NULL DEFAULT 'word',
    layout_preference  text NOT NULL DEFAULT 'rotate',
    voice_over_default boolean NOT NULL DEFAULT false,
    voice              text,
    updated_at         timestamptz NOT NULL DEFAULT now()
);

-- --- clip extras: stages, trim, transcript cache, voice-over -------------
ALTER TABLE clips ADD COLUMN IF NOT EXISTS stage text;
ALTER TABLE clips ADD COLUMN IF NOT EXISTS progress integer NOT NULL DEFAULT 0;
ALTER TABLE clips ADD COLUMN IF NOT EXISTS error text;
ALTER TABLE clips ADD COLUMN IF NOT EXISTS transcript jsonb;
ALTER TABLE clips ADD COLUMN IF NOT EXISTS source_start double precision;
ALTER TABLE clips ADD COLUMN IF NOT EXISTS source_end double precision;
ALTER TABLE clips ADD COLUMN IF NOT EXISTS recording_key text;
ALTER TABLE clips ADD COLUMN IF NOT EXISTS trim_start double precision;
ALTER TABLE clips ADD COLUMN IF NOT EXISTS trim_end double precision;
ALTER TABLE clips ADD COLUMN IF NOT EXISTS layout text;
ALTER TABLE clips ADD COLUMN IF NOT EXISTS caption_style text DEFAULT 'word';
ALTER TABLE clips ADD COLUMN IF NOT EXISTS voice_over boolean NOT NULL DEFAULT false;
ALTER TABLE clips ADD COLUMN IF NOT EXISTS voice text;
ALTER TABLE clips ADD COLUMN IF NOT EXISTS voice_key text;
ALTER TABLE clips ADD COLUMN IF NOT EXISTS export_title text;
ALTER TABLE clips ADD COLUMN IF NOT EXISTS export_description text;
ALTER TABLE clips ADD COLUMN IF NOT EXISTS export_tags jsonb;

-- --- voice-over rows -----------------------------------------------------
CREATE TABLE IF NOT EXISTS voice_overs (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    clip_id    uuid NOT NULL REFERENCES clips(id) ON DELETE CASCADE,
    voice      text NOT NULL,
    text       text NOT NULL,
    audio_key  text,
    duration   double precision,
    state      text NOT NULL DEFAULT 'ready',
    created_at timestamptz NOT NULL DEFAULT now()
);

-- --- export packages -----------------------------------------------------
CREATE TABLE IF NOT EXISTS exports (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    clip_id     uuid NOT NULL REFERENCES clips(id) ON DELETE CASCADE,
    title       text,
    description text,
    tags        jsonb NOT NULL DEFAULT '[]',
    video_key   text,
    thumb_key   text,
    state       text NOT NULL DEFAULT 'ready',
    created_at  timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS exports_clip_idx ON exports (clip_id, created_at DESC);

-- --- job backoff, errors, idempotency ------------------------------------
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS error text;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS retry_count integer NOT NULL DEFAULT 0;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS idempotency_key text UNIQUE;
