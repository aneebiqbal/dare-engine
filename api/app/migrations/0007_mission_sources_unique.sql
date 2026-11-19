-- Re-researching the same game reuses deterministic mission ids, so the source
-- rows must be unique per (mission, url) or they duplicate on every run.
DELETE FROM mission_sources a
USING mission_sources b
WHERE a.id > b.id AND a.mission_id = b.mission_id AND a.url = b.url;

CREATE UNIQUE INDEX IF NOT EXISTS mission_sources_mission_url_idx
    ON mission_sources (mission_id, url);
