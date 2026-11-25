"""Per-IP rate limiting.

Login already counts failures per email and per IP; this adds a general ceiling
so one client cannot hold a worker or scrape the public pages. The budget is
deliberately small on `/auth/` and on mutating `/admin/` requests, where a
script does the most damage. Admin reads share the general budget because the
Models page polls them; the health check is never throttled (a load balancer
must be able to probe a busy container).

`X-Forwarded-For` is honoured because the app sits behind a proxy in
production; the first hop is the client address.
"""
from __future__ import annotations

import threading
import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class SlidingWindow:
    """A fixed-count sliding window per key. Pure, so it is unit-testable."""

    def __init__(self, limit: int, window_seconds: float):
        self.limit = limit
        self.window_seconds = window_seconds
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def allow(self, key: str, now: float | None = None) -> bool:
        now = time.time() if now is None else now
        with self._lock:
            hits = [t for t in self._hits.get(key, []) if now - t < self.window_seconds]
            if len(hits) >= self.limit:
                self._hits[key] = hits
                return False
            hits.append(now)
            self._hits[key] = hits
            return True


def client_ip(request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        limit: int = 60,
        window_seconds: float = 60,
        auth_limit: int = 10,
        clock=time.time,
    ):
        super().__init__(app)
        self.window_seconds = window_seconds
        self.general = SlidingWindow(limit, window_seconds)
        self.auth = SlidingWindow(auth_limit, window_seconds)
        self._clock = clock

    async def dispatch(self, request, call_next):
        path = request.url.path
        if path.startswith("/healthz"):
            return await call_next(request)
        key = client_ip(request)
        strict = path.startswith("/auth/") or (
            path.startswith("/admin/") and request.method != "GET"
        )
        allowed = (self.auth if strict else self.general).allow(key, self._clock())
        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": "too many requests; try again later",
                    "error": {"status": 429, "message": "too many requests"},
                },
                headers={"Retry-After": str(int(self.window_seconds))},
            )
        return await call_next(request)
