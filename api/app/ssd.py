"""SSD import: list the videos on a mounted drive and import one locally.

The container cannot see /Volumes, so a host bridge (`local/ssd_bridge.py`) does
the listing and copies the chosen file into a shared inbox. The API then copies
it into its own local storage and registers a studio recording. Nothing is
uploaded anywhere.
"""
from __future__ import annotations

import json
import pathlib
import urllib.request
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request

from . import db, storage
from .config import settings
from .projects import create_for_recording
from .studio import _probe
from .users import current_user, require_admin

router = APIRouter(dependencies=[Depends(require_admin)])

HOW_TO = "Start the host bridge with `make ssd-bridge` and plug in the drive."


def _bridge(path: str, method: str = "GET", body: dict | None = None) -> dict:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    req = urllib.request.Request(settings.ssd_bridge_url + path, data=data, method=method, headers=headers)
    with urllib.request.urlopen(req, timeout=120) as resp:
        return json.load(resp)


@router.get("/studio/ssd")
def ssd_drives(request: Request):
    current_user(request)
    if not settings.ssd_bridge_url:
        return {"enabled": False, "reason": "SSD_BRIDGE_URL is not set", "how_to": HOW_TO}
    try:
        return {"enabled": True, **_bridge("/drives")}
    except Exception as exc:
        return {"enabled": True, "error": f"{type(exc).__name__}: {exc}", "how_to": HOW_TO}


@router.post("/studio/ssd/import")
def ssd_import(request: Request, payload: dict):
    user = current_user(request)
    path = payload.get("path")
    if not path:
        raise HTTPException(422, "path required")
    try:
        imported = _bridge("/import", "POST", {"path": path})
    except Exception as exc:
        raise HTTPException(502, f"the host bridge could not import that file: {exc}")

    filename = imported["filename"]
    local = pathlib.Path(settings.ssd_inbox_dir) / filename
    if not local.exists():
        raise HTTPException(502, "the imported file is not in the shared inbox")

    recording_id = str(uuid.uuid4())
    suffix = local.suffix or ".mp4"
    key = f"recordings/{user['id']}/studio-{recording_id}{suffix}"
    specs = _probe(str(local))
    storage.put_file(key, str(local))
    # Process-and-release: once the file is safely in local storage, drop the
    # inbox copy so a long session cannot fill the disk.
    release = bool(payload.get("release", True))
    if release:
        try:
            local.unlink()
        except OSError:
            pass
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO studio_recordings "
                "(id, user_id, filename, storage_key, duration_seconds, width, height) "
                "VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (
                    recording_id, user["id"], imported.get("name") or filename, key,
                    specs["duration_seconds"], specs["width"], specs["height"],
                ),
            )
            create_for_recording(
                cur, user["id"], recording_id, imported.get("name") or filename
            )
            # Importing starts the local processing job, not just a file copy.
            cur.execute(
                "INSERT INTO jobs (kind, payload, idempotency_key) "
                "VALUES ('detect_moments', %s, %s)",
                (
                    json.dumps({"recording_id": recording_id, "storage_key": key, "top_n": 5}),
                    f"detect:{recording_id}:{uuid.uuid4().hex}",
                ),
            )
    return {
        "recording_id": recording_id,
        "filename": imported.get("name") or filename,
        "source_path": path,
        "detect_queued": True,
        "released": release and not local.exists(),
        **specs,
    }
