"""Admin: users, invites, pool, templates, jobs, AI usage, audit, setup."""
from __future__ import annotations

import datetime
import hashlib
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request

from . import db, storage
from .config import settings
from .paging import envelope, order_clause, parse
from .users import audit, current_user, require_admin

router = APIRouter(dependencies=[Depends(require_admin)])

USER_SORT = {"created_at": "created_at", "email": "email", "display_name": "display_name", "role": "role"}
JOB_SORT = {"updated_at": "updated_at", "created_at": "created_at", "state": "state", "kind": "kind"}
INVITE_SORT = {"created_at": "created_at", "code": "code"}
AUDIT_SORT = {"created_at": "created_at", "action": "action"}


@router.get("/admin/templates")
def templates(request: Request):
    page, size, sort, order = parse(request, "id")
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM templates")
            total = cur.fetchone()[0]
            cur.execute(
                f"SELECT id, config, weight FROM templates ORDER BY {order_clause(sort, {'id': 'id', 'weight': 'weight'}, 'id', order)} LIMIT %s OFFSET %s",
                (size, (page - 1) * size),
            )
            rows = cur.fetchall()
    return envelope([{"id": r[0], "config": r[1], "weight": r[2]} for r in rows], total, page, size)


@router.get("/admin/users")
def users(request: Request):
    page, size, sort, order = parse(request, "created_at")
    role = request.query_params.get("role")
    with db.session() as conn:
        with conn.cursor() as cur:
            where = "WHERE role = %s" if role else ""
            params = (role,) if role else ()
            cur.execute(f"SELECT count(*) FROM users {where}", params)
            total = cur.fetchone()[0]
            cur.execute(
                f"SELECT id, email, display_name, role, created_at, last_login_at, locked_until "
                f"FROM users {where} ORDER BY {order_clause(sort, USER_SORT, 'created_at', order)} "
                f"LIMIT %s OFFSET %s",
                params + (size, (page - 1) * size),
            )
            rows = cur.fetchall()
    return envelope(
        [
            {
                "id": str(r[0]),
                "email": r[1],
                "display_name": r[2],
                "role": r[3],
                "created_at": r[4].isoformat(),
                "last_login_at": r[5].isoformat() if r[5] else None,
                "locked": bool(r[6] and r[6] > datetime.datetime.now(datetime.timezone.utc)),
            }
            for r in rows
        ],
        total,
        page,
        size,
    )


@router.patch("/admin/users/{user_id}")
def update_user(request: Request, user_id: str, payload: dict):
    user = current_user(request)
    role = payload.get("role")
    if role not in ("admin", "creator"):
        raise HTTPException(422, "role must be admin or creator")
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("UPDATE users SET role = %s WHERE id = %s RETURNING id", (role, user_id))
            if cur.fetchone() is None:
                raise HTTPException(404, "user not found")
    audit(user["id"], "user.update_role", "user", user_id, {"role": role})
    return {"id": user_id, "role": role}


@router.post("/admin/users/{user_id}/reset-link")
def reset_link(request: Request, user_id: str):
    user = current_user(request)
    token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE id = %s", (user_id,))
            if cur.fetchone() is None:
                raise HTTPException(404, "user not found")
            cur.execute(
                "INSERT INTO password_resets (token_hash, user_id, created_by) VALUES (%s, %s, %s)",
                (token_hash, user_id, user["id"]),
            )
    audit(user["id"], "user.reset_link", "user", user_id)
    return {"url": f"{settings.web_origin}/reset?token={token}", "expires_in_minutes": 60}


@router.post("/admin/invites")
def create_invite(request: Request, payload: dict):
    user = current_user(request)
    code = secrets.token_urlsafe(12)
    email = payload.get("email")
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO invites (code, email, created_by) VALUES (%s, %s, %s) RETURNING id",
                (code, email, user["id"]),
            )
            invite_id = cur.fetchone()[0]
    audit(user["id"], "invite.create", "invite", str(invite_id), {"email": email})
    return {"id": str(invite_id), "code": code, "url": f"{settings.web_origin}/signup?code={code}"}


@router.get("/admin/invites")
def invites(request: Request):
    page, size, sort, order = parse(request, "created_at")
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM invites")
            total = cur.fetchone()[0]
            cur.execute(
                "SELECT id, code, email, created_at, expires_at, used_at, revoked_at "
                f"FROM invites ORDER BY {order_clause(sort, INVITE_SORT, 'created_at', order)} "
                "LIMIT %s OFFSET %s",
                (size, (page - 1) * size),
            )
            rows = cur.fetchall()
    return envelope(
        [
            {
                "id": str(r[0]),
                "code": r[1],
                "email": r[2],
                "created_at": r[3].isoformat(),
                "expires_at": r[4].isoformat(),
                "used": bool(r[5]),
                "revoked": bool(r[6]),
            }
            for r in rows
        ],
        total,
        page,
        size,
    )


@router.post("/admin/invites/{invite_id}/revoke")
def revoke_invite(request: Request, invite_id: str):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE invites SET revoked_at = now() WHERE id = %s AND revoked_at IS NULL RETURNING id",
                (invite_id,),
            )
            if cur.fetchone() is None:
                raise HTTPException(404, "invite not found")
    audit(user["id"], "invite.revoke", "invite", invite_id)
    return {"id": invite_id, "revoked": True}


@router.get("/admin/jobs")
def jobs(request: Request):
    page, size, sort, order = parse(request, "updated_at")
    state = request.query_params.get("state")
    with db.session() as conn:
        with conn.cursor() as cur:
            where = "WHERE state = %s" if state else ""
            params = [state] if state else []
            cur.execute(f"SELECT count(*) FROM jobs {where}", params)
            total = cur.fetchone()[0]
            cur.execute(
                "SELECT id, kind, state, attempts, retry_count, error, payload, updated_at "
                f"FROM jobs {where} ORDER BY {order_clause(sort, JOB_SORT, 'updated_at', order)} "
                "LIMIT %s OFFSET %s",
                params + [size, (page - 1) * size],
            )
            rows = cur.fetchall()
    return envelope(
        [
            {
                "id": str(r[0]),
                "kind": r[1],
                "state": r[2],
                "attempts": r[3],
                "retry_count": r[4],
                "error": r[5],
                "payload": r[6],
                "updated_at": r[7].isoformat(),
            }
            for r in rows
        ],
        total,
        page,
        size,
    )


@router.post("/admin/jobs/{job_id}/retry")
def retry_job(request: Request, job_id: str):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE jobs SET state = 'queued', locked_by = NULL, error = NULL, "
                "retry_count = 0, available_at = now(), updated_at = now() "
                "WHERE id = %s RETURNING id",
                (job_id,),
            )
            if cur.fetchone() is None:
                raise HTTPException(404, "job not found")
    audit(user["id"], "job.retry", "job", job_id)
    return {"id": job_id, "state": "queued"}


@router.get("/admin/audit")
def audit_log(request: Request):
    page, size, sort, order = parse(request, "created_at")
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM audit_log")
            total = cur.fetchone()[0]
            cur.execute(
                "SELECT id, actor_id, action, target_type, target_id, meta, created_at "
                f"FROM audit_log ORDER BY {order_clause(sort, AUDIT_SORT, 'created_at', order)} "
                "LIMIT %s OFFSET %s",
                (size, (page - 1) * size),
            )
            rows = cur.fetchall()
    return envelope(
        [
            {
                "id": str(r[0]),
                "actor_id": str(r[1]) if r[1] else None,
                "action": r[2],
                "target_type": r[3],
                "target_id": r[4],
                "meta": r[5],
                "created_at": r[6].isoformat(),
            }
            for r in rows
        ],
        total,
        page,
        size,
    )


@router.get("/admin/ai-usage")
def ai_usage(request: Request):
    page, size, sort, order = parse(request, "created_at")
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT count(*) FROM ai_usage")
            total = cur.fetchone()[0]
            cur.execute(
                "SELECT id, user_id, page, kind, provider, model, prompt_tokens, "
                "completion_tokens, latency_ms, fallback, created_at "
                f"FROM ai_usage ORDER BY {order_clause(sort, {'created_at': 'created_at', 'latency_ms': 'latency_ms'}, 'created_at', order)} "
                "LIMIT %s OFFSET %s",
                (size, (page - 1) * size),
            )
            rows = cur.fetchall()
    return envelope(
        [
            {
                "id": str(r[0]),
                "user_id": str(r[1]) if r[1] else None,
                "page": r[2],
                "kind": r[3],
                "provider": r[4],
                "model": r[5],
                "prompt_tokens": r[6],
                "completion_tokens": r[7],
                "latency_ms": r[8],
                "fallback": r[9],
                "created_at": r[10].isoformat(),
            }
            for r in rows
        ],
        total,
        page,
        size,
    )


@router.get("/admin/ai-config")
def ai_config(request: Request):
    """Which provider and model are configured, and whether a key is present.
    Never the key itself."""
    return {
        "provider": settings.llm_provider,
        "base_url": settings.llm_base_url,
        "model": settings.llm_model,
        "key_present": bool(settings.llm_api_key),
        "configured": settings.ai_configured,
    }


@router.get("/admin/storage")
def storage_status(request: Request):
    store = storage.get_storage()
    return {"driver": settings.storage_driver, "bytes": store.usage_bytes()}


@router.get("/admin/setup")
def setup_status(request: Request):
    """The same checks `make doctor` runs, for the admin Setup page."""
    from .doctor import run_checks

    return {"checks": run_checks()}
