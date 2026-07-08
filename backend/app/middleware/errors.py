"""Unified error code system and exception handlers.

Provides:
- Standard error codes by category
- BusinessError for domain-level errors with code + message
- FastAPI exception handlers that return sanitized responses in production
"""

from __future__ import annotations

from enum import Enum
from typing import Any

import structlog
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

logger = structlog.get_logger(__name__)


def _get_settings():
    """Lazily resolve settings so tests can monkeypatch app.core.config.settings."""
    from app.core.config import settings

    return settings


class ErrorCode(str, Enum):
    """Unified error code catalog.

    Codes are namespaced by category for easy filtering and aggregation.
    Format: <CATEGORY>_<SPECIFIC_ERROR>
    """

    # Generic
    INTERNAL_ERROR = "INTERNAL_ERROR"
    NOT_FOUND = "NOT_FOUND"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    UNAUTHORIZED = "UNAUTHORIZED"
    FORBIDDEN = "FORBIDDEN"
    RATE_LIMIT_EXCEEDED = "RATE_LIMIT_EXCEEDED"

    # Auth
    AUTH_MISSING_API_KEY = "AUTH_MISSING_API_KEY"
    AUTH_INVALID_API_KEY = "AUTH_INVALID_API_KEY"

    # External data source errors
    EXTERNAL_API_UNAVAILABLE = "EXTERNAL_API_UNAVAILABLE"
    EXTERNAL_API_TIMEOUT = "EXTERNAL_API_TIMEOUT"
    EXTERNAL_API_INVALID_RESPONSE = "EXTERNAL_API_INVALID_RESPONSE"

    # Domain
    COUNTRY_NOT_FOUND = "COUNTRY_NOT_FOUND"
    PRODUCT_NOT_FOUND = "PRODUCT_NOT_FOUND"
    TARIFF_DATA_MISSING = "TARIFF_DATA_MISSING"
    INVALID_QUERY_PARAMS = "INVALID_QUERY_PARAMS"


class BusinessError(Exception):
    """Domain-level error with a structured code.

    Use this for business logic errors that should return a specific
    HTTP status and machine-readable code to the client.
    """

    def __init__(
        self,
        code: ErrorCode,
        message: str,
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: dict[str, Any] | None = None,
    ) -> None:
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)

    def to_response(self, request_id: str | None = None) -> dict[str, Any]:
        """Serialize error for HTTP response."""
        body = {
            "error_code": self.code.value,
            "message": self.message,
        }
        if self.details:
            body["details"] = self.details
        if request_id:
            body["request_id"] = request_id
        return body


# Patterns that suggest sensitive data leakage; replace in user-visible messages
_SENSITIVE_PATTERNS = (
    "api_key",
    "apikey",
    "password",
    "passwd",
    "secret",
    "token",
    "openai",
    "deepseek",
    "sk-",
    "bearer ",
)


def _sanitize_message(message: str) -> str:
    """Strip potentially sensitive substrings from user-visible error messages.

    In production, raw exception messages can leak credentials or internal
    paths. This produces a generic placeholder for any message that
    mentions a sensitive pattern.
    """
    if not _get_settings().is_production:
        return message
    lower = message.lower()
    if any(p in lower for p in _SENSITIVE_PATTERNS):
        return "An internal error occurred. Please contact support with the request_id."
    return message


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers on the FastAPI app."""

    @app.exception_handler(BusinessError)
    async def business_error_handler(request: Request, exc: BusinessError):
        request_id = getattr(request.state, "request_id", None)
        logger.warning(
            "business_error",
            error_code=exc.code.value,
            status_code=exc.status_code,
            path=request.url.path,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_response(request_id=request_id),
        )

    @app.exception_handler(StarletteHTTPException)
    async def starlette_http_exception_handler(request: Request, exc: StarletteHTTPException):
        """Handle 404/405 raised by Starlette routing (not FastAPI handlers).

        FastAPI's HTTPException handler doesn't match these because Starlette
        raises its own HTTPException for unrouted paths and wrong methods.
        """
        request_id = getattr(request.state, "request_id", None)
        message = (
            "An internal error occurred. Please contact support with the request_id."
            if exc.status_code >= 500 and _get_settings().is_production
            else _sanitize_message(str(exc.detail))
        )
        body = {
            "error_code": "HTTP_ERROR",
            "message": message,
        }
        if request_id:
            body["request_id"] = request_id
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        request_id = getattr(request.state, "request_id", None)
        # Treat unhandled HTTPException as a generic 500 in production
        if exc.status_code >= 500 and _get_settings().is_production:
            message = "An internal error occurred. Please contact support with the request_id."
        else:
            message = _sanitize_message(str(exc.detail))
        body = {
            "error_code": "HTTP_ERROR",
            "message": message,
        }
        if request_id:
            body["request_id"] = request_id
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        request_id = getattr(request.state, "request_id", None)
        # Sanitize field-level errors (they may echo back user input)
        safe_errors = []
        for err in exc.errors():
            safe_errors.append(
                {
                    "field": ".".join(str(loc) for loc in err.get("loc", [])),
                    "type": err.get("type"),
                    "message": _sanitize_message(err.get("msg", "")),
                }
            )
        body = {
            "error_code": ErrorCode.VALIDATION_ERROR.value,
            "message": "Request validation failed",
            "details": safe_errors,
        }
        if request_id:
            body["request_id"] = request_id
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=body,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Catch-all: log full traceback, return sanitized message to client."""
        request_id = getattr(request.state, "request_id", None)
        logger.exception(
            "unhandled_exception",
            path=request.url.path,
            exception_type=exc.__class__.__name__,
        )
        message = (
            "An internal error occurred. Please contact support with the request_id."
            if _get_settings().is_production
            else f"{exc.__class__.__name__}: {_sanitize_message(str(exc))}"
        )
        body = {
            "error_code": ErrorCode.INTERNAL_ERROR.value,
            "message": message,
        }
        if request_id:
            body["request_id"] = request_id
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=body,
        )
