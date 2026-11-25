-- Vision suggestions: a candidate can come from the cheap audio/scene detector
-- or from the sampled VLM pass, and the VLM keeps the frame it judged.
ALTER TABLE studio_candidates ADD COLUMN IF NOT EXISTS source text NOT NULL DEFAULT 'audio';
ALTER TABLE studio_candidates ADD COLUMN IF NOT EXISTS thumb_key text;
ALTER TABLE studio_recordings ADD COLUMN IF NOT EXISTS vision_model text;
ALTER TABLE studio_recordings ADD COLUMN IF NOT EXISTS vision_seconds double precision;
