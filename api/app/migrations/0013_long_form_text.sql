-- Long-form intro/outro title cards.
ALTER TABLE long_forms ADD COLUMN IF NOT EXISTS intro text;
ALTER TABLE long_forms ADD COLUMN IF NOT EXISTS outro text;
