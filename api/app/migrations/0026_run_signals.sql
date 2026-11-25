-- Cheap-scan signals must survive a retry: they used to live in the run's
-- temp directory, which is destroyed when an attempt ends.
ALTER TABLE pipeline_runs ADD COLUMN IF NOT EXISTS signals jsonb;
