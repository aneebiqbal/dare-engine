"""Admin clip studio: upload a recording, find moments, render accepted windows.

Everything stays on the machine. The detector runs in the worker (it needs
faster-whisper); the API stores the recording, queues the job and reads back the
ranked candidates.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import subprocess
import tempfile
import time
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from . import db, storage
from .config import settings
from .clips import _create_clips
from .projects import create_for_recording
from .users import current_user, require_admin

router = APIRouter(dependencies=[Depends(require_admin)])

CHUNK_SIZE = 1024 * 1024


def _probe(path: str) -> dict:
    """ffprobe a recording, or a clear 422 — never an opaque 500."""
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-show_entries", "stream=codec_type,width,height",
                "-of", "json", path,
            ],
            capture_output=True, text=True, check=True, timeout=60,
        ).stdout
        data = json.loads(out)
        duration = float(data["format"]["duration"])
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, KeyError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(422, f"that file is not a readable video ({type(exc).__name__})")
    if duration < 1.0:
        raise HTTPException(422, f"that recording is too short ({duration:.1f}s) to clip")
    width = height = 0
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video":
            width, height = stream.get("width", 0), stream.get("height", 0)
            break
    return {
        "duration_seconds": round(duration, 3),
        "width": width,
        "height": height,
    }


def require_disk(path: str, needed_mb: int = 500) -> None:
    """Fail with a clear message before a long upload or render fills the disk."""
    free = shutil.disk_usage(path).free
    if free < needed_mb * 1_000_000:
        raise HTTPException(
            507, f"not enough free disk space ({free / 1_000_000:.0f} MB free, need {needed_mb} MB)"
        )


def _owned_recording(cur, request, recording_id: str):
    user = current_user(request)
    cur.execute(
        "SELECT id, user_id, filename, storage_key, duration_seconds, width, height, "
        "whisper_device, whisper_compute_type, encoder, vision_model, vision_seconds "
        "FROM studio_recordings WHERE id = %s",
        (recording_id,),
    )
    row = cur.fetchone()
    if row is None or str(row[1]) != str(user["id"]):
        raise HTTPException(404, "recording not found")
    return row


@router.post("/studio/upload")
async def upload(request: Request, file: UploadFile = File(...)):
    user = current_user(request)
    suffix = pathlib.Path(file.filename or "recording.mp4").suffix or ".mp4"
    recording_id = str(uuid.uuid4())
    key = f"recordings/{user['id']}/studio-{recording_id}{suffix}"
    with tempfile.TemporaryDirectory(prefix="studio-") as tmp:
        require_disk(tmp)
        local = pathlib.Path(tmp) / f"recording{suffix}"
        with open(local, "wb") as out:
            while chunk := await file.read(CHUNK_SIZE):
                out.write(chunk)
        specs = _probe(str(local))
        storage.put_file(key, str(local))
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO studio_recordings "
                "(id, user_id, filename, storage_key, duration_seconds, width, height) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (recording_id, user["id"], file.filename, key,
                 specs["duration_seconds"], specs["width"], specs["height"]),
            )
            create_for_recording(cur, user["id"], recording_id, file.filename or "Recording")
    return {"recording_id": recording_id, "filename": file.filename, **specs}


@router.post("/studio/detect")
def detect(request: Request, payload: dict):
    with db.session() as conn:
        with conn.cursor() as cur:
            row = _owned_recording(cur, request, payload["recording_id"])
            recording_id, key = str(row[0]), row[3]
            cur.execute("DELETE FROM studio_candidates WHERE recording_id = %s", (recording_id,))
            cur.execute(
                "DELETE FROM jobs WHERE kind = 'detect_moments' "
                "AND payload->>'recording_id' = %s AND state IN ('queued', 'running')",
                (recording_id,),
            )
            cur.execute(
                "INSERT INTO jobs (kind, payload, idempotency_key) "
                "VALUES ('detect_moments', %s, %s)",
                (
                    json.dumps({
                        "recording_id": recording_id,
                        "storage_key": key,
                        "top_n": int(payload.get("top_n", 5)),
                    }),
                    f"detect:{recording_id}:{uuid.uuid4().hex}",
                ),
            )
    return {"state": "queued"}


@router.post("/studio/vision")
def vision_suggest(request: Request, payload: dict):
    """Optional: enqueue the sampled VLM pass. Off unless the admin asks."""
    with db.session() as conn:
        with conn.cursor() as cur:
            row = _owned_recording(cur, request, payload["recording_id"])
            recording_id, key = str(row[0]), row[3]
            cur.execute(
                "DELETE FROM jobs WHERE kind = 'suggest_clips' "
                "AND payload->>'recording_id' = %s AND state IN ('queued', 'running')",
                (recording_id,),
            )
            cur.execute(
                "INSERT INTO jobs (kind, payload, idempotency_key) "
                "VALUES ('suggest_clips', %s, %s)",
                (
                    json.dumps({
                        "recording_id": recording_id,
                        "storage_key": key,
                        "top_n": int(payload.get("top_n", 5)),
                    }),
                    f"vision:{recording_id}:{uuid.uuid4().hex}",
                ),
            )
    return {"state": "queued"}


@router.get("/studio/candidates/{candidate_id}/thumb")
def candidate_thumb(request: Request, candidate_id: str):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT c.thumb_key, r.user_id FROM studio_candidates c "
                "JOIN studio_recordings r ON r.id = c.recording_id "
                "WHERE c.id = %s",
                (candidate_id,),
            )
            row = cur.fetchone()
    if row is None or not row[0] or str(row[1]) != str(user["id"]):
        raise HTTPException(404, "no thumbnail")
    key = row[0]
    if settings.storage_driver == "local":
        path = (pathlib.Path(settings.storage_local_dir) / key).resolve()
        if not path.is_file():
            raise HTTPException(404, "no thumbnail")
        return FileResponse(
            path, media_type="image/jpeg",
            headers={"Cache-Control": "public, max-age=3600"},
        )
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="cand-")) / "thumb.jpg"
    storage.get_file(key, str(tmp))
    return FileResponse(
        tmp, media_type="image/jpeg",
        background=BackgroundTask(shutil.rmtree, tmp.parent),
    )


@router.get("/studio/recordings")
def recordings(request: Request):
    """The admin's recent studio sessions, newest first."""
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, filename, duration_seconds, width, height FROM studio_recordings "
                "WHERE user_id = %s ORDER BY created_at DESC LIMIT 20",
                (user["id"],),
            )
            rows = cur.fetchall()
    return {
        "items": [
            {
                "id": str(r[0]),
                "filename": r[1],
                "duration_seconds": r[2],
                "width": r[3],
                "height": r[4],
            }
            for r in rows
        ]
    }


@router.get("/studio/recordings/{recording_id}/file")
def recording_file(request: Request, recording_id: str):
    with db.session() as conn:
        with conn.cursor() as cur:
            row = _owned_recording(cur, request, recording_id)
            key = row[3]
    tmp = pathlib.Path(tempfile.mkdtemp(prefix="studio-play-")) / "recording.mp4"
    storage.get_file(key, str(tmp))
    from fastapi.responses import FileResponse

    return FileResponse(
        tmp, media_type="video/mp4",
        background=BackgroundTask(shutil.rmtree, tmp.parent),
    )


@router.get("/studio/recordings/{recording_id}")
def recording_detail(request: Request, recording_id: str):
    with db.session() as conn:
        with conn.cursor() as cur:
            row = _owned_recording(cur, request, recording_id)
            cur.execute(
                "SELECT id, start_seconds, end_seconds, score, reasons, state, "
                "template_id, clip_id, source, thumb_key FROM studio_candidates "
                "WHERE recording_id = %s ORDER BY score DESC",
                (recording_id,),
            )
            candidates = [
                {
                    "id": str(r[0]),
                    "start": r[1],
                    "end": r[2],
                    "score": r[3],
                    "reasons": r[4],
                    "state": r[5],
                    "template_id": r[6],
                    "clip_id": str(r[7]) if r[7] else None,
                    "source": r[8] or "audio",
                    "thumb_url": f"/studio/candidates/{r[0]}/thumb" if r[9] else None,
                }
                for r in cur.fetchall()
            ]
            cur.execute(
                "SELECT kind, state, stage FROM jobs "
                "WHERE payload->>'recording_id' = %s AND state IN ('queued', 'running') "
                "ORDER BY updated_at DESC LIMIT 1",
                (recording_id,),
            )
            active = cur.fetchone()
    return {
        "recording": {
            "id": str(row[0]),
            "filename": row[2],
            "duration_seconds": row[4],
            "width": row[5],
            "height": row[6],
        },
        "compute": {
            "whisper_device": row[7],
            "whisper_compute_type": row[8],
            "encoder": row[9],
            "gpu": row[7] in ("cuda", "mlx"),
        },
        "vision": {
            "model": row[10],
            "seconds_added": row[11],
        },
        "job": (
            {"kind": active[0], "state": active[1], "stage": active[2]} if active else None
        ),
        "candidates": candidates,
    }


@router.post("/studio/generate")
def generate(request: Request, payload: dict):
    user = current_user(request)
    windows = payload.get("windows") or []
    if not windows:
        raise HTTPException(422, "no windows")
    with db.session() as conn:
        with conn.cursor() as cur:
            row = _owned_recording(cur, request, payload["recording_id"])
            recording_id, key = str(row[0]), row[3]
            mission_id = payload.get("mission_id")
            if not mission_id:
                cur.execute(
                    "SELECT id FROM missions WHERE status = 'unverified' "
                    "ORDER BY created_at LIMIT 1"
                )
                found = cur.fetchone()
                mission_id = found[0] if found else None
            if not mission_id:
                raise HTTPException(422, "no mission available")
            items = [
                {
                    "mission_id": mission_id,
                    "start": float(w["start"]),
                    "end": float(w["end"]),
                    "result": "",
                    "template_id": w.get("template_id"),
                }
                for w in windows
            ]
            _stream_id, created = _create_clips(cur, user, key, items)
            for w, clip_id in zip(windows, created):
                if w.get("candidate_id"):
                    cur.execute(
                        "UPDATE studio_candidates SET state = 'accepted', "
                        "clip_id = %s, template_id = %s WHERE id = %s",
                        (clip_id, w.get("template_id"), w["candidate_id"]),
                    )
    return {"clips": created, "count": len(created)}


@router.get("/studio/templates")
def templates(request: Request):
    path = pathlib.Path(__file__).resolve().parent / "clip_templates.json"
    return json.loads(path.read_text())


@router.get("/studio/system")
def system_load(request: Request):
    """Real CPU, memory and GPU load, never a fake gauge."""
    cpu = _cpu_percent()
    mem = _mem_percent()
    gpu = _gpu_load()
    return {"cpu_percent": cpu, "memory_percent": mem, "gpu": gpu}


def _cpu_percent() -> float:
    def read():
        with open("/proc/stat") as fh:
            parts = fh.readline().split()[1:]
        vals = [int(p) for p in parts]
        idle = vals[3]
        return idle, sum(vals)

    try:
        i1, t1 = read()
        time.sleep(0.2)
        i2, t2 = read()
        if t2 == t1:
            return 0.0
        return round(100.0 * (1.0 - (i2 - i1) / (t2 - t1)), 1)
    except Exception:
        return 0.0


def _mem_percent() -> float:
    try:
        info = {}
        with open("/proc/meminfo") as fh:
            for line in fh:
                key, _, rest = line.partition(":")
                info[key] = int(rest.strip().split()[0])
        total = info.get("MemTotal", 0)
        avail = info.get("MemAvailable", 0)
        if not total:
            return 0.0
        return round(100.0 * (total - avail) / total, 1)
    except Exception:
        return 0.0


def _gpu_load() -> dict | None:
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=utilization.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if out.returncode != 0:
            return None
        util, used, total = [v.strip() for v in out.stdout.strip().split(",")]
        return {"utilization_percent": float(util), "memory_used_mb": float(used),
                "memory_total_mb": float(total)}
    except Exception:
        return None
