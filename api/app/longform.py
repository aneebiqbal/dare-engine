"""Long-form builder: assemble a session's clips into one video.

The worker concatenates the finished Shorts (all rendered by the same engine,
so the concat is a stream copy) and stores one file. The admin picks the clips
and the title; the build runs in the background like any other job.
"""
from __future__ import annotations

import json
import pathlib
import shutil
import tempfile

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask

from . import db, storage
from .users import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


@router.get("/admin/clips")
def admin_clips(request: Request):
    """Every finished clip, so the admin can assemble a long-form video."""
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT c.id, c.title, c.state, c.duration_seconds, c.created_at "
                "FROM clips c WHERE c.state IN ('ready','approved','posted') "
                "AND c.file_key IS NOT NULL ORDER BY c.created_at DESC LIMIT 200"
            )
            rows = cur.fetchall()
    return {
        "items": [
            {
                "id": str(r[0]),
                "title": r[1],
                "state": r[2],
                "duration_seconds": r[3],
                "created_at": r[4].isoformat(),
            }
            for r in rows
        ]
    }


@router.post("/admin/long-form")
def create(request: Request, payload: dict):
    title = (payload.get("title") or "").strip()
    clip_ids = [str(c) for c in (payload.get("clip_ids") or [])]
    if not title:
        raise HTTPException(422, "title required")
    if not clip_ids:
        raise HTTPException(422, "clip_ids required")
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT c.id FROM clips c JOIN assignments a ON a.id = c.assignment_id "
                "WHERE c.id = ANY(%s) AND c.state IN ('ready','approved','posted') "
                "AND c.file_key IS NOT NULL",
                (clip_ids,),
            )
            found = [str(r[0]) for r in cur.fetchall()]
            if not found:
                raise HTTPException(404, "no renderable clips")
            cur.execute(
                "INSERT INTO long_forms (title, clip_ids) VALUES (%s, %s) RETURNING id",
                (title, json.dumps(found)),
            )
            lf_id = str(cur.fetchone()[0])
            cur.execute(
                "INSERT INTO jobs (kind, payload, idempotency_key) "
                "VALUES ('build_long_form', %s, %s) ON CONFLICT (idempotency_key) DO NOTHING",
                (json.dumps({"long_form_id": lf_id}), f"longform:{lf_id}"),
            )
    return {"id": lf_id, "state": "queued"}


@router.get("/admin/long-form")
def list_long_forms(request: Request):
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, state, clip_ids, error, created_at "
                "FROM long_forms ORDER BY created_at DESC LIMIT 50"
            )
            rows = cur.fetchall()
    return {
        "items": [
            {
                "id": str(r[0]),
                "title": r[1],
                "state": r[2],
                "clip_ids": r[3],
                "error": r[4],
                "created_at": r[5].isoformat(),
            }
            for r in rows
        ]
    }


@router.get("/admin/long-form/{lf_id}")
def detail(request: Request, lf_id: str):
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title, state, clip_ids, error, file_key FROM long_forms WHERE id = %s",
                (lf_id,),
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(404, "not found")
    return {
        "id": str(row[0]),
        "title": row[1],
        "state": row[2],
        "clip_ids": row[3],
        "error": row[4],
        "download_url": f"/admin/long-form/{row[0]}/download" if row[5] else None,
    }


@router.get("/admin/long-form/{lf_id}/download")
def download(request: Request, lf_id: str):
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT file_key FROM long_forms WHERE id = %s", (lf_id,))
            row = cur.fetchone()
    if not row or not row[0]:
        raise HTTPException(404, "no file yet")
    tmp = pathlib.Path(tempfile.mkdtemp()) / "long-form.mp4"
    storage.get_file(row[0], str(tmp))
    return FileResponse(
        tmp, media_type="video/mp4", filename=f"{lf_id}.mp4",
        background=BackgroundTask(shutil.rmtree, tmp.parent),
    )
