"""Projects: one stream/recording moving through the clip pipeline.

A project is the unit of work. Its stage is *derived* from real artifacts
(the recording, the analysis jobs, the clips and the exports), never stored, so
the dashboard cannot drift from what actually happened.

Stages, in order:

    planned → recording → imported → analyzing → clips_ready → reviewed → exported

The heavy half is the analysis queue. `POST /projects/{id}/queue` marks a
project queued and enqueues a `run_project` job; the worker runs those one at a
time (a Postgres advisory lock) so two projects never load models at once.
"""
from __future__ import annotations

import json
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from . import db
from .users import current_user, require_admin

router = APIRouter(dependencies=[Depends(require_admin)])

STAGES = [
    "planned",
    "recording",
    "imported",
    "analyzing",
    "clips_ready",
    "reviewed",
    "exported",
]

# A flat progress number per stage, shown on the dashboard. Real work inside a
# stage (job progress, candidate counts) is returned alongside it.
STAGE_PROGRESS = {
    "planned": 0,
    "recording": 10,
    "imported": 25,
    "analyzing": 50,
    "clips_ready": 75,
    "reviewed": 90,
    "exported": 100,
}


def derive_stage(
    *,
    live: bool = False,
    recording: bool = False,
    analyzing: bool = False,
    ready_clips: int = 0,
    total_clips: int = 0,
    reviewed_clips: int = 0,
    exported: bool = False,
) -> str:
    """The project's stage from real state. Highest reached stage wins."""
    if exported:
        return "exported"
    if total_clips and reviewed_clips >= total_clips:
        return "reviewed"
    if ready_clips:
        return "clips_ready"
    if analyzing:
        return "analyzing"
    if recording:
        return "imported"
    if live:
        return "recording"
    return "planned"


def project_state(cur, project_id: str) -> dict | None:
    """Derive one project's live state. Returns None when it does not exist."""
    cur.execute(
        "SELECT id, user_id, name, game_id, recording_id, stream_id, vision, "
        "stage_note, queued_at, created_at, updated_at "
        "FROM projects WHERE id = %s",
        (project_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    (pid, user_id, name, game_id, recording_id, stream_id, vision,
     stage_note, queued_at, created_at, updated_at) = row

    live = False
    if stream_id:
        cur.execute("SELECT ended_at FROM streams WHERE id = %s", (stream_id,))
        stream = cur.fetchone()
        live = bool(stream and stream[0] is None)

    analyzing = False
    candidates = 0
    ready_clips = total_clips = reviewed_clips = 0
    exported = False
    if recording_id:
        cur.execute(
            "SELECT count(*) FROM jobs WHERE kind IN ('detect_moments', 'suggest_clips') "
            "AND payload->>'recording_id' = %s AND state IN ('queued', 'running')",
            (str(recording_id),),
        )
        analyzing = cur.fetchone()[0] > 0
        cur.execute(
            "SELECT count(*) FROM studio_candidates WHERE recording_id = %s",
            (recording_id,),
        )
        candidates = cur.fetchone()[0]
        # Clips are linked to the recording by the storage key the render used.
        cur.execute(
            "SELECT count(*), count(*) FILTER (WHERE c.state = 'ready'), "
            "count(*) FILTER (WHERE c.state IN ('approved', 'posted')) "
            "FROM clips c JOIN studio_recordings r ON r.storage_key = c.recording_key "
            "WHERE r.id = %s",
            (recording_id,),
        )
        total_clips, ready_clips, reviewed_clips = cur.fetchone()
        cur.execute(
            "SELECT count(*) FROM exports e JOIN clips c ON c.id = e.clip_id "
            "JOIN studio_recordings r ON r.storage_key = c.recording_key "
            "WHERE r.id = %s",
            (recording_id,),
        )
        exported = cur.fetchone()[0] > 0

    stage = derive_stage(
        live=live,
        recording=bool(recording_id),
        analyzing=analyzing,
        ready_clips=ready_clips,
        total_clips=total_clips,
        reviewed_clips=reviewed_clips,
        exported=exported,
    )
    position = None
    if queued_at is not None:
        cur.execute(
            "SELECT count(*) + 1 FROM projects WHERE queued_at IS NOT NULL "
            "AND (queued_at, created_at) < (%s, %s)",
            (queued_at, created_at),
        )
        position = cur.fetchone()[0]
    return {
        "id": str(pid),
        "name": name,
        "game_id": str(game_id) if game_id else None,
        "recording_id": str(recording_id) if recording_id else None,
        "stream_id": str(stream_id) if stream_id else None,
        "vision": bool(vision),
        "stage": stage,
        "stage_index": STAGES.index(stage),
        "progress": STAGE_PROGRESS[stage],
        "stage_note": stage_note,
        "candidates": candidates,
        "clips": {"ready": ready_clips, "total": total_clips, "reviewed": reviewed_clips},
        "queued": queued_at is not None,
        "queue_position": position,
        "created_at": created_at.isoformat() if created_at else None,
        "updated_at": updated_at.isoformat() if updated_at else None,
    }


def create_for_recording(cur, user_id: str, recording_id: str, name: str) -> str:
    """A recording starts a project. Called by upload and SSD import."""
    cur.execute(
        "INSERT INTO projects (user_id, name, recording_id) VALUES (%s, %s, %s) "
        "RETURNING id",
        (user_id, name[:120] or "Untitled project", recording_id),
    )
    return str(cur.fetchone()[0])


def attach_stream(cur, storage_key: str, stream_id: str) -> None:
    """Link the stream a render created back to its recording's project."""
    cur.execute(
        "UPDATE projects SET stream_id = %s, updated_at = now() "
        "WHERE recording_id = (SELECT id FROM studio_recordings WHERE storage_key = %s)",
        (stream_id, storage_key),
    )


@router.get("/projects")
def list_projects(request: Request):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM projects WHERE user_id = %s ORDER BY created_at DESC LIMIT 50",
                (user["id"],),
            )
            items = [project_state(cur, str(r[0])) for r in cur.fetchall()]
    return {"items": [i for i in items if i]}


@router.post("/projects")
def create_project(request: Request, payload: dict):
    user = current_user(request)
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(422, "name required")
    game_id = payload.get("game_id")
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO projects (user_id, name, game_id) VALUES (%s, %s, %s) "
                "RETURNING id",
                (user["id"], name[:120], game_id or None),
            )
            pid = str(cur.fetchone()[0])
            state = project_state(cur, pid)
    return state


@router.get("/projects/{project_id}")
def get_project(request: Request, project_id: str):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM projects WHERE id = %s", (project_id,))
            row = cur.fetchone()
            if row is None or str(row[0]) != str(user["id"]):
                raise HTTPException(404, "project not found")
            state = project_state(cur, project_id)
    return state


@router.post("/projects/{project_id}/attach")
def attach(request: Request, project_id: str, payload: dict):
    """Attach a studio recording to a project (one recording = one project)."""
    user = current_user(request)
    recording_id = payload.get("recording_id")
    if not recording_id:
        raise HTTPException(422, "recording_id required")
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM projects WHERE id = %s", (project_id,))
            row = cur.fetchone()
            if row is None or str(row[0]) != str(user["id"]):
                raise HTTPException(404, "project not found")
            cur.execute(
                "SELECT user_id FROM studio_recordings WHERE id = %s", (recording_id,)
            )
            rec = cur.fetchone()
            if rec is None or str(rec[0]) != str(user["id"]):
                raise HTTPException(404, "recording not found")
            cur.execute(
                "UPDATE projects SET recording_id = %s, stage_note = NULL, "
                "updated_at = now() WHERE id = %s",
                (recording_id, project_id),
            )
            state = project_state(cur, project_id)
    return state


@router.post("/projects/{project_id}/vision")
def set_vision(request: Request, project_id: str, payload: dict):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id FROM projects WHERE id = %s", (project_id,))
            row = cur.fetchone()
            if row is None or str(row[0]) != str(user["id"]):
                raise HTTPException(404, "project not found")
            cur.execute(
                "UPDATE projects SET vision = %s, updated_at = now() WHERE id = %s",
                (bool(payload.get("vision")), project_id),
            )
            state = project_state(cur, project_id)
    return state


@router.post("/projects/{project_id}/queue")
def queue(request: Request, project_id: str, payload: dict | None = None):
    """Mark the project queued and enqueue one analysis run.

    The worker claims the oldest queued project under an advisory lock, so two
    projects never analyse (and never load models) at the same time.
    """
    user = current_user(request)
    payload = payload or {}
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, queued_at FROM projects WHERE id = %s", (project_id,))
            row = cur.fetchone()
            if row is None or str(row[0]) != str(user["id"]):
                raise HTTPException(404, "project not found")
            if "vision" in payload:
                cur.execute(
                    "UPDATE projects SET vision = %s WHERE id = %s",
                    (bool(payload["vision"]), project_id),
                )
            cur.execute(
                "UPDATE projects SET queued_at = now(), updated_at = now() WHERE id = %s",
                (project_id,),
            )
            cur.execute(
                "INSERT INTO jobs (kind, payload, idempotency_key) "
                "VALUES ('run_project', %s, %s)",
                (
                    json.dumps({"project_id": project_id}),
                    f"run-project:{project_id}:{uuid.uuid4().hex}",
                ),
            )
            state = project_state(cur, project_id)
    return {"queued": True, "project_id": project_id, "state": state}


@router.delete("/projects/{project_id}")
def delete_project(request: Request, project_id: str):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM projects WHERE id = %s AND user_id = %s", (project_id, user["id"]))
    return {"deleted": True}
