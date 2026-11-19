"""A tiny global key/value store, used by the provider picker."""
from __future__ import annotations

from . import db


def get(key: str, default: str | None = None) -> str | None:
    try:
        with db.session() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT value FROM global_settings WHERE key = %s", (key,))
                row = cur.fetchone()
        return row[0] if row else default
    except Exception:
        return default


def set(key: str, value: str) -> None:
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO global_settings (key, value) VALUES (%s, %s) "
                "ON CONFLICT (key) DO UPDATE SET value = EXCLUDED.value",
                (key, value),
            )
