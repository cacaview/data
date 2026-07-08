"""Prometheus metrics middleware.

Records request count and duration for every HTTP request.
"""
from __future__ import annotations

import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.metrics import registry


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """Record request count + duration into the in-memory registry."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Skip /metrics itself to avoid self-referential noise
        if request.url.path == "/api/metrics":
            return await call_next(request)

        start = time.perf_counter()
        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            status_code = 500
            raise
        finally:
            duration_ms = (time.perf_counter() - start) * 1000
            registry.record_request(
                method=request.method,
                path=request.url.path,
                status_code=status_code,
                duration_ms=duration_ms,
            )
        return response
