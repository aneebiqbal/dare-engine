"""Posting calendar: a review-and-export queue with cadence guardrails.

Publishing is manual or YouTube-API only. TikTok and Instagram are approval
gated and are refused here until the platform grants access. The YouTube API is
not connected yet, so "publish" records the intent and is marked unproven.
"""
from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, HTTPException, Request

from . import db
from .users import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])

PLATFORMS = {
    "youtube": "YouTube",
    "tiktok": "TikTok (approval required)",
    "instagram": "Instagram (approval required)",
}
GATED = {"tiktok", "instagram"}
DAILY_SHORT_LIMIT = 2


def _entry(row) -> dict:
    return {
        "id": str(row[0]),
        "clip_id": str(row[1]),
        "date": row[2].isoformat() if row[2] else None,
        "platform": row[3],
        "state": row[4],
        "title": row[5],
        "duration_seconds": row[6],
    }


@router.get("/admin/calendar")
def calendar(request: Request, month: str = ""):
    month = month or datetime.date.today().strftime("%Y-%m")
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT ce.id, ce.clip_id, ce.scheduled_for, ce.platform, ce.state, "
                "c.title, c.duration_seconds "
                "FROM calendar_entries ce JOIN clips c ON c.id = ce.clip_id "
                "WHERE to_char(ce.scheduled_for, 'YYYY-MM') = %s "
                "ORDER BY ce.scheduled_for, c.created_at",
                (month,),
            )
            entries = [_entry(r) for r in cur.fetchall()]
            cur.execute(
                "SELECT c.id, c.title, c.duration_seconds "
                "FROM clips c JOIN assignments a ON a.id = c.assignment_id "
                "WHERE c.state = 'approved' AND NOT EXISTS ("
                "  SELECT 1 FROM calendar_entries ce WHERE ce.clip_id = c.id) "
                "ORDER BY c.created_at DESC LIMIT 50"
            )
            unscheduled = [
                {"id": str(r[0]), "title": r[1], "duration_seconds": r[2]}
                for r in cur.fetchall()
            ]
    per_day: dict[str, int] = {}
    for e in entries:
        per_day[e["date"]] = per_day.get(e["date"], 0) + 1
    warnings = [
        f"{day}: {n} Shorts scheduled — the default cadence is {DAILY_SHORT_LIMIT}/day."
        for day, n in sorted(per_day.items())
        if n > DAILY_SHORT_LIMIT
    ]
    return {
        "month": month,
        "entries": entries,
        "unscheduled": unscheduled,
        "warnings": warnings,
        "daily_limit": DAILY_SHORT_LIMIT,
        "platforms": PLATFORMS,
        "gated": sorted(GATED),
    }


@router.post("/admin/calendar")
def schedule(request: Request, payload: dict):
    clip_id = payload.get("clip_id")
    platform = (payload.get("platform") or "youtube").lower()
    day = payload.get("scheduled_for")
    if platform not in PLATFORMS:
        raise HTTPException(422, "unknown platform")
    if platform in GATED:
        raise HTTPException(403, "tiktok and instagram require platform approval")
    try:
        datetime.date.fromisoformat(day)
    except (TypeError, ValueError):
        raise HTTPException(422, "scheduled_for must be a date (YYYY-MM-DD)")
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT c.id FROM clips c JOIN assignments a ON a.id = c.assignment_id "
                "WHERE c.id = %s",
                (clip_id,),
            )
            if cur.fetchone() is None:
                raise HTTPException(404, "clip not found")
            cur.execute(
                "INSERT INTO calendar_entries (clip_id, scheduled_for, platform) "
                "VALUES (%s, %s, %s) "
                "ON CONFLICT (clip_id, platform) DO UPDATE SET scheduled_for = EXCLUDED.scheduled_for",
                (clip_id, day, platform),
            )
    return {"ok": True}


@router.post("/admin/calendar/{entry_id}/publish")
def publish(request: Request, entry_id: str):
    # Manual publish marker. The YouTube Data API is not connected, so this is
    # not a real upload; it records that the admin published it themselves.
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE calendar_entries SET state = 'published', published_at = now() "
                "WHERE id = %s",
                (entry_id,),
            )
    return {"ok": True, "unproven": "youtube-api"}


@router.delete("/admin/calendar/{entry_id}")
def remove(request: Request, entry_id: str):
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM calendar_entries WHERE id = %s", (entry_id,))
    return {"ok": True}
