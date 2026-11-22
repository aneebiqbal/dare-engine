-- Live research progress: which stage the run is in and a human-readable detail
-- line. Written by the run as it moves so the admin can watch it happen.
ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS stage text;
ALTER TABLE research_runs ADD COLUMN IF NOT EXISTS detail text;
