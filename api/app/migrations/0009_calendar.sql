-- Posting calendar: a review-and-export queue. One entry per clip per platform.
CREATE TABLE IF NOT EXISTS calendar_entries (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    clip_id       uuid NOT NULL REFERENCES clips(id) ON DELETE CASCADE,
    scheduled_for date NOT NULL,
    platform      text NOT NULL DEFAULT 'youtube',
    state         text NOT NULL DEFAULT 'draft',  -- draft | published
    published_at  timestamptz,
    created_at    timestamptz NOT NULL DEFAULT now(),
    UNIQUE (clip_id, platform)
);
