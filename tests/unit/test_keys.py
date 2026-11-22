"""Integration keys: masking, encryption and the live status mapping."""
import importlib.util
import pathlib
import sys
import urllib.error

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "api"))


def _load(name: str, path: pathlib.Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


key_crypto = _load("key_crypto", ROOT / "shared" / "key_crypto.py")
from app import keys  # noqa: E402


class _Resp:
    def __init__(self, status: int = 200):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def read(self):
        return b"{}"


def test_mask_never_returns_the_full_key():
    assert keys.mask("sk-abcdef4f2a") == "sk-...4f2a"
    assert keys.mask("abc") == "•••"
    assert keys.mask("") == ""


def test_encrypt_decrypt_roundtrip_and_fail_closed():
    token = key_crypto.encrypt("secret", "sk-abcdef4f2a")
    assert token != "sk-abcdef4f2a"
    assert key_crypto.decrypt("secret", token) == "sk-abcdef4f2a"
    assert key_crypto.decrypt("other-secret", token) == ""
    assert key_crypto.decrypt("secret", "not-a-token") == ""


def test_resolve_prefers_the_stored_key(monkeypatch):
    monkeypatch.setattr(keys, "_row", lambda name: ("token", "untested", None, None))
    monkeypatch.setattr(keys, "decrypt", lambda secret, token: "sk-stored")
    monkeypatch.setattr(keys.settings, "youtube_api_key", "env-key")
    assert keys.resolve("youtube") == "sk-stored"


def test_resolve_falls_back_to_the_environment(monkeypatch):
    monkeypatch.setattr(keys, "_row", lambda name: None)
    monkeypatch.setattr(keys.settings, "youtube_api_key", "env-key")
    assert keys.resolve("youtube") == "env-key"


def test_research_sources_configured(monkeypatch):
    monkeypatch.setattr(
        keys,
        "resolve",
        lambda name: {"youtube": "k", "reddit_client": "", "reddit_secret": ""}.get(name, ""),
    )
    assert keys.research_sources_configured() is True
    monkeypatch.setattr(keys, "resolve", lambda name: "")
    assert keys.research_sources_configured() is False


def test_youtube_status_mapping(monkeypatch):
    monkeypatch.setattr(keys.urllib.request, "urlopen", lambda *a, **k: _Resp(200))
    assert keys._test_youtube("k") == ("connected", "YouTube Data API v3 accepted the key.")

    def forbidden(*a, **k):
        raise urllib.error.HTTPError("u", 403, "Forbidden", {}, None)

    monkeypatch.setattr(keys.urllib.request, "urlopen", forbidden)
    status, detail = keys._test_youtube("k")
    assert status == "invalid" and "403" in detail

    def dns(*a, **k):
        raise OSError("dns")

    monkeypatch.setattr(keys.urllib.request, "urlopen", dns)
    assert keys._test_youtube("k")[0] == "unreachable"


def test_reddit_requires_both_parts(monkeypatch):
    assert keys._test_reddit("", "")[0] == "invalid"
