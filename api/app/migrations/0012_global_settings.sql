-- Global key/value settings, used by the provider picker. The environment is
-- still the source of truth; a stored value overrides it at runtime.
CREATE TABLE IF NOT EXISTS global_settings (
    key   text PRIMARY KEY,
    value text NOT NULL
);
