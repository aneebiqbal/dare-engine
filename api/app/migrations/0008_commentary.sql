-- Originality / added-value step: the creator's own commentary or context.
-- The 2026 platform policy requires added value for monetisation; a clip with
-- no commentary is flagged in review.
ALTER TABLE clips ADD COLUMN IF NOT EXISTS commentary text;
