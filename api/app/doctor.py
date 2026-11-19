"""Environment and connection checks. Prints PASS/FAIL, never a value."""
from __future__ import annotations

import os
import shutil
import subprocess

from .config import settings


def _check(name: str, ok: bool, detail: str = "") -> dict:
    return {"name": name, "ok": bool(ok), "detail": detail}


def run_checks() -> list[dict]:
    checks = []

    checks.append(_check(
        "DATABASE_URL set",
        bool(settings.database_url),
        "pooled connection string",
    ))
    checks.append(_check(
        "DATABASE_URL_DIRECT set",
        bool(settings.database_url_direct),
        "direct connection string for migrations and the worker",
    ))

    from . import db

    try:
        db.check()
        checks.append(_check("pooled database connect", True))
    except Exception as exc:
        checks.append(_check("pooled database connect", False, type(exc).__name__))

    try:
        from contextlib import closing

        with closing(db.connect(direct=True)) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
                cur.fetchone()
        checks.append(_check("direct database connect", True))
    except Exception as exc:
        checks.append(_check("direct database connect", False, type(exc).__name__))

    checks.append(_check(
        "SESSION_SECRET changed",
        bool(settings.session_secret) and settings.session_secret != "change-me",
        "generate one locally: openssl rand -hex 32",
    ))
    checks.append(_check(
        "LLM_BASE_URL set",
        bool(settings.llm_base_url),
        "OpenAI-compatible base URL",
    ))
    checks.append(_check(
        "LLM_API_KEY present",
        bool(settings.llm_api_key),
        "never printed",
    ))
    checks.append(_check(
        "LLM_MODEL set",
        bool(settings.llm_model),
        "model id from the provider",
    ))
    research_keys = bool(
        settings.youtube_api_key
        or (settings.reddit_client_id and settings.reddit_client_secret)
        or settings.rawg_api_key
    )
    checks.append(_check(
        "research sources (optional)",
        True,
        "live keys present"
        if research_keys
        else "no source keys — the daily brain runs on the saved sample feed",
    ))

    from . import storage

    try:
        store = storage.get_storage()
        store.ensure_bucket()
        checks.append(_check(f"storage ({settings.storage_driver})", True))
    except Exception as exc:
        checks.append(_check(f"storage ({settings.storage_driver})", False, type(exc).__name__))

    # The worker owns TTS; ask its readiness endpoint.
    try:
        import json
        import urllib.request

        with urllib.request.urlopen("http://worker:8001/healthz/ready", timeout=5) as resp:
            worker = json.load(resp)
        checks.append(_check("worker reachable", True))
        # Voice-over is an optional, GPL-licensed add-on; not installed is not a
        # failure of the default build.
        checks.append(_check(
            "local TTS command (optional)",
            True,
            settings.tts_command if worker.get("tts") else f"{settings.tts_command} not installed — run `make voice`",
        ))
        voice_model = os.path.join(settings.tts_model_dir, f"{settings.tts_voice}.onnx")
        checks.append(_check(
            "voice model (optional)",
            True,
            voice_model if worker.get("voice_model") else f"{voice_model} not downloaded — run `make voice`",
        ))
    except Exception as exc:
        checks.append(_check("worker reachable", False, type(exc).__name__))
        checks.append(_check("local TTS command", False, "worker unreachable"))
        checks.append(_check("voice model present", False, "worker unreachable"))

    checks.append(_check("WEB_ORIGIN set", bool(settings.web_origin)))
    return checks


def main() -> None:
    checks = run_checks()
    failed = sum(1 for check in checks if not check["ok"])
    for check in checks:
        status = "PASS" if check["ok"] else "FAIL"
        suffix = f" — {check['detail']}" if check["detail"] else ""
        print(f"{status}  {check['name']}{suffix}")
    print(f"\n{len(checks) - failed}/{len(checks)} checks passed")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
