"""Structured logging configuration.

Uses structlog for JSON-formatted logs with built-in context binding
(request_id, path, etc.) and force-traceback for exceptions.

In development, the LOG_FORMAT=text setting yields a colored key=value
output. In production, JSON is emitted by default.
"""
from __future__ import annotations

import logging
import sys
from typing import Any

import structlog

from app.core.config import settings


def configure_logging() -> None:
    """Configure structlog + stdlib logging once at process start."""
    level = getattr(logging, settings.LOG_LEVEL, logging.INFO)
    is_json = settings.LOG_FORMAT.lower() == "json"
    is_tty = sys.stderr.isatty()

    # Shared processors (run on every log record)
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]

    if is_json:
        # Production: pure JSON to stdout
        renderer = structlog.processors.JSONRenderer()
    elif is_tty:
        # Dev TTY: colored, readable
        renderer = structlog.dev.ConsoleRenderer(colors=True)
    else:
        # Dev non-TTY: key=value
        renderer = structlog.processors.KeyValueRenderer(
            key_order=["timestamp", "level", "event"]
        )

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        wrapper_class=structlog.make_filtering_bound_logger(level),
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Quiet down noisy libraries
    for noisy in ("uvicorn.access", "httpx", "httpcore"):
        logging.getLogger(noisy).setLevel(max(level, logging.WARNING))


def get_logger(name: str | None = None) -> structlog.stdlib.BoundLogger:
    """Return a configured structlog logger."""
    return structlog.get_logger(name)
