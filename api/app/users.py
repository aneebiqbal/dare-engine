"""Current user from a real session cookie, role checks, CSRF and audit."""
from __future__ import annotations

import hashlib
import hmac

from fastapi import HTTPException, Request

from . import db
from .config import settings


def hash_token(token: str) -> str:
    """Sessions store only an HMAC of the token, keyed by SESSION_SECRET.

    A database dump therefore does not contain usable session tokens.
    """
    return hmac.new(
        settings.session_secret.encode(), token.encode(), hashlib.sha256
    ).hexdigest()


def current_user(request: Request) -> dict:
    token = request.cookies.get(settings.session_cookie)
    if not token:
        raise HTTPException(status_code=401, detail="not signed in")
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT u.id, u.email, u.display_name, u.role "
                "FROM sessions s JOIN users u ON u.id = s.user_id "
                "WHERE s.token = %s AND s.expires_at > now()",
                (hash_token(token),),
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="session expired")
    return {
        "id": str(row[0]),
        "email": row[1],
        "display_name": row[2],
        "role": row[3],
    }


def require_admin(request: Request) -> dict:
    user = current_user(request)
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="admin role required")
    return user


def csrf_protect(request: Request) -> None:
    """Double-submit cookie CSRF check on every state-changing route.

    The client reads the non-HttpOnly `clipdesk_csrf` cookie and sends it back
    in `X-CSRF-Token`. Relay hooks are exempt: they authenticate with a shared
    secret instead.
    """
    if request.method in ("GET", "HEAD", "OPTIONS"):
        return
    if request.url.path.startswith("/hooks/"):
        return
    sent = request.headers.get("x-csrf-token")
    cookie = request.cookies.get(settings.csrf_cookie)
    if not sent or not cookie or not hmac.compare_digest(sent, cookie):
        raise HTTPException(status_code=403, detail="csrf token missing or invalid")


def audit(actor_id: str | None, action: str, target_type: str = "", target_id: str = "", meta: dict | None = None) -> None:
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO audit_log (actor_id, action, target_type, target_id, meta) "
                "VALUES (%s, %s, %s, %s, %s)",
                (actor_id, action, target_type, target_id, __import__("json").dumps(meta or {})),
            )
