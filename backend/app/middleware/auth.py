"""API Key authentication middleware.

Validates X-API-Key header on protected endpoints. If API_KEY is not
configured (empty), authentication is disabled (development mode).

Public endpoints (no auth required): /docs, /openapi.json, /api/health
"""

from __future__ import annotations

import hmac
from collections.abc import Callable

import structlog
from fastapi import Request, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings

logger = structlog.get_logger(__name__)

# Endpoints that never require API key (health, docs, etc.)
_PUBLIC_PATH_PREFIXES = (
    "/docs",
    "/openapi.json",
    "/redoc",
    "/api/health",
)


def _is_public_path(path: str) -> bool:
    """Check if the path is public (no auth required)."""
    return any(path.startswith(prefix) for prefix in _PUBLIC_PATH_PREFIXES)


def _is_protected_path(path: str) -> bool:
    """Check if the path requires API key authentication."""
    if _is_public_path(path):
        return False
    protected = settings.api_key_protected_paths_list
    if not protected:
        return False
    return any(path.startswith(p) for p in protected)


class APIKeyAuthMiddleware(BaseHTTPMiddleware):
    """Validate X-API-Key header on protected endpoints.

    Uses constant-time comparison to prevent timing attacks.
    If settings.API_KEY is empty, authentication is disabled.
    """

    async def dispatch(self, request: Request, call_next: Callable):
        # Skip if API key not configured (dev mode or auth disabled)
        if not settings.API_KEY:
            return await call_next(request)

        # Skip public endpoints
        if _is_public_path(request.url.path):
            return await call_next(request)

        # Only enforce on protected paths
        if not _is_protected_path(request.url.path):
            return await call_next(request)

        client_key = request.headers.get("X-API-Key")
        if not client_key:
            logger.warning(
                "auth.missing_api_key",
                path=request.url.path,
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={
                    "error_code": "AUTH_MISSING_API_KEY",
                    "message": "X-API-Key header is required for this endpoint",
                },
                headers={"WWW-Authenticate": "ApiKey"},
            )

        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(client_key, settings.API_KEY):
            logger.warning(
                "auth.invalid_api_key",
                path=request.url.path,
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={
                    "error_code": "AUTH_INVALID_API_KEY",
                    "message": "Invalid API key",
                },
            )

        return await call_next(request)
