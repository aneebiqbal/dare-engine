"""Tour progress, stored per user."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request

from . import db
from .users import current_user

router = APIRouter()


@router.get("/tours")
def all_progress(request: Request):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT tour_id, step_index, completed, skipped FROM tour_progress "
                "WHERE user_id = %s",
                (user["id"],),
            )
            rows = cur.fetchall()
    return [
        {"tour_id": r[0], "step_index": r[1], "completed": r[2], "skipped": r[3]}
        for r in rows
    ]


@router.post("/tours/{tour_id}")
def save_progress(request: Request, tour_id: str, payload: dict):
    user = current_user(request)
    step_index = int(payload.get("step_index", 0))
    completed = bool(payload.get("completed", False))
    skipped = bool(payload.get("skipped", False))
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO tour_progress (user_id, tour_id, step_index, completed, skipped) "
                "VALUES (%s, %s, %s, %s, %s) "
                "ON CONFLICT (user_id, tour_id) DO UPDATE SET "
                "step_index = EXCLUDED.step_index, completed = EXCLUDED.completed, "
                "skipped = EXCLUDED.skipped, updated_at = now()",
                (user["id"], tour_id, step_index, completed, skipped),
            )
    return {"tour_id": tour_id, "step_index": step_index, "completed": completed, "skipped": skipped}


@router.delete("/tours/{tour_id}")
def reset_progress(request: Request, tour_id: str):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "DELETE FROM tour_progress WHERE user_id = %s AND tour_id = %s",
                (user["id"], tour_id),
            )
    return {"ok": True}
