"""Current user, from a real session cookie.

R1 adds a development sign-in that creates real users and real sessions.
M5 replaces only how the identity is verified (Google), not this model.
"""
from __future__ import annotations

from fastapi import HTTPException, Request

from . import db
from .config import settings


def current_user(request: Request) -> dict:
    token = request.cookies.get(settings.session_cookie)
    if not token:
        raise HTTPException(status_code=401, detail="not signed in")
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT u.id, u.google_subject, u.display_name, u.role "
                "FROM sessions s JOIN users u ON u.id = s.user_id "
                "WHERE s.token = %s AND s.expires_at > now()",
                (token,),
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="session expired")
    return {
        "id": str(row[0]),
        "google_subject": row[1],
        "display_name": row[2],
        "role": row[3],
    }
