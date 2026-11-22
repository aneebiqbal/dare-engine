"""First-run setup wizard: four verified steps, progress persisted per user.

The wizard does not fake a check. Each step's Verify button calls the real
endpoint (SSD bridge, OBS WebSocket, model bridge, provider config) and only
then records `done`. A returning user sees completed steps and lands on the
first incomplete one.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from . import db
from .users import current_user, require_admin

router = APIRouter(dependencies=[Depends(require_admin)])

STEPS = [
    {
        "id": "ssd",
        "title": "Connect the SSD",
        "body": "Plug in the drive that holds your recordings. The app lists it and imports locally — nothing is uploaded.",
        "help": "Start the host bridge with `make ssd-bridge`, then plug in the drive. If it does not appear, check the cable and whether the drive is mounted.",
    },
    {
        "id": "obs",
        "title": "Connect OBS over the network",
        "body": "OBS can run on another machine on the same network. Enter its WebSocket address and password, then test the connection.",
        "help": "In OBS open Tools → WebSocket Server Settings, enable the server and set a password. Put the address and password in OBS_WS_URL and OBS_WS_PASSWORD in .env.",
    },
    {
        "id": "models",
        "title": "Install the local models",
        "body": "MLX Whisper for transcription, a writing model, and the Qwen vision model. Each shows its size, whether it fits this Mac, and a one-click install.",
        "help": "Start the host bridge with `make mlx-bridge`. Downloads can be interrupted and resumed; the model unloads when a job finishes.",
    },
    {
        "id": "cloud",
        "title": "Connect the cloud account and AI provider",
        "body": "Sign in, then choose a provider. With no key or no credit, the app runs on local models and says so.",
        "help": "Set LLM_PROVIDER, LLM_BASE_URL, LLM_API_KEY and LLM_MODEL in .env, or keep the local provider.",
    },
]

IDS = {s["id"] for s in STEPS}


def _steps(cur, user_id: str) -> list[dict]:
    cur.execute(
        "SELECT step, status, detail, updated_at FROM setup_steps WHERE user_id = %s",
        (user_id,),
    )
    saved = {r[0]: (r[1], r[2], r[3]) for r in cur.fetchall()}
    out = []
    for step in STEPS:
        status, detail, updated = saved.get(step["id"], ("pending", None, None))
        out.append({
            **step,
            "status": status,
            "detail": detail,
            "updated_at": updated.isoformat() if updated else None,
        })
    return out


@router.get("/admin/wizard")
def wizard(request: Request):
    user = current_user(request)
    with db.session() as conn:
        with conn.cursor() as cur:
            steps = _steps(cur, user["id"])
    ready = all(s["status"] == "done" for s in steps)
    next_step = next((s["id"] for s in steps if s["status"] != "done"), None)
    return {"steps": steps, "ready": ready, "next": next_step}


@router.post("/admin/wizard/{step}")
def save_step(request: Request, step: str, payload: dict):
    user = current_user(request)
    if step not in IDS:
        raise HTTPException(404, "unknown step")
    status = payload.get("status")
    if status not in ("pending", "done", "failed"):
        raise HTTPException(422, "status must be pending, done or failed")
    detail = payload.get("detail")
    if detail:
        detail = str(detail)[:500]
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO setup_steps (user_id, step, status, detail) "
                "VALUES (%s, %s, %s, %s) "
                "ON CONFLICT (user_id, step) DO UPDATE SET "
                "status = EXCLUDED.status, detail = EXCLUDED.detail, updated_at = now()",
                (user["id"], step, status, detail),
            )
            steps = _steps(cur, user["id"])
    ready = all(s["status"] == "done" for s in steps)
    next_step = next((s["id"] for s in steps if s["status"] != "done"), None)
    return {"steps": steps, "ready": ready, "next": next_step}
