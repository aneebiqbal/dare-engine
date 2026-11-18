"""Results, settings, data export and account deletion."""
from __future__ import annotations

import json
import pathlib
import tempfile

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse

from . import db, storage
from .users import audit, current_user

router = APIRouter()


def _score(views: int, avg_view_percentage: float | None) -> float:
    return round(views / 1000 + (avg_view_percentage or 0) / 100, 4)


@router.post("/metrics")
def record_metric(request: Request, payload: dict):
    """Manual metric entry. The YouTube collector is built, unproven."""
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
                "SELECT m.card->>'mode', COUNT(c.id), COALESCE(SUM(mm.views), 0), "
                "AVG(mm.avg_view_percentage) "
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
            {
                "mode": r[0],
                "clips": r[1],
                "views": int(r[2] or 0),
                "avg_view_percentage": round(float(r[3]), 2) if r[3] else None,
            }
            for r in by_type
        ],
    }


@router.get("/settings")
def get_settings(request: Request):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT caption_style, layout_preference, voice_over_default, voice "
                "FROM user_settings WHERE user_id = %s",
                (user["id"],),
            )
            row = cur.fetchone()
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
        "caption_style": row[0] if row else "word",
        "layout_preference": row[1] if row else "rotate",
        "voice_over_default": bool(row[2]) if row else False,
        "voice": row[3] if row else None,
    }


@router.patch("/settings")
def update_settings(request: Request, payload: dict):
    user = current_user(request)
    fields = {}
    for key in ("caption_style", "layout_preference", "voice_over_default", "voice"):
        if key in payload:
            fields[key] = payload[key]
    if not fields:
        raise HTTPException(422, "nothing to update")
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO user_settings (user_id, caption_style, layout_preference, "
                "voice_over_default, voice) VALUES (%s, %s, %s, %s, %s) "
                "ON CONFLICT (user_id) DO UPDATE SET "
                "caption_style = COALESCE(EXCLUDED.caption_style, user_settings.caption_style), "
                "layout_preference = COALESCE(EXCLUDED.layout_preference, user_settings.layout_preference), "
                "voice_over_default = EXCLUDED.voice_over_default, "
                "voice = COALESCE(EXCLUDED.voice, user_settings.voice), updated_at = now()",
                (
                    user["id"],
                    fields.get("caption_style", "word"),
                    fields.get("layout_preference", "rotate"),
                    fields.get("voice_over_default", False),
                    fields.get("voice"),
                ),
            )
    audit(user["id"], "settings.update", "user", user["id"], fields)
    return {"ok": True, **fields}


@router.get("/account/export")
def export_account(request: Request):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, display_name, role, created_at FROM users WHERE id = %s",
                (user["id"],),
            )
            row = cur.fetchone()
            cur.execute(
                "SELECT a.mission_id, a.date, a.state FROM assignments a WHERE a.user_id = %s",
                (user["id"],),
            )
            assignments = [
                {"mission_id": r[0], "date": r[1].isoformat(), "state": r[2]}
                for r in cur.fetchall()
            ]
    data = {
        "user": {
            "id": str(row[0]) if row else user["id"],
            "email": row[1] if row else None,
            "display_name": row[2] if row else None,
            "role": row[3] if row else None,
            "created_at": row[4].isoformat() if row and row[4] else None,
        },
        "assignments": assignments,
    }
    tmp = pathlib.Path(tempfile.mkdtemp()) / "clipdesk-export.json"
    tmp.write_text(json.dumps(data, indent=2))
    return FileResponse(tmp, media_type="application/json", filename="clipdesk-export.json")


@router.delete("/account")
def delete_account(request: Request):
    user = current_user(request)
    store = storage.get_storage()

    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM clips WHERE assignment_id IN "
                "(SELECT id FROM assignments WHERE user_id = %s)",
                (user["id"],),
            )
            clip_ids = [str(r[0]) for r in cur.fetchall()]
            cur.execute(
                "SELECT audio_key FROM voice_overs WHERE clip_id = ANY(%s) "
                "AND audio_key IS NOT NULL",
                (clip_ids,),
            )
            preview_keys = [r[0] for r in cur.fetchall()]
            cur.execute("DELETE FROM users WHERE id = %s", (user["id"],))

    store.delete_prefix(f"recordings/{user['id']}/")
    for clip_id in clip_ids:
        store.delete_prefix(f"clips/{clip_id}/")
    for key in preview_keys:
        store.delete_prefix(key)
    return {"ok": True}
