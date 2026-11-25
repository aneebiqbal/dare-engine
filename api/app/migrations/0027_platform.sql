-- Platform targeting: one registry in shared/platforms.py, carried on the
-- project, the pipeline run and the finished clip. All three current targets
-- are 9:16 vertical, so aspect stays a preset value rather than a special case.
ALTER TABLE projects ADD COLUMN IF NOT EXISTS platform text NOT NULL DEFAULT 'youtube_shorts';
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS platform text NOT NULL DEFAULT 'youtube_shorts';
ALTER TABLE clips ADD COLUMN IF NOT EXISTS platform text NOT NULL DEFAULT 'youtube_shorts';

CREATE INDEX IF NOT EXISTS projects_platform_idx ON projects (platform);

-- Research provenance: sample-feed fallback and AI-provider fallback are
-- different facts. A run can read live YouTube and still have no AI credit.
ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS source_fallback boolean NOT NULL DEFAULT false;
ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS ai_fallback boolean NOT NULL DEFAULT false;
