"""Serialize acceptance runs.

The suites share one database and several of them TRUNCATE shared tables, so two
concurrent runs invalidate each other. A file lock makes them take turns.
"""
from __future__ import annotations

import fcntl
import pathlib

import pytest

_LOCK_PATH = pathlib.Path("/tmp/clipdesk-accept.lock")
_lock_handle = None


def pytest_sessionstart(session):
    global _lock_handle
    _lock_handle = _LOCK_PATH.open("w")
    fcntl.flock(_lock_handle, fcntl.LOCK_EX)


def pytest_sessionfinish(session):
    global _lock_handle
    if _lock_handle is not None:
        fcntl.flock(_lock_handle, fcntl.LOCK_UN)
        _lock_handle.close()
        _lock_handle = None
