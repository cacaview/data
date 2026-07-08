"""Rate limiting middleware.

Lightweight in-process token-bucket rate limiter keyed by client IP.
No external dependency required. Uses a sliding window
counter to prevent bursts above the limit.

For multi-worker production deployments, swap the in-memory store
for Redis. The interface is designed for that swap.
"""

from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable

import structlog
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = structlog.get_logger(__name__)


class IPRateLimiter:
    """Thread-safe per-IP rate limiter using a sliding window.

    Stores a deque of request timestamps per client IP and rejects new
    requests if more than `max_requests` arrived within `window_seconds`.
    """

    def __init__(self, max_requests: int, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._lock = threading.Lock()
        self._buckets: dict[str, deque[float]] = {}

    def is_allowed(self, client_ip: str) -> tuple[bool, int]:
        """Check if a request from client_ip is allowed.

        Returns:
            (allowed, remaining) tuple
        """
        now = time.monotonic()
        cutoff = now - self.window_seconds
        with self._lock:
            bucket = self._buckets.setdefault(client_ip, deque())
            # Drop expired entries
            while bucket and bucket[0] < cutoff:
                bucket.popleft()
            if len(bucket) >= self.max_requests:
                return False, 0
            bucket.append(now)
            return True, self.max_requests - len(bucket)

    def cleanup(self, max_age_seconds: int = 300) -> int:
        """Remove entries for IPs not seen in `max_age_seconds`. Returns count removed."""
        cutoff = time.monotonic() - max_age_seconds
        removed = 0
        with self._lock:
            for ip in list(self._buckets.keys()):
                bucket = self._buckets[ip]
                while bucket and bucket[0] < cutoff:
                    bucket.popleft()
                if not bucket:
                    del self._buckets[ip]
                    removed += 1
        return removed


# Global limiters: one for general traffic, one for sensitive endpoints
_general_limiter = IPRateLimiter(
    max_requests=settings.RATE_LIMIT_PER_MINUTE,
    window_seconds=60,
)
_strict_limiter = IPRateLimiter(
    max_requests=settings.RATE_LIMIT_STRICT_PER_MINUTE,
    window_seconds=60,
)

# Endpoints subject to the strict limit
_STRICT_PATH_PREFIXES = (
    "/api/datasources/refresh",
    "/api/chat",
)


def _is_strict_path(path: str) -> bool:
    return any(path.startswith(p) for p in _STRICT_PATH_PREFIXES)


def _get_client_ip(request: Request) -> str:
    """Resolve client IP, honoring X-Forwarded-For if behind a proxy."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        # First entry is the original client
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Apply per-IP rate limiting to all endpoints.

    - General endpoints: settings.RATE_LIMIT_PER_MINUTE
    - Strict endpoints (refresh, chat): settings.RATE_LIMIT_STRICT_PER_MINUTE
    """

    async def dispatch(self, request: Request, call_next: Callable):
        # Skip health and docs endpoints from BUCKET accounting, but still
        # expose X-RateLimit-* headers so callers/monitoring can observe them.
        is_skip_path = request.url.path.startswith(
            ("/api/health", "/docs", "/openapi.json", "/redoc")
        )

        client_ip = _get_client_ip(request)
        limiter = _strict_limiter if _is_strict_path(request.url.path) else _general_limiter

        if is_skip_path:
            response = await call_next(request)
            response.headers["X-RateLimit-Limit"] = str(limiter.max_requests)
            response.headers["X-RateLimit-Remaining"] = str(limiter.max_requests)
            return response

        allowed, remaining = limiter.is_allowed(client_ip)

        if not allowed:
            logger.warning(
                "rate_limit.exceeded",
                client_ip=client_ip,
                path=request.url.path,
                strict=_is_strict_path(request.url.path),
            )
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={
                    "error_code": "RATE_LIMIT_EXCEEDED",
                    "message": "Too many requests. Please try again later.",
                },
                headers={"Retry-After": "60"},
            )

        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limiter.max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        return response
