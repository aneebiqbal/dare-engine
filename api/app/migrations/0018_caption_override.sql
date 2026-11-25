-- Caption text/timing overrides, edited in the review screen. The transcript
-- stays cached; an edit never re-transcribes.
ALTER TABLE clips ADD COLUMN IF NOT EXISTS captions_override jsonb;
