"""MediaMTX hooks: stream-key auth, segment registration, connection status."""
from __future__ import annotations

import hashlib
import urllib.request

from fastapi import APIRouter, HTTPException, Request

from . import db

router = APIRouter()


def _creds(payload: dict) -> tuple[str | None, str | None]:
    user = payload.get("user")
    password = payload.get("pass")
    query = payload.get("query") or ""
    if query:
        from urllib.parse import parse_qs

        params = parse_qs(query)
        user = user or (params.get("user") or [None])[0]
        password = password or (params.get("pass") or [None])[0]
    return user, password


@router.post("/hooks/relay/auth")
def auth(payload: dict):
    """Allow a publish only when the stream key matches a real stream."""
    action = payload.get("action")
    if action not in (None, "publish", "read"):
        return {"ok": False}
    _user, password = _creds(payload)
    path = payload.get("path") or ""
    key = (password or path.rstrip("/").split("/")[-1] or "").strip()
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM streams WHERE stream_key_hash = %s",
                (hashlib.sha256(key.encode()).hexdigest(),),
            )
            row = cur.fetchone()
    if row is None:
        return {"ok": False}
    return {"ok": True}


@router.post("/hooks/relay/segment")
def segment(payload: dict):
    path = payload.get("path") or ""
    key = path.rstrip("/").split("/")[-1]
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id FROM streams WHERE stream_key_hash = %s",
                (hashlib.sha256(key.encode()).hexdigest(),),
            )
            row = cur.fetchone()
            if row is None:
                return {"ok": False}
            cur.execute(
                "INSERT INTO stream_segments (stream_id, path, duration) VALUES (%s, %s, %s)",
                (row[0], payload.get("segment"), float(payload.get("duration") or 0)),
            )
    return {"ok": True}


@router.get("/streams/{stream_id}/status")
def stream_status(request: Request, stream_id: str):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT storage_prefix FROM streams WHERE id = %s AND user_id = %s",
                (stream_id, user["id"]),
            )
            row = cur.fetchone()
    if row is None:
        raise HTTPException(404, "stream not found")
    try:
        with urllib.request.urlopen(
            "http://relay:9997/v3/paths/list", timeout=5
        ) as resp:
            paths = __import__("json").load(resp)
    except Exception:
        paths = {"items": []}
    active = [p.get("name") for p in paths.get("items", [])]
    return {"connected": bool(active), "paths": active}


from .users import current_user  # noqa: E402
