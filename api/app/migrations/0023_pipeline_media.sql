-- Media facts the ingest stage measures once and the ETA model reuses.
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS duration_seconds double precision;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS width integer;
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS height integer;
