-- Leading indicators for the results screen and the research ranking:
-- viewed vs swiped, saves and shares.
ALTER TABLE metrics ADD COLUMN IF NOT EXISTS swiped integer NOT NULL DEFAULT 0;
ALTER TABLE metrics ADD COLUMN IF NOT EXISTS saves  integer NOT NULL DEFAULT 0;
ALTER TABLE metrics ADD COLUMN IF NOT EXISTS shares integer NOT NULL DEFAULT 0;
