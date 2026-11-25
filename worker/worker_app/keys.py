"""The worker's view of stored integration keys. Same table, same crypto."""
from __future__ import annotations

from key_crypto import decrypt

from . import db
from .config import settings


def _row(name: str):
    try:
        with db.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT value_encrypted FROM integration_keys WHERE name = %s",
                    (name,),
                )
                return cur.fetchone()
    except Exception:
        # A missing table (pre-migration) or a dropped connection reads as no
        # stored key; the environment fallback still works.
        return None


def resolve(name: str, env_attr: str, default: str = "") -> str:
    """Stored key first, environment second. Never raises."""
    row = _row(name)
    token = row[0] if row else None
    if token:
        value = decrypt(settings.session_secret, token)
        if value:
            return value
    return getattr(settings, env_attr, default) or ""
