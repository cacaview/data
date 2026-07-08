"""Health check endpoints.

Provides:
- /api/health  — lightweight liveness probe
- /api/health/ready — readiness probe with dependency checks
- /api/metrics — Prometheus-style metrics
"""
from __future__ import annotations

import os
from typing import Any, Dict

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import text

from app.core.config import settings
from app.core.metrics import registry
from app.models.database import engine

router = APIRouter(prefix="/api", tags=["健康检查"])


def _check_database() -> Dict[str, Any]:
    """Check database connectivity with a lightweight SELECT 1."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:200]}


def _check_cache() -> Dict[str, Any]:
    """Check cache database is reachable."""
    try:
        from app.data.cache import CACHE_DB_PATH, get_cache_stats
        exists = os.path.exists(CACHE_DB_PATH)
        stats = get_cache_stats() if exists else None
        return {"status": "ok", "path": CACHE_DB_PATH, "stats": stats}
    except Exception as exc:
        return {"status": "error", "error": str(exc)[:200]}


@router.get("/health")
def health_check():
    """Liveness probe — process is up and responding.

    Lightweight check for liveness probes (k8s, load balancers). Does
    NOT check dependencies — use /ready for that.
    """
    return {
        "status": "ok",
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "environment": settings.ENVIRONMENT.value,
    }


@router.get("/health/ready")
def readiness_check():
    """Readiness probe — process and dependencies are ready.

    Checks:
    - Database connectivity
    - Cache file accessibility

    Returns HTTP 503 when any dependency is unhealthy so that load
    balancers / k8s readiness probes can take the instance out of
    rotation. The body always includes per-dependency status.
    """
    db_check = _check_database()
    cache_check = _check_cache()

    all_ok = db_check["status"] == "ok" and cache_check["status"] == "ok"
    overall = "ok" if all_ok else "degraded"
    http_status = status.HTTP_200_OK if all_ok else status.HTTP_503_SERVICE_UNAVAILABLE

    body = {
        "status": overall,
        "service": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "checks": {
            "database": db_check,
            "cache": cache_check,
        },
    }
    return JSONResponse(status_code=http_status, content=body)


@router.get("/metrics", response_class=PlainTextResponse)
def metrics():
    """Prometheus-style metrics endpoint.

    Exposes request counts, duration sums, error counts, and uptime.
    Suitable for scraping by Prometheus, VictoriaMetrics, etc.
    """
    return registry.render()
