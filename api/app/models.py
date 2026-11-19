"""Admin model manager: the real local engine, never a fake gauge.

The host bridge (`local/mlx_bridge.py`) owns Ollama and MLX. This router proxies
it so the Models page can show every local model, pull with progress, unload or
free all, and read live memory. When the bridge is down the page says so.
"""
from __future__ import annotations

import json
import urllib.request

from fastapi import APIRouter, Depends, HTTPException, Request

from .config import settings
from .users import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])
BRIDGE = settings.model_bridge_url.rstrip("/")


def _get(path: str, timeout: float = 10):
    try:
        with urllib.request.urlopen(BRIDGE + path, timeout=timeout) as resp:
            return json.loads(resp.read()), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


def _post(path: str, payload: dict, timeout: float = 60):
    req = urllib.request.Request(
        BRIDGE + path,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read()), None
    except Exception as exc:
        return None, f"{type(exc).__name__}: {exc}"


@router.get("/admin/models")
def models(request: Request):
    engine, error = _get("/models")
    return {
        "bridge": "up" if error is None else "down",
        "error": error,
        "provider": {
            "llm_provider": settings.llm_provider,
            "llm_model": settings.llm_model,
            "llm_base_url": settings.llm_base_url,
            "configured": settings.ai_configured,
            "asr": "mlx" if settings.mlx_whisper_url else "cpu",
            "mlx_model": settings.mlx_whisper_model,
        },
        "engine": engine,
    }


@router.post("/admin/models/pull")
def pull(request: Request, payload: dict):
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(422, "name required")
    task, error = _post("/models/pull", {"name": name})
    if error:
        raise HTTPException(502, error)
    return task


@router.get("/admin/models/pull/{task_id}")
def pull_status(request: Request, task_id: str):
    task, error = _get(f"/models/pull/{task_id}")
    if error:
        raise HTTPException(502, error)
    return task or {"error": "unknown task"}


@router.post("/admin/models/unload")
def unload(request: Request, payload: dict):
    name = (payload.get("name") or "").strip()
    result, error = _post("/models/unload", {"name": name})
    if error:
        raise HTTPException(502, error)
    return result


@router.post("/admin/models/free")
def free_all(request: Request):
    result, error = _post("/models/free", {})
    if error:
        raise HTTPException(502, error)
    return result
