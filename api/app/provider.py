"""Provider picker: choose the AI provider/model and the transcription engine.

The environment stays the source of truth; a stored choice overrides it at
runtime and is honoured by both the API and the worker.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from .config import settings
from .keys import resolve
from .settings_store import get, set
from .users import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])

KEYS = ("llm_provider", "llm_model", "llm_base_url", "asr")


@router.get("/admin/provider")
def provider(request: Request):
    stored = {k: get(k) for k in KEYS}
    asr = stored.get("asr") or ("mlx" if settings.mlx_whisper_url else "cpu")
    provider = stored.get("llm_provider") or settings.llm_provider
    base_url = stored.get("llm_base_url") or settings.llm_base_url
    model = stored.get("llm_model") or settings.llm_model
    return {
        "env": {
            "llm_provider": settings.llm_provider,
            "llm_model": settings.llm_model,
            "llm_base_url": settings.llm_base_url,
            "configured": settings.ai_configured,
        },
        "stored": stored,
        "effective": {
            "llm_provider": provider,
            "llm_model": model,
            "llm_base_url": base_url,
            "asr": asr,
            "configured": bool(provider == "openai" and base_url and model and resolve("llm")),
        },
    }


@router.post("/admin/provider")
def save(request: Request, payload: dict):
    for key in KEYS:
        if key in payload and payload[key] is not None:
            set(key, str(payload[key]))
    return {"ok": True}
