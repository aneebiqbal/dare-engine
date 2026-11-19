"""The worker's AI client: the same shared OpenAI-compatible client as the API.

Returns None when no key is configured, so callers fall back to word density.
"""
from __future__ import annotations

from worker_app.config import settings


def _log_usage(**kw) -> None:
    """Best-effort usage logging; never let it break a render."""
    try:
        from worker_app import db

        with db.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO ai_usage (user_id, page, kind, provider, model, "
                    "prompt_tokens, completion_tokens, latency_ms, fallback) "
                    "VALUES (NULL, 'clips', %s, %s, %s, %s, %s, %s, %s)",
                    (
                        kw["kind"], kw["provider"], kw["model"],
                        kw["prompt_tokens"], kw["completion_tokens"],
                        kw["latency_ms"], kw["fallback"],
                    ),
                )
    except Exception:
        pass


def get_llm():
    from worker_app.settings_store import get as stored

    if (stored("llm_provider") or settings.llm_provider or "").lower() != "openai":
        return None
    if not settings.llm_api_key:
        return None
    from llm_shared import OpenAICompatibleLLM

    return OpenAICompatibleLLM(
        stored("llm_base_url") or settings.llm_base_url,
        settings.llm_api_key,
        stored("llm_model") or settings.llm_model,
        settings.llm_timeout,
        log_usage=_log_usage,
    )
