"""Current user.

M2 runs before accounts exist, so this returns a seeded developer creator.
M5 replaces it with Google session auth and per-user isolation.
"""
from __future__ import annotations

from fastapi import HTTPException

from . import db

DEV_SUBJECT = "dev-user"


def current_user() -> dict:
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, google_subject, display_name, role "
                "FROM users WHERE google_subject = %s",
                (DEV_SUBJECT,),
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="not signed in")
    return {
        "id": str(row[0]),
        "google_subject": row[1],
        "display_name": row[2],
        "role": row[3],
    }
