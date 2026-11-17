-- Render idempotency: a retried job must not render the same clip twice.
ALTER TABLE clips ADD COLUMN IF NOT EXISTS render_key text;
