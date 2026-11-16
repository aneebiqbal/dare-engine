"""Development sign-in.

Enabled only by DEV_AUTH_ENABLED. The app refuses to start when it is enabled in
production, so this path can never reach a real deployment. Google sign-in (M5)
replaces the identity provider, not the session model.
"""
from __future__ import annotations

import secrets

from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel

from . import db
from .config import settings

router = APIRouter()


class DevSignIn(BaseModel):
    display_name: str


def _guard() -> None:
    if not settings.dev_auth_enabled:
        raise HTTPException(status_code=404, detail="not found")


@router.post("/auth/dev/sign-in")
def dev_sign_in(payload: DevSignIn, response: Response):
    _guard()
    name = payload.display_name.strip()
    if not name:
        raise HTTPException(422, "display name required")
    subject = f"dev:{name.lower().replace(' ', '-')}"
    token = secrets.token_urlsafe(32)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (google_subject, display_name, role) "
                "VALUES (%s, %s, 'creator') "
                "ON CONFLICT (google_subject) DO UPDATE SET display_name = EXCLUDED.display_name "
                "RETURNING id",
                (subject, name),
            )
            user_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO sessions (token, user_id) VALUES (%s, %s)",
                (token, user_id),
            )
    response.set_cookie(
        key=settings.session_cookie,
        value=token,
        httponly=True,
        samesite="lax",
        path="/",
        max_age=60 * 60 * 24 * 30,
    )
    return {"user": {"id": str(user_id), "display_name": name, "role": "creator"}, "token": token}


@router.post("/auth/dev/sign-out")
def dev_sign_out(response: Response):
    response.delete_cookie(settings.session_cookie, path="/")
    return {"ok": True}
