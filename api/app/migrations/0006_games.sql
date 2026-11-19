-- Games and the daily research brain.
-- A game owns ideas (missions). Research pulls public sources per game and
-- writes sourced candidates; an admin approves them before a gamer sees them.

CREATE TABLE IF NOT EXISTS games (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    slug         text NOT NULL UNIQUE,
    name         text NOT NULL,
    external_id  text,
    source       text NOT NULL DEFAULT 'rawg',
    genre        text,
    release_date date,
    art_url      text,
    enabled      boolean NOT NULL DEFAULT true,
    created_at   timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE missions ADD COLUMN IF NOT EXISTS game_id uuid REFERENCES games(id) ON DELETE SET NULL;
CREATE INDEX IF NOT EXISTS missions_game_idx ON missions(game_id);

-- The real sources an idea came from. An idea with no rows here is never shown.
CREATE TABLE IF NOT EXISTS mission_sources (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    mission_id   text NOT NULL REFERENCES missions(id) ON DELETE CASCADE,
    kind         text NOT NULL,
    title        text NOT NULL,
    url          text NOT NULL,
    external_id  text,
    published_at timestamptz,
    created_at   timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS mission_sources_mission_idx ON mission_sources(mission_id);

CREATE TABLE IF NOT EXISTS research_runs (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    game_id      uuid NOT NULL REFERENCES games(id) ON DELETE CASCADE,
    status       text NOT NULL DEFAULT 'running',
    source_counts jsonb NOT NULL DEFAULT '{}',
    ideas_count  integer NOT NULL DEFAULT 0,
    fallback     boolean NOT NULL DEFAULT false,
    error        text,
    created_at   timestamptz NOT NULL DEFAULT now(),
    finished_at  timestamptz
);
CREATE INDEX IF NOT EXISTS research_runs_game_idx ON research_runs(game_id, created_at);
