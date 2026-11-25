-- Transcript-first moment selection: detected language, the region transcript,
-- per-candidate rubric output and the selection controls (a quality bar, not a
-- fixed count).
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS language text;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS transcript jsonb;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS regions jsonb;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS max_clips integer NOT NULL DEFAULT 40;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS min_seconds integer NOT NULL DEFAULT 14;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS quality_bar integer NOT NULL DEFAULT 60;

ALTER TABLE pipeline_candidates ADD COLUMN IF NOT EXISTS label text;
ALTER TABLE pipeline_candidates ADD COLUMN IF NOT EXISTS hook text;
ALTER TABLE pipeline_candidates ADD COLUMN IF NOT EXISTS reason text;
ALTER TABLE pipeline_candidates ADD COLUMN IF NOT EXISTS scores jsonb;
ALTER TABLE pipeline_candidates ADD COLUMN IF NOT EXISTS composite double precision;
ALTER TABLE pipeline_candidates ADD COLUMN IF NOT EXISTS timeline text;
ALTER TABLE pipeline_candidates ADD COLUMN IF NOT EXISTS keep boolean;
