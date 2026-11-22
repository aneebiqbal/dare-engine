"""Rate limiting: a per-IP sliding window, stricter on auth and admin routes."""
import asyncio
import pathlib
import sys
import types

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "api"))

from app.ratelimit import SlidingWindow, RateLimitMiddleware  # noqa: E402


def test_allows_up_to_the_limit_then_denies():
    window = SlidingWindow(limit=3, window_seconds=60)
    assert window.allow("1.2.3.4", now=0) is True
    assert window.allow("1.2.3.4", now=1) is True
    assert window.allow("1.2.3.4", now=2) is True
    assert window.allow("1.2.3.4", now=3) is False


def test_window_slides_so_old_hits_stop_counting():
    window = SlidingWindow(limit=2, window_seconds=10)
    assert window.allow("ip", now=0) is True
    assert window.allow("ip", now=1) is True
    assert window.allow("ip", now=2) is False
    # Both hits are now older than the window.
    assert window.allow("ip", now=20) is True


def test_keys_are_independent():
    window = SlidingWindow(limit=1, window_seconds=60)
    assert window.allow("a", now=0) is True
    assert window.allow("b", now=0) is True
    assert window.allow("a", now=1) is False


def _request(path: str, ip: str = "9.9.9.9", forwarded: str | None = None):
    headers = {}
    if forwarded:
        headers["x-forwarded-for"] = forwarded
    return types.SimpleNamespace(
        url=types.SimpleNamespace(path=path),
        client=types.SimpleNamespace(host=ip),
        headers=headers,
    )


async def _ok(request):
    return types.SimpleNamespace(status_code=200)


def _denied(middleware, path, ip="9.9.9.9", forwarded=None, now=0.0):
    return asyncio.run(middleware.dispatch(_request(path, ip, forwarded), _ok))


def _middleware(limit=2, auth_limit=1, clock=lambda: 0.0):
    return RateLimitMiddleware(
        None, limit=limit, window_seconds=60, auth_limit=auth_limit, clock=clock
    )


def test_denies_over_the_limit_with_retry_after():
    middleware = _middleware()
    assert _denied(middleware, "/open", now=0).status_code == 200
    assert _denied(middleware, "/open", now=1).status_code == 200
    third = _denied(middleware, "/open", now=2)
    assert third.status_code == 429
    assert third.headers["retry-after"]


def test_healthcheck_is_never_throttled():
    middleware = _middleware()
    for i in range(10):
        assert _denied(middleware, "/healthz", now=i).status_code == 200


def test_auth_routes_have_a_stricter_budget():
    middleware = _middleware()
    assert _denied(middleware, "/auth/sign-in", now=0).status_code == 200
    assert _denied(middleware, "/auth/sign-in", now=1).status_code == 429


def test_admin_routes_have_a_stricter_budget():
    middleware = _middleware()
    assert _denied(middleware, "/admin/models", now=0).status_code == 200
    assert _denied(middleware, "/admin/models", now=1).status_code == 429


def test_forwarded_for_is_honoured_behind_a_proxy():
    middleware = _middleware(limit=1)
    assert _denied(middleware, "/open", ip="10.0.0.1", forwarded="8.8.8.8", now=0).status_code == 200
    assert _denied(middleware, "/open", ip="10.0.0.1", forwarded="8.8.8.8", now=1).status_code == 429
    # A different client IP is a different bucket.
    assert _denied(middleware, "/open", ip="10.0.0.1", forwarded="8.8.8.7", now=2).status_code == 200
