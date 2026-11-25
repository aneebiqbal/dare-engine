"""Client error reporting.

The browser posts a message, a stack and the path; an admin reads the recent
reports. This is the light, dependency-free half of error reporting: it is
stored in the same database, so it needs no external service and survives a
restart. For an external service, ship the reports from `/admin/errors` to
Sentry or a log drain; see `docs/deploy-web.md`.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field

from . import db
from .users import current_user, require_admin

router = APIRouter()


class ReportIn(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    stack: str | None = Field(default=None, max_length=8000)
    path: str | None = Field(default=None, max_length=500)


@router.post("/client-error")
def report(payload: ReportIn, request: Request):
    user_id = None
    try:
        user_id = current_user(request)["id"]
    except HTTPException:
        pass  # an expired session must not swallow the report
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO error_reports (user_id, message, stack, path) "
                "VALUES (%s, %s, %s, %s)",
                (user_id, payload.message, payload.stack, payload.path),
            )
    return {"ok": True}


@router.get("/admin/errors")
def admin_errors(request: Request):
    require_admin(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT e.id, e.message, e.path, e.created_at, u.display_name "
                "FROM error_reports e LEFT JOIN users u ON u.id = e.user_id "
                "ORDER BY e.created_at DESC LIMIT 50"
            )
            rows = cur.fetchall()
    return {
        "items": [
            {
                "id": str(r[0]),
                "message": r[1],
                "path": r[2],
                "created_at": r[3].isoformat(),
                "user": r[4],
            }
            for r in rows
        ]
    }
