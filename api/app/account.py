"""R5 results, R6 settings and account deletion."""
from __future__ import annotations

import pathlib
import tempfile

from fastapi import APIRouter, HTTPException, Request

from . import db, storage
from .users import current_user

router = APIRouter()


def _score(views: int, avg_view_percentage: float | None) -> float:
    return round(views / 1000 + (avg_view_percentage or 0) / 100, 4)


@router.post("/metrics")
def record_metric(request: Request, payload: dict):
    """Manual metric entry (R5). The YouTube collector is built, unproven."""
    user = current_user(request)
    clip_id = payload.get("clip_id")
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT c.id FROM clips c JOIN assignments a ON a.id = c.assignment_id "
                "WHERE c.id = %s AND a.user_id = %s",
                (clip_id, user["id"]),
            )
            if cur.fetchone() is None:
                raise HTTPException(404, "clip not found")
            cur.execute(
                "INSERT INTO posts (clip_id, state) VALUES (%s, 'manual') "
                "ON CONFLICT DO NOTHING RETURNING id",
                (clip_id,),
            )
            row = cur.fetchone()
            post_id = row[0] if row else None
            if post_id is None:
                cur.execute("SELECT id FROM posts WHERE clip_id = %s LIMIT 1", (clip_id,))
                post_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO metrics (post_id, views, avg_view_percentage) VALUES (%s, %s, %s)",
                (post_id, int(payload.get("views", 0)), payload.get("avg_view_percentage")),
            )
            cur.execute(
                "SELECT a.mission_id FROM assignments a JOIN clips c ON c.assignment_id = a.id "
                "WHERE c.id = %s",
                (clip_id,),
            )
            mission = cur.fetchone()
            if mission:
                score = _score(int(payload.get("views", 0)), payload.get("avg_view_percentage"))
                cur.execute("UPDATE missions SET score = %s WHERE id = %s", (score, mission[0]))
    return {"ok": True, "source": "manual"}


@router.get("/results")
def results(request: Request):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT c.id, c.title, SUM(m.views), AVG(m.avg_view_percentage) "
                "FROM clips c "
                "JOIN assignments a ON a.id = c.assignment_id "
                "LEFT JOIN posts p ON p.clip_id = c.id "
                "LEFT JOIN metrics m ON m.post_id = p.id "
                "WHERE a.user_id = %s GROUP BY c.id, c.title ORDER BY c.created_at DESC",
                (user["id"],),
            )
            rows = cur.fetchall()
            cur.execute(
                "SELECT m.card->>'mode', COUNT(c.id), COALESCE(SUM(mm.views), 0) "
                "FROM clips c JOIN assignments a ON a.id = c.assignment_id "
                "JOIN missions m ON m.id = a.mission_id "
                "LEFT JOIN posts p ON p.clip_id = c.id "
                "LEFT JOIN metrics mm ON mm.post_id = p.id "
                "WHERE a.user_id = %s GROUP BY m.card->>'mode'",
                (user["id"],),
            )
            by_type = cur.fetchall()
    return {
        "clips": [
            {
                "clip_id": str(r[0]),
                "title": r[1],
                "views": int(r[2] or 0),
                "avg_view_percentage": round(float(r[3]), 2) if r[3] else None,
                "source": "manual",
            }
            for r in rows
        ],
        "by_type": [
            {"mode": r[0], "clips": r[1], "views": int(r[2] or 0)} for r in by_type
        ],
    }


@router.get("/settings")
def settings(request: Request):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT COUNT(*) FROM clips c JOIN assignments a ON a.id = c.assignment_id "
                "WHERE a.user_id = %s",
                (user["id"],),
            )
            used = cur.fetchone()[0]
    return {
        "plan": "free",
        "clips_used": used,
        "clips_limit": 5,
        "caption_style": "word",
        "layout_preference": "rotate",
    }


@router.delete("/account")
def delete_account(request: Request):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM users WHERE id = %s", (user["id"],))
    # Remove the user's stored files.
    client = storage._client()
    prefix = f"recordings/{user['id']}/"
    try:
        objects = client.list_objects_v2(Bucket=storage.settings.s3_bucket, Prefix=prefix)
        for obj in objects.get("Contents", []):
            client.delete_object(Bucket=storage.settings.s3_bucket, Key=obj["Key"])
    except Exception:
        pass
    return {"ok": True}
