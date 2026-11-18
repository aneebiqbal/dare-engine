"""Email/password accounts: sign-up, sign-in, sessions, CSRF, reset, lockout.

Passwords are hashed with Argon2id (argon2-cffi). Sessions live in Postgres.
Cookies are HttpOnly, Secure in production and SameSite=Lax. State-changing
routes require a double-submit CSRF token.
"""
from __future__ import annotations

import datetime
import hashlib
import re
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from fastapi import APIRouter, HTTPException, Request, Response
from pydantic import BaseModel, Field

from . import db
from .config import settings
from .users import audit, current_user, hash_token

router = APIRouter()

ph = PasswordHasher()
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SESSION_DAYS = 30
MAX_FAILURES = 10
LOCK_MINUTES = 15
RATE_LIMIT = 20
IP_RATE_LIMIT = 50
RATE_WINDOW_MINUTES = 15


class SignUp(BaseModel):
    email: str
    password: str = Field(min_length=10)
    display_name: str = Field(min_length=1, max_length=80)
    invite_code: str | None = None


class SignIn(BaseModel):
    email: str
    password: str


class ChangePassword(BaseModel):
    current_password: str
    new_password: str = Field(min_length=10)


class ResetPassword(BaseModel):
    token: str
    new_password: str = Field(min_length=10)


class DevSignIn(BaseModel):
    display_name: str


def _hash(password: str) -> str:
    return ph.hash(password)


def _verify(user_hash: str | None, password: str) -> bool:
    if not user_hash:
        return False
    try:
        return ph.verify(user_hash, password)
    except VerifyMismatchError:
        return False


def _set_session(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.session_cookie,
        value=token,
        httponly=True,
        secure=settings.cookies_secure,
        samesite="lax",
        path="/",
        max_age=60 * 60 * 24 * SESSION_DAYS,
    )


def _set_csrf(response: Response, token: str) -> None:
    response.set_cookie(
        key=settings.csrf_cookie,
        value=token,
        httponly=False,
        secure=settings.cookies_secure,
        samesite="lax",
        path="/",
        max_age=60 * 60 * 24 * SESSION_DAYS,
    )


def _new_session(cur, user_id: str) -> str:
    token = secrets.token_urlsafe(32)
    cur.execute(
        "INSERT INTO sessions (token, user_id) VALUES (%s, %s)",
        (hash_token(token), user_id),
    )
    return token


def _guard_dev() -> None:
    if not settings.dev_auth_enabled:
        raise HTTPException(status_code=404, detail="not found")


@router.get("/auth/csrf")
def csrf(response: Response):
    token = secrets.token_urlsafe(32)
    _set_csrf(response, token)
    return {"csrf": token}


@router.post("/auth/sign-up")
def sign_up(payload: SignUp, response: Response):
    email = payload.email.strip().lower()
    if not EMAIL.match(email):
        raise HTTPException(422, "a valid email is required")
    if len(payload.password) < 10:
        raise HTTPException(422, "password must be at least 10 characters")

    invite = None
    if settings.invite_required or payload.invite_code:
        if not payload.invite_code:
            raise HTTPException(403, "an invite code is required")
        with db.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, email, used_by, revoked_at, expires_at FROM invites "
                    "WHERE code = %s",
                    (payload.invite_code.strip(),),
                )
                invite = cur.fetchone()
        if invite is None:
            raise HTTPException(403, "invite code is not valid")
        if invite[2] or invite[3] or invite[4] < datetime.datetime.now(datetime.timezone.utc):
            raise HTTPException(403, "invite code has been used or expired")
        if invite[1] and invite[1].lower() != email:
            raise HTTPException(403, "invite code is for a different email")

    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE lower(email) = %s", (email,))
            if cur.fetchone() is not None:
                raise HTTPException(409, "an account with that email already exists")
            cur.execute(
                "INSERT INTO users (email, display_name, password_hash, role) "
                "VALUES (%s, %s, %s, 'creator') RETURNING id",
                (email, payload.display_name.strip(), _hash(payload.password)),
            )
            user_id = cur.fetchone()[0]
            if invite is not None:
                cur.execute(
                    "UPDATE invites SET used_by = %s, used_at = now() WHERE id = %s",
                    (user_id, invite[0]),
                )
            token = _new_session(cur, user_id)
    _set_session(response, token)
    _set_csrf(response, secrets.token_urlsafe(32))
    return {"user": {"id": str(user_id), "email": email, "display_name": payload.display_name.strip(), "role": "creator"}}


@router.post("/auth/sign-in")
def sign_in(request: Request, payload: SignIn, response: Response):
    email = payload.email.strip().lower()
    ip = request.client.host if request.client else None
    now = datetime.datetime.now(datetime.timezone.utc)
    token: str | None = None
    error: tuple[int, str] | None = None
    with db.session() as conn:
        with conn.cursor() as cur:
            window = now - datetime.timedelta(minutes=RATE_WINDOW_MINUTES)
            cur.execute(
                "SELECT count(*) FROM login_attempts WHERE email = %s AND created_at > %s",
                (email, window),
            )
            email_attempts = cur.fetchone()[0]
            cur.execute(
                "SELECT count(*) FROM login_attempts "
                "WHERE ip = %s AND ok = false AND created_at > %s",
                (ip, window),
            )
            ip_attempts = cur.fetchone()[0]
            if email_attempts >= RATE_LIMIT or ip_attempts >= IP_RATE_LIMIT:
                error = (429, "too many attempts; try again later")

            if error is None:
                cur.execute(
                    "SELECT id, password_hash, failed_logins, locked_until FROM users "
                    "WHERE lower(email) = %s",
                    (email,),
                )
                row = cur.fetchone()
                if row is None:
                    cur.execute(
                        "INSERT INTO login_attempts (email, ip, ok) VALUES (%s, %s, false)",
                        (email, ip),
                    )
                    error = (401, "invalid email or password")
                else:
                    user_id, user_hash, failures, locked_until = row
                    if locked_until and locked_until > now:
                        cur.execute(
                            "INSERT INTO login_attempts (email, ip, ok) VALUES (%s, %s, false)",
                            (email, ip),
                        )
                        error = (423, "account locked; try again later")
                    elif not _verify(user_hash, payload.password):
                        failures = (failures or 0) + 1
                        lock = None
                        if failures >= MAX_FAILURES:
                            lock = now + datetime.timedelta(minutes=LOCK_MINUTES)
                        cur.execute(
                            "UPDATE users SET failed_logins = %s, locked_until = %s WHERE id = %s",
                            (failures, lock, user_id),
                        )
                        cur.execute(
                            "INSERT INTO login_attempts (email, ip, ok) VALUES (%s, %s, false)",
                            (email, ip),
                        )
                        error = (401, "invalid email or password")
                    else:
                        cur.execute(
                            "UPDATE users SET failed_logins = 0, locked_until = NULL, "
                            "last_login_at = now() WHERE id = %s",
                            (user_id,),
                        )
                        cur.execute(
                            "INSERT INTO login_attempts (email, ip, ok) VALUES (%s, %s, true)",
                            (email, ip),
                        )
                        token = _new_session(cur, user_id)
    if error is not None:
        raise HTTPException(error[0], error[1])
    _set_session(response, token)
    _set_csrf(response, secrets.token_urlsafe(32))
    return {"ok": True}


@router.post("/auth/sign-out")
def sign_out(request: Request, response: Response):
    token = request.cookies.get(settings.session_cookie)
    if token:
        with db.session() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM sessions WHERE token = %s", (hash_token(token),))
    response.delete_cookie(settings.session_cookie, path="/")
    return {"ok": True}


@router.post("/auth/sign-out-all")
def sign_out_all(request: Request, response: Response):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM sessions WHERE user_id = %s", (user["id"],))
    audit(user["id"], "sign_out_all", "user", user["id"])
    response.delete_cookie(settings.session_cookie, path="/")
    return {"ok": True}


@router.post("/auth/change-password")
def change_password(request: Request, payload: ChangePassword, response: Response):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT password_hash FROM users WHERE id = %s", (user["id"],))
            row = cur.fetchone()
            if not _verify(row[0] if row else None, payload.current_password):
                raise HTTPException(401, "current password is incorrect")
            cur.execute(
                "UPDATE users SET password_hash = %s WHERE id = %s",
                (_hash(payload.new_password), user["id"]),
            )
            # Every other device must sign in again with the new password.
            cur.execute(
                "DELETE FROM sessions WHERE user_id = %s", (user["id"],)
            )
            token = _new_session(cur, user["id"])
    audit(user["id"], "change_password", "user", user["id"])
    _set_session(response, token)
    return {"ok": True}


@router.post("/auth/reset-password")
def reset_password(payload: ResetPassword, response: Response):
    token_hash = hashlib.sha256(payload.token.encode()).hexdigest()
    if len(payload.new_password) < 10:
        raise HTTPException(422, "password must be at least 10 characters")
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT token_hash, user_id, used_at, expires_at FROM password_resets "
                "WHERE token_hash = %s",
                (token_hash,),
            )
            row = cur.fetchone()
            now = datetime.datetime.now(datetime.timezone.utc)
            if row is None or row[2] or row[3] < now:
                raise HTTPException(400, "reset link is not valid or has expired")
            cur.execute(
                "UPDATE users SET password_hash = %s, failed_logins = 0, "
                "locked_until = NULL WHERE id = %s",
                (_hash(payload.new_password), row[1]),
            )
            cur.execute(
                "UPDATE password_resets SET used_at = now() WHERE token_hash = %s",
                (row[0],),
            )
            cur.execute("DELETE FROM sessions WHERE user_id = %s", (row[1],))
    response.delete_cookie(settings.session_cookie, path="/")
    return {"ok": True}


@router.post("/auth/dev/sign-in")
def dev_sign_in(payload: DevSignIn, response: Response):
    """Test-only identity provider. Off unless DEV_AUTH_ENABLED=true."""
    _guard_dev()
    name = payload.display_name.strip()
    if not name:
        raise HTTPException(422, "display name required")
    subject = f"dev:{name.lower().replace(' ', '-')}"
    role = "admin" if name.strip().lower() == "admin" else "creator"
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (google_subject, display_name, role) "
                "VALUES (%s, %s, %s) "
                "ON CONFLICT (google_subject) DO UPDATE SET "
                "display_name = EXCLUDED.display_name, role = EXCLUDED.role "
                "RETURNING id",
                (subject, name, role),
            )
            user_id = cur.fetchone()[0]
            token = _new_session(cur, str(user_id))
    _set_session(response, token)
    _set_csrf(response, secrets.token_urlsafe(32))
    return {"user": {"id": str(user_id), "display_name": name, "role": "creator"}, "token": token}


@router.post("/auth/dev/sign-out")
def dev_sign_out(response: Response):
    response.delete_cookie(settings.session_cookie, path="/")
    return {"ok": True}
