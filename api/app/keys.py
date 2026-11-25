"""Integration key management.

Keys are encrypted at rest and never returned in full. The admin can paste a
key, test it against the real provider, and see the last result. Research and
the AI client read `resolve()` first and fall back to the environment only when
no stored key exists.
"""
from __future__ import annotations

import base64
import json
import urllib.error
import urllib.parse
import urllib.request

from fastapi import APIRouter, Depends, HTTPException, Request

from key_crypto import decrypt, encrypt, mask

from . import db
from .config import settings
from .settings_store import get as stored
from .users import audit, current_user, require_admin

router = APIRouter(dependencies=[Depends(require_admin)])

# name -> (label, environment fallback, docs, group)
INTEGRATIONS: dict[str, dict[str, str]] = {
    "youtube": {
        "label": "YouTube Data API",
        "env": "youtube_api_key",
        "docs": "https://console.cloud.google.com/apis/credentials",
        "group": "Research sources",
    },
    "reddit_client": {
        "label": "Reddit client ID",
        "env": "reddit_client_id",
        "docs": "https://www.reddit.com/prefs/apps",
        "group": "Research sources",
    },
    "reddit_secret": {
        "label": "Reddit client secret",
        "env": "reddit_client_secret",
        "docs": "https://www.reddit.com/prefs/apps",
        "group": "Research sources",
    },
    "rawg": {
        "label": "RAWG game database",
        "env": "rawg_api_key",
        "docs": "https://rawg.io/apidocs",
        "group": "Research sources",
    },
    "llm": {
        "label": "AI provider key",
        "env": "llm_api_key",
        "docs": "https://opencode.ai/zen",
        "group": "AI",
    },
}

RESEARCH_KEYS = ("youtube", "reddit_client", "reddit_secret")


# --- storage ---------------------------------------------------------------

def _row(name: str):
    try:
        with db.session() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT value_encrypted, status, status_detail, tested_at "
                    "FROM integration_keys WHERE name = %s",
                    (name,),
                )
                return cur.fetchone()
    except Exception:
        # A missing table (pre-migration) or a dropped connection reads as no
        # stored key; the environment fallback still works.
        return None


def _write_status(name: str, status: str, detail: str | None) -> None:
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO integration_keys "
                "(name, value_encrypted, status, status_detail, tested_at, updated_at) "
                "VALUES (%s, NULL, %s, %s, now(), now()) "
                "ON CONFLICT (name) DO UPDATE SET "
                "status = EXCLUDED.status, status_detail = EXCLUDED.status_detail, "
                "tested_at = EXCLUDED.tested_at, updated_at = now()",
                (name, status, detail),
            )


def resolve(name: str) -> str:
    """Stored key first, environment second. Never raises."""
    spec = INTEGRATIONS.get(name)
    if spec is None:
        return ""
    row = _row(name)
    if row and row[0]:
        value = decrypt(settings.session_secret, row[0])
        if value:
            return value
    return getattr(settings, spec["env"], "") or ""


def research_sources_configured() -> bool:
    return bool(resolve("youtube") or (resolve("reddit_client") and resolve("reddit_secret")))


def status_list() -> dict:
    integrations = []
    for name, spec in INTEGRATIONS.items():
        row = _row(name)
        env_value = getattr(settings, spec["env"], "") or ""
        stored_value = bool(row and row[0])
        value = decrypt(settings.session_secret, row[0]) if stored_value else env_value
        integrations.append({
            "name": name,
            "label": spec["label"],
            "group": spec["group"],
            "docs": spec["docs"],
            "env_var": spec["env"],
            "masked": mask(value),
            "configured": bool(value),
            "source": "stored" if stored_value else ("env" if env_value else "none"),
            "status": (row[1] if row else None) or "untested",
            "status_detail": row[2] if row else None,
            "tested_at": row[3].isoformat() if row and row[3] else None,
        })
    return {
        "integrations": integrations,
        "research_sources_configured": research_sources_configured(),
    }


# --- tests -----------------------------------------------------------------

def _status_from_http(url: str, headers: dict | None = None):
    try:
        req = urllib.request.Request(url, headers=headers or {})
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status, ""
    except urllib.error.HTTPError as exc:
        return exc.code, ""
    except Exception as exc:  #URLError, timeout, TLS
        return None, type(exc).__name__


def _test_youtube(key: str) -> tuple[str, str]:
    url = "https://www.googleapis.com/youtube/v3/search?" + urllib.parse.urlencode({
        "part": "snippet", "maxResults": "1", "q": "gaming", "type": "video", "key": key,
    })
    code, err = _status_from_http(url)
    if code == 200:
        return "connected", "YouTube Data API v3 accepted the key."
    if code in (400, 403):
        return "invalid", f"YouTube rejected the key (HTTP {code})."
    if code is None:
        return "unreachable", f"Could not reach YouTube ({err})."
    return "unreachable", f"YouTube returned HTTP {code}."


def _test_reddit(client_id: str, secret: str) -> tuple[str, str]:
    if not (client_id and secret):
        return "invalid", "Both the Reddit client ID and secret are required."
    basic = base64.b64encode(f"{client_id}:{secret}".encode()).decode()
    req = urllib.request.Request(
        "https://www.reddit.com/api/v1/access_token",
        data=urllib.parse.urlencode({"grant_type": "client_credentials"}).encode(),
        headers={
            "User-Agent": settings.reddit_user_agent,
            "Authorization": f"Basic {basic}",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.load(resp)
        if data.get("access_token"):
            return "connected", "Reddit OAuth accepted the app."
        return "invalid", "Reddit returned no access token."
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            return "invalid", f"Reddit rejected the app (HTTP {exc.code})."
        return "unreachable", f"Reddit returned HTTP {exc.code}."
    except Exception as exc:
        return "unreachable", f"Could not reach Reddit ({type(exc).__name__})."


def _test_rawg(key: str) -> tuple[str, str]:
    url = "https://api.rawg.io/api/games?" + urllib.parse.urlencode({"key": key, "page_size": "1"})
    code, err = _status_from_http(url, {"User-Agent": settings.reddit_user_agent})
    if code == 200:
        return "connected", "RAWG accepted the key."
    if code in (401, 403):
        return "invalid", f"RAWG rejected the key (HTTP {code})."
    if code is None:
        return "unreachable", f"Could not reach RAWG ({err})."
    return "unreachable", f"RAWG returned HTTP {code}."


def _test_llm(key: str) -> tuple[str, str]:
    provider = (stored("llm_provider") or settings.llm_provider or "").lower()
    if provider != "openai":
        return "invalid", f"Provider is '{provider or 'unset'}'; choose OpenAI-compatible first."
    base_url = (stored("llm_base_url") or settings.llm_base_url or "").rstrip("/")
    model = stored("llm_model") or settings.llm_model
    if not (base_url and model):
        return "invalid", "Set the AI base URL and model first."
    body = {
        "model": model,
        "messages": [{"role": "user", "content": "Return JSON only."}],
        "temperature": 0,
        "response_format": {"type": "json_object"},
    }
    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
        return "connected", f"{model} answered a test call."
    except urllib.error.HTTPError as exc:
        if exc.code in (401, 403):
            return "invalid", f"The provider rejected the key (HTTP {exc.code})."
        return "unreachable", f"The provider returned HTTP {exc.code}."
    except Exception as exc:
        return "unreachable", f"Could not reach the provider ({type(exc).__name__})."


def run_test(name: str) -> tuple[str, str]:
    if name == "youtube":
        return _test_youtube(resolve("youtube"))
    if name in ("reddit_client", "reddit_secret"):
        status, detail = _test_reddit(resolve("reddit_client"), resolve("reddit_secret"))
        _write_status("reddit_client", status, detail)
        _write_status("reddit_secret", status, detail)
        return status, detail
    if name == "rawg":
        return _test_rawg(resolve("rawg"))
    if name == "llm":
        return _test_llm(resolve("llm"))
    raise HTTPException(404, "unknown integration")


# --- routes ----------------------------------------------------------------

@router.get("/admin/keys")
def list_keys():
    return status_list()


@router.post("/admin/keys")
def save_key(request: Request, payload: dict):
    user = current_user(request)
    name = payload.get("name")
    value = payload.get("value")
    if name not in INTEGRATIONS:
        raise HTTPException(404, "unknown integration")
    if not isinstance(value, str) or not value.strip():
        raise HTTPException(422, "value required")
    value = value.strip()
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO integration_keys "
                "(name, value_encrypted, status, status_detail, tested_at, updated_at) "
                "VALUES (%s, %s, 'untested', NULL, NULL, now()) "
                "ON CONFLICT (name) DO UPDATE SET "
                "value_encrypted = EXCLUDED.value_encrypted, status = 'untested', "
                "status_detail = NULL, tested_at = NULL, updated_at = now()",
                (name, encrypt(settings.session_secret, value)),
            )
    audit(user["id"], "key.save", "integration", name, {})
    return {"ok": True, "name": name, "masked": mask(value)}


@router.delete("/admin/keys/{name}")
def remove_key(request: Request, name: str):
    user = current_user(request)
    if name not in INTEGRATIONS:
        raise HTTPException(404, "unknown integration")
    with db.session() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE integration_keys SET value_encrypted = NULL, status = 'untested', "
                "status_detail = NULL, tested_at = NULL, updated_at = now() WHERE name = %s",
                (name,),
            )
    audit(user["id"], "key.remove", "integration", name, {})
    return {"ok": True}


@router.post("/admin/keys/test")
def test_key(request: Request, payload: dict):
    user = current_user(request)
    name = payload.get("name")
    if name not in INTEGRATIONS:
        raise HTTPException(404, "unknown integration")
    status, detail = run_test(name)
    if name not in ("reddit_client", "reddit_secret"):
        _write_status(name, status, detail)
    audit(user["id"], "key.test", "integration", name, {"status": status})
    return {"ok": status == "connected", "status": status, "detail": detail}
