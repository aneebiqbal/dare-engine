"""Encrypt-then-MAC for stored integration keys.

Fernet (AES-128-CBC + HMAC) with a key derived from SESSION_SECRET. The
plaintext never leaves the API and is never returned to the browser. Rotating
SESSION_SECRET invalidates stored keys; they must be re-entered.
"""
from __future__ import annotations

import base64
import hashlib

from cryptography.fernet import Fernet


def _fernet(secret: str) -> Fernet:
    digest = hashlib.sha256((secret or "").encode("utf-8")).digest()
    return Fernet(base64.urlsafe_b64encode(digest))


def encrypt(secret: str, value: str) -> str:
    return _fernet(secret).encrypt((value or "").encode("utf-8")).decode("ascii")


def decrypt(secret: str, token: str) -> str:
    """Fail closed: a missing or corrupted row reads as no key."""
    if not token:
        return ""
    try:
        return _fernet(secret).decrypt(token.encode("ascii")).decode("utf-8")
    except Exception:
        return ""


def mask(value: str) -> str:
    """Never show a full key. `sk-...4f2a` for anything long enough."""
    if not value:
        return ""
    if len(value) <= 7:
        return "•" * len(value)
    return f"{value[:3]}...{value[-4:]}"
