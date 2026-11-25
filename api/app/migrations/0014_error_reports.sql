-- Client error reporting: the browser posts a message + stack, an admin reads
-- the recent ones. Never a secret, never a session token.
CREATE TABLE IF NOT EXISTS error_reports (
    id         uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id    uuid REFERENCES users(id) ON DELETE SET NULL,
    message    text NOT NULL,
    stack      text,
    path       text,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS error_reports_created_idx ON error_reports (created_at DESC);
