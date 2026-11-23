"""The admin overview: one batched read of everything that is happening.

The dashboard used to fire eight requests and render tiles. This returns the
live state, the queue and what needs the user in one round trip, so the
command center paints fast and every number links to the page that acts on it.
"""
from __future__ import annotations

import datetime

from fastapi import APIRouter, Depends, Request

from . import db, keys, studio
from .projects import project_state
from .users import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


def _serialize_run(r) -> dict:
    return {
        "id": str(r[0]),
        "game_id": str(r[1]),
        "game_name": r[2],
        "status": r[3],
        "stage": r[4],
        "detail": r[5],
        "source_counts": r[6],
        "ideas_count": r[7],
        "fallback": r[8],
        "error": r[9],
        "created_at": r[10].isoformat() if r[10] else None,
        "finished_at": r[11].isoformat() if r[11] else None,
    }


_RUN_SELECT = (
    "SELECT r.id, r.game_id, g.name, r.status, r.stage, r.detail, r.source_counts, "
    "r.ideas_count, r.fallback, r.error, r.created_at, r.finished_at "
    "FROM research_runs r JOIN games g ON g.id = r.game_id "
)


def _overview() -> dict:
    with db.session() as conn:
        with conn.cursor() as cur:
            # The five scalar counts go in one round trip: every extra statement
            # is another Neon latency hit on the command center.
            cur.execute(
                "SELECT "
                "(SELECT json_object_agg(state, n) FROM "
                "  (SELECT state, count(*) AS n FROM jobs GROUP BY state) s), "
                "(SELECT json_object_agg(status, n) FROM "
                "  (SELECT status, count(*) AS n FROM missions GROUP BY status) s), "
                "(SELECT count(*) FROM clips WHERE created_at::date = current_date), "
                "(SELECT count(*) FROM users), "
                "(SELECT count(*) FROM users WHERE role = 'admin'), "
                "(SELECT count(*) FROM users WHERE locked_until IS NOT NULL "
                "  AND locked_until > now()), "
                "(SELECT count(*) FROM invites WHERE used_at IS NULL AND revoked_at IS NULL)"
            )
            (job_json, pool_json, clips_today, users_total, admins, locked, open_invites) = (
                cur.fetchone()
            )
            job_counts = job_json or {}
            pool = pool_json or {}
            cur.execute(
                "SELECT id, kind, state, stage, error, updated_at FROM jobs "
                "WHERE state IN ('queued', 'running', 'failed') "
                "ORDER BY updated_at DESC LIMIT 12"
            )
            active_jobs = [
                {
                    "id": str(r[0]),
                    "kind": r[1],
                    "state": r[2],
                    "stage": r[3],
                    "error": r[4],
                    "updated_at": r[5].isoformat() if r[5] else None,
                }
                for r in cur.fetchall()
            ]

            cur.execute(_RUN_SELECT + "ORDER BY r.created_at DESC LIMIT 12")
            runs = [_serialize_run(r) for r in cur.fetchall()]

            cur.execute("SELECT id FROM projects ORDER BY created_at DESC LIMIT 50")
            projects = [project_state(cur, str(r[0])) for r in cur.fetchall()]

            cur.execute(
                "SELECT c.id, c.title, COALESCE(SUM(m.views), 0), "
                "AVG(m.avg_view_percentage), COALESCE(SUM(m.swiped), 0), "
                "COALESCE(SUM(m.saves), 0) "
                "FROM clips c LEFT JOIN posts p ON p.clip_id = c.id "
                "LEFT JOIN metrics m ON m.post_id = p.id "
                "GROUP BY c.id, c.title ORDER BY c.created_at DESC"
            )
            clip_rows = cur.fetchall()

            cur.execute(
                "SELECT id, kind, detail, created_at FROM engine_events "
                "ORDER BY created_at DESC LIMIT 12"
            )
            activity = [
                {
                    "id": str(r[0]),
                    "kind": r[1],
                    "detail": r[2],
                    "created_at": r[3].isoformat() if r[3] else None,
                }
                for r in cur.fetchall()
            ]

    clips = [
        {
            "clip_id": str(r[0]),
            "title": r[1],
            "views": int(r[2] or 0),
            "avg_view_percentage": round(float(r[3]), 2) if r[3] else None,
            "swiped": int(r[4] or 0),
            "saves": int(r[5] or 0),
        }
        for r in clip_rows
    ]
    with_metrics = [c for c in clips if c["views"] > 0]
    best = max(with_metrics, key=lambda c: c["views"]) if with_metrics else None
    worst = (
        min(
            with_metrics,
            key=lambda c: (
                c["avg_view_percentage"]
                if c["avg_view_percentage"] is not None
                else 101
            ),
        )
        if with_metrics
        else None
    )

    key_status = keys.status_list()
    failing_keys = [
        i["name"] for i in key_status["integrations"]
        if i["configured"] and i["status"] == "invalid"
    ]
    unreachable_keys = [
        i["name"] for i in key_status["integrations"]
        if i["configured"] and i["status"] == "unreachable"
    ]

    try:
        system = studio.system_load(None)
    except Exception:
        system = None

    return {
        "generated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "jobs": {
            "counts": job_counts,
            "active": active_jobs,
            "running": job_counts.get("running", 0) + job_counts.get("queued", 0),
            "failed": job_counts.get("failed", 0),
        },
        "research": {
            "active": [r for r in runs if r["status"] == "running"],
            "recent": runs,
        },
        "projects": [p for p in projects if p],
        "pool": {
            "candidate": pool.get("candidate", 0),
            "unverified": pool.get("unverified", 0),
            "rejected": pool.get("rejected", 0),
        },
        "keys": {
            "research_sources_configured": key_status["research_sources_configured"],
            "failing": failing_keys,
            "unreachable": unreachable_keys,
            "integrations": key_status["integrations"],
        },
        "system": system,
        "activity": activity,
        "results": {
            "best": best,
            "worst": worst,
            "total_views": sum(c["views"] for c in clips),
        },
        "clips_today": clips_today,
        "users": {"total": users_total, "admins": admins, "locked": locked},
        "invites": {"open": open_invites},
    }


@router.get("/admin/overview")
def overview(request: Request):
    return _overview()
