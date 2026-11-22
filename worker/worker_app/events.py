"""The engine's activity log. Best-effort: logging must never break a job."""
from __future__ import annotations

from contextlib import closing

import psycopg

from .config import settings


def log(kind: str, detail: str = "") -> None:
    try:
        with closing(psycopg.connect(settings.direct_url)) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO engine_events (kind, detail) VALUES (%s, %s)",
                    (kind, detail[:500]),
                )
            conn.commit()
    except Exception:
        pass
