"""Marks, the local upload path and real clips."""
from __future__ import annotations

import datetime
import json
import pathlib
import tempfile
import uuid

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile

from . import db, storage
from .users import current_user

router = APIRouter()


def _clip(row) -> dict:
    return {
        "id": str(row[0]),
        "assignment_id": str(row[1]) if row[1] else None,
        "file_key": row[2],
        "title": row[3],
        "state": row[4],
        "template": row[5],
        "duration_seconds": row[6],
        "download_url": f"/clips/{row[0]}/download" if row[2] else None,
    }


@router.post("/marks")
def mark(request: Request, payload: dict):
    user = current_user(request)
    assignment_id = payload.get("assignment_id")
    kind = payload.get("kind")
    if kind not in ("start", "done"):
        raise HTTPException(422, "kind must be start or done")
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM assignments WHERE id = %s AND user_id = %s",
                (assignment_id, user["id"]),
            )
            if cur.fetchone() is None:
                raise HTTPException(404, "assignment not found")
            stream_time = payload.get("stream_time")
            if stream_time is None:
                stream_time = 0.0
            cur.execute(
                "INSERT INTO marks (assignment_id, kind, stream_time, result) "
                "VALUES (%s, %s, %s, %s) RETURNING id, stream_time",
                (assignment_id, kind, float(stream_time), payload.get("result")),
            )
            row = cur.fetchone()
            if kind == "done":
                cur.execute(
                    "SELECT stream_time FROM marks WHERE assignment_id = %s AND kind = 'start' "
                    "ORDER BY stream_time DESC LIMIT 1",
                    (assignment_id,),
                )
                start_row = cur.fetchone()
                start = start_row[0] if start_row else max(0.0, float(stream_time) - 30.0)
                _enqueue_relay_clip(
                    cur,
                    user["id"],
                    assignment_id,
                    {"start": start, "end": float(stream_time), "result": payload.get("result")},
                )
    return {"id": str(row[0]), "assignment_id": assignment_id, "kind": kind, "stream_time": row[1]}


@router.post("/uploads")
async def upload(request: Request, file: UploadFile = File(...), marks: str = Form(...)):
    """Local path: one recording plus its marks produces one clip job per mission."""
    user = current_user(request)
    try:
        items = json.loads(marks)
    except json.JSONDecodeError:
        raise HTTPException(422, "marks must be a JSON array")
    if not items:
        raise HTTPException(422, "no marks supplied")

    suffix = pathlib.Path(file.filename or "recording.mp4").suffix or ".mp4"
    with tempfile.TemporaryDirectory() as tmp:
        local = pathlib.Path(tmp) / f"recording{suffix}"
        local.write_bytes(await file.read())
        key = f"recordings/{user['id']}/{uuid.uuid4().hex}{suffix}"
        storage.put_file(key, str(local))

    today = datetime.date.today()
    created = []
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO streams (user_id, stream_key_hash, storage_prefix) "
                "VALUES (%s, %s, %s) RETURNING id",
                (user["id"], "local-upload", key),
            )
            stream_id = cur.fetchone()[0]
            for item in items:
                mission_id = item["mission_id"]
                cur.execute(
                    "INSERT INTO assignments (user_id, mission_id, date, state) "
                    "VALUES (%s, %s, %s, 'accepted') RETURNING id",
                    (user["id"], mission_id, today),
                )
                assignment_id = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO marks (assignment_id, stream_id, kind, stream_time) "
                    "VALUES (%s, %s, 'start', %s)",
                    (assignment_id, stream_id, float(item["start"])),
                )
                cur.execute(
                    "INSERT INTO marks (assignment_id, stream_id, kind, stream_time, result) "
                    "VALUES (%s, %s, 'done', %s, %s)",
                    (assignment_id, stream_id, float(item["end"]), item.get("result")),
                )
                cur.execute(
                    "INSERT INTO clips (assignment_id, state) VALUES (%s, 'rendering') RETURNING id",
                    (assignment_id,),
                )
                clip_id = cur.fetchone()[0]
                result = item.get("result")
                try:
                    result_value = float(result) if result not in (None, "", "pass", "fail") else None
                except ValueError:
                    result_value = None
                cur.execute(
                    "INSERT INTO attempts (mission_id, user_id, result_value, clip_id) "
                    "VALUES (%s, %s, %s, %s)",
                    (mission_id, user["id"], result_value, clip_id),
                )
                cur.execute(
                    "SELECT card FROM missions WHERE id = %s", (mission_id,)
                )
                card = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO jobs (kind, payload) VALUES ('render_clip', %s)",
                    (
                        json.dumps(
                            {
                                "clip_id": str(clip_id),
                                "assignment_id": str(assignment_id),
                                "recording_key": key,
                                "card": card,
                                "start": float(item["start"]),
                                "end": float(item["end"]),
                                "result": item.get("result", ""),
                            }
                        ),
                    ),
                )
                created.append(str(clip_id))
    return {"stream_id": str(stream_id), "clips": created, "count": len(created)}


@router.get("/clips")
def clips(request: Request):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT c.id, c.assignment_id, c.file_key, c.title, c.state, "
                "c.template, c.duration_seconds "
                "FROM clips c JOIN assignments a ON a.id = c.assignment_id "
                "WHERE a.user_id = %s ORDER BY c.created_at DESC",
                (user["id"],),
            )
            return [_clip(r) for r in cur.fetchall()]


@router.patch("/clips/{clip_id}")
def retitle(request: Request, clip_id: str, payload: dict):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE clips c SET title = %s FROM assignments a "
                "WHERE c.id = %s AND c.assignment_id = a.id AND a.user_id = %s "
                "RETURNING c.id",
                (payload.get("title"), clip_id, user["id"]),
            )
            if cur.fetchone() is None:
                raise HTTPException(404, "clip not found")
    return {"id": clip_id, "title": payload.get("title")}


def _owned_clip(cur, request, clip_id):
    user = current_user(request)
    cur.execute(
        "SELECT c.id FROM clips c JOIN assignments a ON a.id = c.assignment_id "
        "WHERE c.id = %s AND a.user_id = %s",
        (clip_id, user["id"]),
    )
    if cur.fetchone() is None:
        raise HTTPException(404, "clip not found")


@router.post("/clips/{clip_id}/approve")
def approve(request: Request, clip_id: str):
    with db.session() as conn:
        with conn.cursor() as cur:
            _owned_clip(cur, request, clip_id)
            cur.execute("UPDATE clips SET state = 'approved' WHERE id = %s", (clip_id,))
    return {"id": clip_id, "state": "approved"}


@router.post("/clips/{clip_id}/post")
def post(request: Request, clip_id: str):
    # Publishing needs a YouTube channel (M6). Built, unproven.
    with db.session() as conn:
        with conn.cursor() as cur:
            _owned_clip(cur, request, clip_id)
            cur.execute("UPDATE clips SET state = 'posted' WHERE id = %s", (clip_id,))
    return {"id": clip_id, "state": "posted", "unproven": "youtube"}


@router.get("/clips/{clip_id}/download")
def download(request: Request, clip_id: str):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT c.file_key FROM clips c JOIN assignments a ON a.id = c.assignment_id "
                "WHERE c.id = %s AND a.user_id = %s",
                (clip_id, user["id"]),
            )
            row = cur.fetchone()
    if not row or not row[0]:
        raise HTTPException(404, "no file")
    tmp = pathlib.Path(tempfile.mkdtemp()) / "short.mp4"
    storage.get_file(row[0], str(tmp))
    from fastapi.responses import FileResponse

    return FileResponse(tmp, media_type="video/mp4", filename=f"{clip_id}.mp4")


@router.post("/streams")
def create_stream(request: Request, payload: dict):
    user = current_user(request)
    import hashlib
    import secrets

    key = secrets.token_urlsafe(24)
    rtmp_url = f"rtmp://localhost:1935/live/{key}"
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO streams (user_id, stream_key_hash, storage_prefix) "
                "VALUES (%s, %s, %s) RETURNING id",
                (user["id"], hashlib.sha256(key.encode()).hexdigest(), f"live/{key}"),
            )
            stream_id = cur.fetchone()[0]
    return {"id": str(stream_id), "rtmp_url": rtmp_url, "stream_key": key}


def _enqueue_relay_clip(cur, user_id: str, assignment_id: str, payload: dict) -> None:
    """On Done, queue a render from the relay's recorded segments."""
    cur.execute(
        "SELECT id, storage_prefix FROM streams "
        "WHERE user_id = %s AND ended_at IS NULL ORDER BY started_at DESC LIMIT 1",
        (user_id,),
    )
    stream = cur.fetchone()
    if stream is None:
        return
    stream_id, prefix = stream
    cur.execute("SELECT mission_id FROM assignments WHERE id = %s", (assignment_id,))
    row = cur.fetchone()
    if row is None:
        return
    mission_id = row[0]
    cur.execute("SELECT card FROM missions WHERE id = %s", (mission_id,))
    card = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO clips (assignment_id, state) VALUES (%s, 'rendering') RETURNING id",
        (assignment_id,),
    )
    clip_id = cur.fetchone()[0]
    cur.execute(
        "INSERT INTO jobs (kind, payload) VALUES ('render_clip', %s)",
        (
            json.dumps(
                {
                    "clip_id": str(clip_id),
                    "assignment_id": str(assignment_id),
                    "recording_dir": f"/recordings/{prefix}",
                    "card": card,
                    "start": float(payload["start"]),
                    "end": float(payload["end"]),
                    "result": payload.get("result", ""),
                    "stream_id": str(stream_id),
                }
            ),
        ),
    )


@router.get("/history")
def history(request: Request):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT a.mission_id, a.date, a.state, c.id, c.state, c.duration_seconds "
                "FROM assignments a LEFT JOIN clips c ON c.assignment_id = a.id "
                "WHERE a.user_id = %s ORDER BY a.created_at DESC",
                (user["id"],),
            )
            return [
                {
                    "mission_id": r[0],
                    "date": r[1].isoformat(),
                    "state": r[2],
                    "result_value": None,
                    "clip_id": str(r[3]) if r[3] else None,
                }
                for r in cur.fetchall()
            ]

