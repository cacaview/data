"""Request tracking middleware.

Generates a unique request ID for each incoming request, attaches it to
the request state, and echoes it back in the response header for
distributed tracing and log correlation.
"""
from __future__ import annotations

import time
import uuid
from typing import Callable

import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = structlog.get_logger(__name__)


class RequestTrackingMiddleware(BaseHTTPMiddleware):
    """Track each HTTP request with a unique ID and timing.

    - Generates a request_id (uses X-Request-ID from caller if provided)
    - Binds the request_id to the structlog contextvars so all log lines
      in this request automatically include it
    - Logs request start/end with timing info
    - Returns the request_id in response header X-Request-ID
    - Honors W3C traceparent header for distributed tracing
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Use incoming X-Request-ID or traceparent (W3C) if present,
        # otherwise generate a new one
        incoming_rid = request.headers.get("X-Request-ID")
        traceparent = request.headers.get("traceparent")
        request_id = incoming_rid or (
            _extract_trace_id(traceparent) if traceparent else None
        ) or str(uuid.uuid4())
        request.state.request_id = request_id

        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path

        # Bind to contextvars so all structlog calls in this request get request_id
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            method=method,
            path=path,
            client_ip=client_ip,
        )

        start_time = time.perf_counter()
        logger.info("request.start")

        try:
            response = await call_next(request)
        except Exception:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.exception("request.error", duration_ms=round(duration_ms, 2))
            raise
        finally:
            structlog.contextvars.clear_contextvars()

        duration_ms = (time.perf_counter() - start_time) * 1000
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}"

        logger.info(
            "request.end",
            status_code=response.status_code,
            duration_ms=round(duration_ms, 2),
        )
        return response


def _extract_trace_id(traceparent: str) -> str | None:
    """Extract the 32-char trace ID from a W3C traceparent header.

    Format: version-trace_id-span_id-flags (e.g. 00-0af7651916cd43dd8448eb211c80319c-b7ad6b7169203331-01)
    """
    try:
        parts = traceparent.split("-")
        if len(parts) >= 2 and len(parts[1]) == 32:
            return parts[1]
    except (ValueError, AttributeError):
        pass
    return None
