"""R7: admin templates, users, job queue and health."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from . import db
from .users import current_user

router = APIRouter()


@router.get("/admin/templates")
def templates(request: Request):
    current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, config, weight FROM templates")
            return [{"id": r[0], "config": r[1], "weight": r[2]} for r in cur.fetchall()]


@router.get("/admin/users")
def users(request: Request):
    current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT id, display_name, role FROM users ORDER BY created_at")
            return [{"id": str(r[0]), "display_name": r[1], "role": r[2]} for r in cur.fetchall()]


@router.get("/admin/jobs")
def jobs(request: Request):
    current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, kind, state, attempts, payload, updated_at "
                "FROM jobs ORDER BY updated_at DESC LIMIT 50"
            )
            return [
                {
                    "id": str(r[0]),
                    "kind": r[1],
                    "state": r[2],
                    "attempts": r[3],
                    "payload": r[4],
                    "updated_at": r[5].isoformat(),
                }
                for r in cur.fetchall()
            ]


@router.post("/admin/jobs/{job_id}/retry")
def retry_job(request: Request, job_id: str):
    current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE jobs SET state = 'queued', locked_by = NULL, updated_at = now() "
                "WHERE id = %s RETURNING id",
                (job_id,),
            )
            if cur.fetchone() is None:
                raise HTTPException(404, "job not found")
    return {"id": job_id, "state": "queued"}
