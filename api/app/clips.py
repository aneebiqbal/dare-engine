"""Marks, uploads, clips, trim, voice-over and export packages."""
from __future__ import annotations

import datetime
import json
import pathlib
import shutil
import tempfile
import uuid

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from starlette.background import BackgroundTask

from . import db, storage
from .paging import envelope, order_clause, parse
from .users import current_user

router = APIRouter()

CLIP_SORT = {"created_at": "c.created_at", "title": "c.title", "state": "c.state"}
CHUNK_SIZE = 1024 * 1024


def _clip(row) -> dict:
    return {
        "id": str(row[0]),
        "assignment_id": str(row[1]) if row[1] else None,
        "file_key": row[2],
        "title": row[3],
        "state": row[4],
        "template": row[5],
        "duration_seconds": row[6],
        "stage": row[7],
        "progress": row[8],
        "error": row[9],
        "layout": row[10],
        "caption_style": row[11],
        "voice_over": row[12],
        "voice": row[13],
        "export_title": row[14],
        "export_description": row[15],
        "export_tags": row[16],
        "transcript": row[17],
        "download_url": f"/clips/{row[0]}/download" if row[2] else None,
        "thumb_url": f"/clips/{row[0]}/thumbnail" if row[2] else None,
    }


_SELECT = (
    "SELECT c.id, c.assignment_id, c.file_key, c.title, c.state, c.template, "
    "c.duration_seconds, c.stage, c.progress, c.error, c.layout, c.caption_style, "
    "c.voice_over, c.voice, c.export_title, c.export_description, c.export_tags, "
    "c.transcript "
    "FROM clips c"
)


def _owned_clip(cur, request, clip_id):
    user = current_user(request)
    cur.execute(
        "SELECT c.id FROM clips c JOIN assignments a ON a.id = c.assignment_id "
        "WHERE c.id = %s AND a.user_id = %s",
        (clip_id, user["id"]),
    )
    if cur.fetchone() is None:
        raise HTTPException(404, "clip not found")


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


# --------------------------------------------------------------------- uploads


def _upload_dir(upload_id: str) -> pathlib.Path:
    from .config import settings

    path = pathlib.Path(settings.upload_tmp_dir) / upload_id
    path.mkdir(parents=True, exist_ok=True)
    return path


@router.post("/uploads/start")
def upload_start(request: Request, payload: dict):
    current_user(request)
    upload_id = uuid.uuid4().hex
    _upload_dir(upload_id)
    return {"upload_id": upload_id, "chunk_size": CHUNK_SIZE}


@router.get("/uploads/{upload_id}")
def upload_status(request: Request, upload_id: str):
    current_user(request)
    directory = _upload_dir(upload_id)
    parts = sorted(
        (int(p.stem) for p in directory.glob("*.part")),
        key=lambda n: (n == -1, n),
    )
    return {"upload_id": upload_id, "received": parts}


@router.put("/uploads/{upload_id}/chunks/{index}")
async def upload_chunk(upload_id: str, index: int, request: Request):
    current_user(request)
    body = await request.body()
    path = _upload_dir(upload_id) / f"{index}.part"
    path.write_bytes(body)
    return {"upload_id": upload_id, "index": index, "bytes": len(body)}


@router.post("/uploads/{upload_id}/complete")
def upload_complete(upload_id: str, request: Request, payload: dict):
    user = current_user(request)
    items = payload.get("marks")
    if not items:
        raise HTTPException(422, "marks must be a non-empty array")
    directory = _upload_dir(upload_id)
    parts = sorted(directory.glob("*.part"), key=lambda p: int(p.stem))
    if not parts:
        raise HTTPException(422, "no chunks uploaded")
    filename = payload.get("filename") or "recording.mp4"
    suffix = pathlib.Path(filename).suffix or ".mp4"
    assembled = directory / f"assembled{suffix}"
    with open(assembled, "wb") as out:
        for part in parts:
            out.write(part.read_bytes())
    try:
        return _finalize_upload(user, filename, assembled, items, upload_id)
    finally:
        shutil.rmtree(directory, ignore_errors=True)


@router.post("/uploads")
async def upload(request: Request, file: UploadFile = File(...), marks: str = Form(...)):
    """Single-request upload. The web app uses the chunked route above."""
    user = current_user(request)
    try:
        items = json.loads(marks)
    except json.JSONDecodeError:
        raise HTTPException(422, "marks must be a JSON array")
    if not items:
        raise HTTPException(422, "no marks supplied")
    suffix = pathlib.Path(file.filename or "recording.mp4").suffix or ".mp4"
    with tempfile.TemporaryDirectory(prefix="upload-") as tmp:
        local = pathlib.Path(tmp) / f"recording{suffix}"
        # Stream to disk in chunks; never hold the whole file in memory.
        with open(local, "wb") as out:
            while chunk := await file.read(CHUNK_SIZE):
                out.write(chunk)
        return _finalize_upload(
            user, file.filename or "recording.mp4", local, items, uuid.uuid4().hex
        )


def _create_clips(cur, user, key, items):
    """One stream, one assignment/mark pair, clip and render job per window."""
    today = datetime.date.today()
    created = []
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
            "INSERT INTO clips (assignment_id, state, stage, recording_key, "
            "source_start, source_end) VALUES (%s, 'queued', 'queued', %s, %s, %s) "
            "RETURNING id",
            (assignment_id, key, float(item["start"]), float(item["end"])),
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
        cur.execute("SELECT card FROM missions WHERE id = %s", (mission_id,))
        card = cur.fetchone()[0]
        _enqueue_render(
            cur,
            clip_id=str(clip_id),
            assignment_id=str(assignment_id),
            card=card,
            start=float(item["start"]),
            end=float(item["end"]),
            result=item.get("result", ""),
            recording_key=key,
            template_id=item.get("template_id"),
        )
        created.append(str(clip_id))
    return str(stream_id), created


def _finalize_upload(user, filename: str, local: pathlib.Path, items: list, upload_id: str) -> dict:
    if user is None:
        raise HTTPException(401, "not signed in")
    key = f"recordings/{user['id']}/{upload_id}{pathlib.Path(filename).suffix or '.mp4'}"
    storage.put_file(key, str(local))
    with db.session() as conn:
        with conn.cursor() as cur:
            stream_id, created = _create_clips(cur, user, key, items)
    return {"stream_id": stream_id, "clips": created, "count": len(created)}


# ---------------------------------------------------------------------- clips


@router.get("/clips")
def clips(request: Request):
    user = current_user(request)
    page, size, sort, order = parse(request, "created_at")
    state = request.query_params.get("state")
    with db.session() as conn:
        with conn.cursor() as cur:
            where = "a.user_id = %s"
            params: list = [user["id"]]
            if state:
                where += " AND c.state = %s"
                params.append(state)
            cur.execute(f"SELECT count(*) FROM clips c JOIN assignments a ON a.id = c.assignment_id WHERE {where}", params)
            total = cur.fetchone()[0]
            cur.execute(
                _SELECT + f" JOIN assignments a ON a.id = c.assignment_id WHERE {where} "
                f"ORDER BY {order_clause(sort, CLIP_SORT, 'c.created_at', order)} "
                f"LIMIT %s OFFSET %s",
                params + [size, (page - 1) * size],
            )
            rows = cur.fetchall()
    return envelope([_clip(r) for r in rows], total, page, size)


@router.get("/clips/{clip_id}")
def clip_detail(request: Request, clip_id: str):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                _SELECT + " JOIN assignments a ON a.id = c.assignment_id "
                "WHERE c.id = %s AND a.user_id = %s",
                (clip_id, user["id"]),
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(404, "clip not found")
    return _clip(row)


@router.patch("/clips/{clip_id}")
def update_clip(request: Request, clip_id: str, payload: dict):
    user = current_user(request)
    fields = {}
    for key in ("title", "layout", "caption_style", "voice_over", "voice", "export_title", "export_description", "export_tags"):
        if key in payload:
            fields[key] = payload[key]
    template_id = payload.get("template_id")
    if not fields and not template_id:
        raise HTTPException(422, "nothing to update")
    with db.session() as conn:
        with conn.cursor() as cur:
            _owned_clip(cur, request, clip_id)
            if fields:
                set_clause = ", ".join(f"{k} = %s" for k in fields)
                cur.execute(f"UPDATE clips SET {set_clause} WHERE id = %s", (*fields.values(), clip_id))
            # A template, layout or caption change re-renders in place.
            if template_id or "layout" in fields or "caption_style" in fields:
                cur.execute(
                    "SELECT c.recording_key, c.source_start, c.source_end, m.card, "
                    "c.trim_start, c.trim_end, c.voice_over, c.voice "
                    "FROM clips c JOIN assignments a ON a.id = c.assignment_id "
                    "JOIN missions m ON m.id = a.mission_id WHERE c.id = %s",
                    (clip_id,),
                )
                row = cur.fetchone()
                if row:
                    _enqueue_render(
                        cur,
                        clip_id=clip_id,
                        assignment_id=None,
                        card=row[3],
                        start=float(row[4] or row[1]),
                        end=float(row[5] or row[2]),
                        result="",
                        recording_key=row[0],
                        layout=fields.get("layout"),
                        caption_style=fields.get("caption_style"),
                        voice_over=bool(row[6]),
                        voice=row[7],
                        template_id=template_id,
                    )
    return {"id": clip_id, **fields}


@router.post("/clips/{clip_id}/trim")
def trim(request: Request, clip_id: str, payload: dict):
    user = current_user(request)
    start = float(payload.get("start", 0))
    end = float(payload.get("end", 0))
    if end <= start:
        raise HTTPException(422, "end must be after start")
    with db.session() as conn:
        with conn.cursor() as cur:
            _owned_clip(cur, request, clip_id)
            cur.execute(
                "SELECT c.recording_key, c.source_start, c.source_end, m.card, "
                "c.layout, c.caption_style, c.voice_over, c.voice "
                "FROM clips c JOIN assignments a ON a.id = c.assignment_id "
                "JOIN missions m ON m.id = a.mission_id WHERE c.id = %s",
                (clip_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(404, "clip not found")
            cur.execute(
                "UPDATE clips SET trim_start = %s, trim_end = %s WHERE id = %s",
                (start, end, clip_id),
            )
            _enqueue_render(
                cur,
                clip_id=clip_id,
                assignment_id=None,
                card=row[3],
                start=start,
                end=end,
                result="",
                recording_key=row[0],
                layout=row[4],
                caption_style=row[5],
                voice_over=bool(row[6]),
                voice=row[7],
                trim_start=start,
                trim_end=end,
            )
    return {"id": clip_id, "trim_start": start, "trim_end": end}


@router.post("/clips/{clip_id}/voice-over")
def voice_over(request: Request, clip_id: str, payload: dict):
    user = current_user(request)
    enabled = bool(payload.get("enabled", True))
    voice = payload.get("voice") or "en_US-amy-medium"
    with db.session() as conn:
        with conn.cursor() as cur:
            _owned_clip(cur, request, clip_id)
            cur.execute(
                "SELECT c.recording_key, c.source_start, c.source_end, m.card, "
                "c.layout, c.caption_style, c.trim_start, c.trim_end "
                "FROM clips c JOIN assignments a ON a.id = c.assignment_id "
                "JOIN missions m ON m.id = a.mission_id WHERE c.id = %s",
                (clip_id,),
            )
            row = cur.fetchone()
            if row is None:
                raise HTTPException(404, "clip not found")
            cur.execute(
                "UPDATE clips SET voice_over = %s, voice = %s WHERE id = %s",
                (enabled, voice if enabled else None, clip_id),
            )
            _enqueue_render(
                cur,
                clip_id=clip_id,
                assignment_id=None,
                card=row[3],
                start=float(row[6] or row[1]),
                end=float(row[7] or row[2]),
                result="",
                recording_key=row[0],
                layout=row[4],
                caption_style=row[5],
                voice_over=enabled,
                voice=voice if enabled else None,
                trim_start=row[6],
                trim_end=row[7],
            )
    return {"id": clip_id, "voice_over": enabled, "voice": voice if enabled else None}


@router.post("/clips/{clip_id}/voice-preview")
def voice_preview(request: Request, clip_id: str, payload: dict):
    user = current_user(request)
    voice = payload.get("voice") or "en_US-amy-medium"
    with db.session() as conn:
        with conn.cursor() as cur:
            _owned_clip(cur, request, clip_id)
            cur.execute("SELECT title FROM clips WHERE id = %s", (clip_id,))
            row = cur.fetchone()
            text = (row[0] if row and row[0] else "Clipdesk Missions")[:200]
            cur.execute(
                "INSERT INTO voice_overs (clip_id, voice, text, state) "
                "VALUES (%s, %s, %s, 'rendering') RETURNING id",
                (clip_id, voice, text),
            )
            preview_id = cur.fetchone()[0]
            cur.execute(
                "INSERT INTO jobs (kind, payload, idempotency_key) "
                "VALUES ('preview_voice', %s, %s)",
                (
                    json.dumps({"voice_over_id": str(preview_id), "voice": voice, "text": text}),
                    f"preview:{preview_id}",
                ),
            )
    return {"id": str(preview_id), "state": "rendering"}


@router.get("/voice-overs/{voice_over_id}")
def voice_over_status(request: Request, voice_over_id: str):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT v.id, v.state, v.audio_key, v.voice, v.text "
                "FROM voice_overs v JOIN clips c ON c.id = v.clip_id "
                "JOIN assignments a ON a.id = c.assignment_id "
                "WHERE v.id = %s AND a.user_id = %s",
                (voice_over_id, user["id"]),
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(404, "not found")
    return {
        "id": str(row[0]),
        "state": row[1],
        "voice": row[3],
        "text": row[4],
        "audio_url": f"/voice-overs/{row[0]}/audio" if row[2] else None,
    }


@router.get("/voice-overs/{voice_over_id}/audio")
def voice_over_audio(request: Request, voice_over_id: str):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT v.audio_key FROM voice_overs v JOIN clips c ON c.id = v.clip_id "
                "JOIN assignments a ON a.id = c.assignment_id "
                "WHERE v.id = %s AND a.user_id = %s",
                (voice_over_id, user["id"]),
            )
            row = cur.fetchone()
    if not row or not row[0]:
        raise HTTPException(404, "no audio")
    tmp = pathlib.Path(tempfile.mkdtemp()) / "preview.wav"
    storage.get_file(row[0], str(tmp))
    from fastapi.responses import FileResponse

    return FileResponse(
        tmp, media_type="audio/wav", filename="preview.wav",
        background=BackgroundTask(shutil.rmtree, tmp.parent),
    )


@router.post("/clips/{clip_id}/approve")
def approve(request: Request, clip_id: str):
    with db.session() as conn:
        with conn.cursor() as cur:
            _owned_clip(cur, request, clip_id)
            cur.execute("UPDATE clips SET state = 'approved' WHERE id = %s", (clip_id,))
    return {"id": clip_id, "state": "approved"}


@router.post("/clips/{clip_id}/post")
def post(request: Request, clip_id: str):
    # Publishing to YouTube is not in this sprint (see docs/SPRINT6_PROMPT.md).
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

    return FileResponse(
        tmp, media_type="video/mp4", filename=f"{clip_id}.mp4",
        background=BackgroundTask(shutil.rmtree, tmp.parent),
    )


@router.get("/clips/{clip_id}/thumbnail")
def thumbnail(request: Request, clip_id: str):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            _owned_clip(cur, request, clip_id)
    key = f"clips/{clip_id}/thumb.jpg"
    if not storage.exists(key):
        raise HTTPException(404, "no thumbnail yet")
    tmp = pathlib.Path(tempfile.mkdtemp()) / "thumb.jpg"
    storage.get_file(key, str(tmp))
    from fastapi.responses import FileResponse

    return FileResponse(
        tmp, media_type="image/jpeg", filename=f"{clip_id}.jpg",
        background=BackgroundTask(shutil.rmtree, tmp.parent),
    )


@router.post("/clips/{clip_id}/export")
def create_export(request: Request, clip_id: str, payload: dict):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            _owned_clip(cur, request, clip_id)
            cur.execute(
                "SELECT title, export_title, export_description, export_tags, file_key "
                "FROM clips WHERE id = %s",
                (clip_id,),
            )
            row = cur.fetchone()
            if not row:
                raise HTTPException(404, "clip not found")
            title = payload.get("title") or row[1] or row[0] or "Untitled"
            description = payload.get("description") if "description" in payload else (row[2] or "")
            tags = payload.get("tags") if "tags" in payload else (row[3] or [])
            cur.execute(
                "UPDATE clips SET export_title = %s, export_description = %s, export_tags = %s "
                "WHERE id = %s",
                (title, description, json.dumps(tags), clip_id),
            )
            cur.execute(
                "INSERT INTO exports (clip_id, title, description, tags, video_key, thumb_key) "
                "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                (clip_id, title, description, json.dumps(tags), row[4], f"clips/{clip_id}/thumb.jpg"),
            )
            export_id = cur.fetchone()[0]
    return {"id": str(export_id), "clip_id": clip_id, "state": "ready"}


@router.get("/clips/{clip_id}/export")
def download_export(request: Request, clip_id: str):
    """Download the package: video, thumbnail, title, description and tags."""
    import zipfile

    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT c.file_key, c.export_title, c.export_description, c.export_tags "
                "FROM clips c JOIN assignments a ON a.id = c.assignment_id "
                "WHERE c.id = %s AND a.user_id = %s",
                (clip_id, user["id"]),
            )
            row = cur.fetchone()
    if not row or not row[0]:
        raise HTTPException(404, "no export")
    video_key, title, description, tags = row
    tmp = pathlib.Path(tempfile.mkdtemp())
    video = tmp / "short.mp4"
    storage.get_file(video_key, str(video))
    thumb = tmp / "thumb.jpg"
    if storage.exists(f"clips/{clip_id}/thumb.jpg"):
        storage.get_file(f"clips/{clip_id}/thumb.jpg", str(thumb))
    meta = {
        "title": title or "Untitled",
        "description": description or "",
        "tags": tags or [],
    }
    (tmp / "metadata.json").write_text(json.dumps(meta, indent=2))
    if thumb.exists():
        (tmp / "thumbnail.jpg").write_bytes(thumb.read_bytes())
    zip_path = tmp / "package.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(video, "short.mp4")
        if thumb.exists():
            zf.write(thumb, "thumbnail.jpg")
        zf.write(tmp / "metadata.json", "metadata.json")
    from fastapi.responses import FileResponse

    return FileResponse(
        zip_path, media_type="application/zip", filename=f"{clip_id}-package.zip",
        background=BackgroundTask(shutil.rmtree, tmp),
    )


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


def _enqueue_render(
    cur,
    clip_id: str,
    assignment_id: str | None,
    card: dict,
    start: float,
    end: float,
    result: str,
    recording_key: str | None = None,
    recording_dir: str | None = None,
    layout: str | None = None,
    caption_style: str | None = None,
    voice_over: bool = False,
    voice: str | None = None,
    trim_start: float | None = None,
    trim_end: float | None = None,
    template_id: str | None = None,
) -> None:
    key = f"render:{clip_id}:{start}:{end}:{layout}:{caption_style}:{voice_over}:{voice}"
    cur.execute(
        "INSERT INTO jobs (kind, payload, idempotency_key) VALUES ('render_clip', %s, %s) "
        "ON CONFLICT (idempotency_key) DO NOTHING",
        (
            json.dumps(
                {
                    "clip_id": clip_id,
                    "assignment_id": assignment_id,
                    "recording_key": recording_key,
                    "recording_dir": recording_dir,
                    "card": card,
                    "start": start,
                    "end": end,
                    "result": result,
                    "layout": layout,
                    "caption_style": caption_style,
                    "voice_over": voice_over,
                    "voice": voice,
                    "trim_start": trim_start,
                    "trim_end": trim_end,
                    "template_id": template_id,
                }
            ),
            key,
        ),
    )


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
        "INSERT INTO clips (assignment_id, state, stage) VALUES (%s, 'queued', 'queued') RETURNING id",
        (assignment_id,),
    )
    clip_id = cur.fetchone()[0]
    _enqueue_render(
        cur,
        clip_id=str(clip_id),
        assignment_id=str(assignment_id),
        card=card,
        start=float(payload["start"]),
        end=float(payload["end"]),
        result=payload.get("result", ""),
        recording_dir=f"/recordings/{prefix}",
    )


@router.get("/history")
def history(request: Request):
    user = current_user(request)
    page, size, sort, order = parse(request, "created_at")
    q = request.query_params.get("q", "").strip()
    where = "a.user_id = %s"
    params: list = [user["id"]]
    if q:
        where += " AND (a.mission_id ILIKE %s OR m.card->>'question' ILIKE %s)"
        params += [f"%{q}%", f"%{q}%"]
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                f"SELECT count(*) FROM assignments a JOIN missions m ON m.id = a.mission_id WHERE {where}",
                params,
            )
            total = cur.fetchone()[0]
            cur.execute(
                "SELECT a.mission_id, a.date, a.state, c.id, c.state, c.duration_seconds, "
                "(SELECT result_value FROM attempts WHERE clip_id = c.id LIMIT 1), "
                "m.card->>'question' "
                "FROM assignments a JOIN missions m ON m.id = a.mission_id "
                f"LEFT JOIN clips c ON c.assignment_id = a.id WHERE {where} "
                "ORDER BY a.created_at DESC LIMIT %s OFFSET %s",
                params + [size, (page - 1) * size],
            )
            return envelope(
                [
                    {
                        "mission_id": r[0],
                        "date": r[1].isoformat(),
                        "state": r[2],
                        "result_value": r[6],
                        "clip_id": str(r[3]) if r[3] else None,
                        "clip_state": r[4],
                        "duration_seconds": r[5],
                        "question": r[7],
                    }
                    for r in cur.fetchall()
                ],
                total,
                page,
                size,
            )
