"""The automatic upload-to-Shorts pipeline API.

One upload starts one run. The API stores the source on the SSD in a
per-project folder, queues a `run_pipeline` job and reads live progress back.
It never renders, transcribes or moves media to a cloud: the worker does the
heavy work and the database holds only metadata.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import tempfile
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from . import db, storage
from .config import settings
from .studio import _probe, require_disk
from .users import current_user, require_admin

router = APIRouter(dependencies=[Depends(require_admin)])

CHUNK_SIZE = 1024 * 1024
DEFAULT_TOP_N = 10


def _owned_run(cur, request: Request, run_id: str) -> dict:
    user = current_user(request)
    cur.execute("SELECT * FROM pipeline_runs WHERE id = %s", (run_id,))
    row = cur.fetchone()
    if row is None:
        raise HTTPException(404, "pipeline run not found")
    cols = [d.name for d in cur.description]
    run = dict(zip(cols, row))
    if str(run["user_id"]) != str(user["id"]):
        raise HTTPException(404, "pipeline run not found")
    return run


def _enqueue(run_id: str, project_id: str | None = None) -> None:
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO jobs (kind, payload, idempotency_key) "
                "VALUES ('run_pipeline', %s, %s)",
                (
                    json.dumps({"run_id": run_id, "project_id": project_id}),
                    f"pipeline:{run_id}:{uuid.uuid4().hex}",
                ),
            )


@router.post("/pipeline/upload")
async def upload(request: Request, file: UploadFile = File(...)):
    """Accept one video and start the automatic pipeline. Zero manual steps."""
    user = current_user(request)
    suffix = pathlib.Path(file.filename or "video.mp4").suffix or ".mp4"
    with tempfile.TemporaryDirectory(prefix="pipeline-upload-") as tmp:
        require_disk(tmp)
        local = pathlib.Path(tmp) / f"source{suffix}"
        with open(local, "wb") as out:
            while chunk := await file.read(CHUNK_SIZE):
                out.write(chunk)
        specs = _probe(str(local))
        name = pathlib.Path(file.filename or "Video").stem[:120] or "Video"
        with db.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO projects (user_id, name) VALUES (%s, %s) RETURNING id",
                    (user["id"], name),
                )
                project_id = str(cur.fetchone()[0])
                cur.execute(
                    "INSERT INTO pipeline_runs (project_id, user_id, top_n) "
                    "VALUES (%s, %s, %s) RETURNING id",
                    (project_id, user["id"], DEFAULT_TOP_N),
                )
                run_id = str(cur.fetchone()[0])
                key = f"projects/{run_id}/source{suffix}"
                storage.put_file(key, str(local))
                cur.execute(
                    "INSERT INTO studio_recordings "
                    "(id, user_id, filename, storage_key, duration_seconds, width, height) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                    (
                        run_id, user["id"], file.filename, key,
                        specs["duration_seconds"], specs["width"], specs["height"],
                    ),
                )
                cur.execute(
                    "UPDATE projects SET recording_id = %s WHERE id = %s",
                    (run_id, project_id),
                )
                cur.execute(
                    "UPDATE pipeline_runs SET recording_id = %s, source_key = %s "
                    "WHERE id = %s",
                    (run_id, key, run_id),
                )
                cur.execute(
                    "INSERT INTO jobs (kind, payload, idempotency_key) "
                    "VALUES ('run_pipeline', %s, %s)",
                    (
                        json.dumps({"run_id": run_id, "project_id": project_id}),
                        f"pipeline:{run_id}:{uuid.uuid4().hex}",
                    ),
                )
    return {"run_id": run_id, "project_id": project_id, **specs}


@router.get("/pipeline")
def list_runs(request: Request):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT r.id, r.project_id, r.state, r.stage, r.progress, r.action, "
                "r.eta_seconds, r.remaining_seconds, r.model_loaded, r.error, "
                "r.created_at, r.finished_at, p.name "
                "FROM pipeline_runs r JOIN projects p ON p.id = r.project_id "
                "WHERE r.user_id = %s ORDER BY r.created_at DESC LIMIT 50",
                (user["id"],),
            )
            cols = [d.name for d in cur.description]
            items = [dict(zip(cols, row)) for row in cur.fetchall()]
    return {
        "items": [
            {
                **{k: v for k, v in item.items() if k not in ("created_at", "finished_at")},
                "created_at": item["created_at"].isoformat() if item["created_at"] else None,
                "finished_at": item["finished_at"].isoformat() if item["finished_at"] else None,
            }
            for item in items
        ]
    }


def _candidate_dict(cur, run_id: str, row: tuple) -> dict:
    cols = [d.name for d in cur.description]
    c = dict(zip(cols, row))
    return {
        "id": str(c["id"]),
        "start": c["start_seconds"],
        "end": c["end_seconds"],
        "cheap_score": c["cheap_score"],
        "vision_score": c["vision_score"],
        "final_score": c["final_score"],
        "reasons": c["reasons"],
        "vision_reason": c["vision_reason"],
        "origin": c["origin"],
        "selected": c["selected"],
        "status": c["status"],
        "label": c["label"],
        "hook": c["hook"],
        "reason": c["reason"],
        "scores": c["scores"],
        "composite": c["composite"],
        "thumb_url": f"/pipeline/{run_id}/candidates/{c['id']}/thumb" if c["thumb_key"] else None,
        "clip_id": str(c["clip_id"]) if c["clip_id"] else None,
        "error": c["error"],
    }


@router.get("/pipeline/{run_id}")
def get_run(request: Request, run_id: str):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            run = _owned_run(cur, request, run_id)
            cur.execute(
                "SELECT * FROM pipeline_candidates WHERE run_id = %s "
                "ORDER BY final_score DESC",
                (run_id,),
            )
            candidates = [_candidate_dict(cur, run_id, row) for row in cur.fetchall()]
            clip_ids = [c["clip_id"] for c in candidates if c["clip_id"]]
            clips: list[dict] = []
            if clip_ids:
                cur.execute(
                    "SELECT id, state, duration_seconds, title, layout, caption_style "
                    "FROM clips WHERE id = ANY(%s)",
                    (clip_ids,),
                )
                cols = [d.name for d in cur.description]
                clips = [
                    {
                        **dict(zip(cols, row)),
                        "id": str(row[0]),
                        "thumb_url": f"/clips/{row[0]}/thumbnail",
                        "download_url": f"/clips/{row[0]}/download",
                    }
                    for row in cur.fetchall()
                ]
    run_out = dict(run)
    for key in ("created_at", "updated_at", "started_at", "finished_at"):
        run_out[key] = run_out[key].isoformat() if run_out.get(key) else None
    return {"run": run_out, "candidates": candidates, "clips": clips}


@router.get("/pipeline/{run_id}/candidates/{candidate_id}/thumb")
def candidate_thumb(request: Request, run_id: str, candidate_id: str):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            _owned_run(cur, request, run_id)
            cur.execute(
                "SELECT thumb_key FROM pipeline_candidates WHERE id = %s AND run_id = %s",
                (candidate_id, run_id),
            )
            row = cur.fetchone()
    if row is None or not row[0]:
        raise HTTPException(404, "no thumbnail")
    key = row[0]
    if settings.storage_driver == "local":
        path = (pathlib.Path(settings.storage_local_dir) / key).resolve()
        if not path.is_file():
            raise HTTPException(404, "no thumbnail")
        return FileResponse(
            path, media_type="image/jpeg", headers={"Cache-Control": "public, max-age=3600"}
        )
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="pipe-thumb-")) / "thumb.jpg"
    storage.get_file(key, str(tmp))
    return FileResponse(
        tmp, media_type="image/jpeg",
        background=BackgroundTask(shutil.rmtree, tmp.parent),
    )


@router.post("/pipeline/{run_id}/timestamps")
def add_timestamps(request: Request, run_id: str, payload: dict):
    """Add exact windows to the cut list. The AI suggestions are never replaced."""
    user = current_user(request)
    raw = payload.get("timestamps") or []
    if not isinstance(raw, list):
        raise HTTPException(422, "timestamps must be a list")
    ignored: list[str] = []
    valid: list[dict] = []
    enqueue_needed = False
    project_id = None
    with db.session() as conn:
        with conn.cursor() as cur:
            run = _owned_run(cur, request, run_id)
            project_id = str(run["project_id"])
            state = run["state"]
            duration = float(run.get("duration_seconds") or 0.0)
            if duration <= 0:
                cur.execute(
                    "SELECT duration_seconds FROM studio_recordings WHERE id = %s",
                    (run["recording_id"],),
                )
                found = cur.fetchone()
                duration = float(found[0]) if found and found[0] else 0.0
            for item in raw:
                try:
                    start = float(item.get("start"))
                    end = float(item.get("end"))
                except (TypeError, AttributeError, ValueError):
                    ignored.append(f"not a window: {item!r}")
                    continue
                if start < 0 or end <= start or (duration and end > duration + 1e-6):
                    ignored.append(f"outside the video: {start:.1f}-{end:.1f}s")
                    continue
                valid.append({"start": start, "end": end})

            cur.execute(
                "SELECT count(*) FROM pipeline_candidates WHERE run_id = %s", (run_id,)
            )
            has_candidates = cur.fetchone()[0] > 0
            stage = run["stage"]
            will_rank = stage in ("ingest", "scan", "regions") or (
                stage == "detect" and not has_candidates
            )
            if will_rank:
                merged = list(run.get("timestamps") or []) + valid
                cur.execute(
                    "UPDATE pipeline_runs SET timestamps = %s, updated_at = now() "
                    "WHERE id = %s",
                    (json.dumps(merged), run_id),
                )
                enqueue_needed = state in ("paused", "failed")
            else:
                for item in valid:
                    cur.execute(
                        "INSERT INTO pipeline_candidates "
                        "(run_id, start_seconds, end_seconds, cheap_score, final_score, "
                        " reasons, origin, selected) "
                        "VALUES (%s, %s, %s, 1.5, 1.5, '[\"you marked this\"]', 'user', false)",
                        (run_id, item["start"], item["end"]),
                    )
                timings = dict(run.get("stage_timings") or {})
                for done in ("signals", "score", "cut", "render"):
                    timings.pop(done, None)
                cur.execute(
                    "UPDATE pipeline_runs SET state = 'queued', stage = 'detect', "
                    "progress = 22, stage_timings = %s, timestamps = '[]', "
                    "error = NULL, updated_at = now() WHERE id = %s",
                    (json.dumps(timings), run_id),
                )
                enqueue_needed = True
    if valid and enqueue_needed:
        _enqueue(run_id, project_id)
    return {"added": len(valid), "ignored": ignored}


@router.post("/pipeline/{run_id}/resume")
def resume(request: Request, run_id: str):
    """Re-queue a paused or failed run. It continues from the last completed stage."""
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            run = _owned_run(cur, request, run_id)
            if run["state"] == "done":
                raise HTTPException(422, "this run is already done")
            cur.execute(
                "UPDATE pipeline_runs SET state = 'queued', error = NULL, "
                "action = 'Queued to resume', updated_at = now() WHERE id = %s",
                (run_id,),
            )
            project_id = str(run["project_id"])
    _enqueue(run_id, project_id)
    return {"run_id": run_id, "state": "queued"}
