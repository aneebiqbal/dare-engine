"""The engine activity log: model loads/unloads, job stages and cleanups."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from . import db
from .users import current_user, require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/admin/engine-events")
def engine_events(request: Request):
    current_user(request)
    try:
        limit = min(100, max(1, int(request.query_params.get("limit", 20))))
    except ValueError:
        limit = 20
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, kind, detail, created_at FROM engine_events "
                "ORDER BY created_at DESC LIMIT %s",
                (limit,),
            )
            rows = cur.fetchall()
    return {
        "items": [
            {
                "id": str(r[0]),
                "kind": r[1],
                "detail": r[2],
                "created_at": r[3].isoformat() if r[3] else None,
            }
            for r in rows
        ]
    }
