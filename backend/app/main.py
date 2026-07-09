"""ACTAP - ASEAN Cross-Border Trade AI Analytics Platform.

FastAPI application entry point. Wires up:
- Configuration (env-driven)
- Middleware chain: CORS, request tracking, rate limit, auth
- Error handling with sanitized responses
- Routers (domain + health)
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import ORJSONResponse

from app.core.config import settings, validate_production_config
from app.core.logging import configure_logging
from app.middleware.auth import APIKeyAuthMiddleware
from app.middleware.errors import register_exception_handlers
from app.middleware.metrics_mw import PrometheusMetricsMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.middleware.tracking import RequestTrackingMiddleware

configure_logging()
logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown hooks."""
    # Validate production config before doing anything else
    validate_production_config()

    # Lazy imports to avoid loading models at import time
    from app.mock_data.init_db import init_database
    from app.models.database import Base, engine

    logger.info(
        "startup.begin",
        version=settings.APP_VERSION,
        env=settings.ENVIRONMENT.value,
    )
    Base.metadata.create_all(bind=engine)
    init_database()
    logger.info("startup.complete")
    yield
    logger.info("shutdown.complete")


app = FastAPI(
    title="ACTAP - 东盟跨境贸易AI智能分析平台",
    description="ASEAN Cross-Border Trade AI Analytics Platform",
    version=settings.APP_VERSION,
    lifespan=lifespan,
    default_response_class=ORJSONResponse,
)

# === Middleware chain (order matters: outer to inner) ===
# 1. CORS — must be first to handle preflight
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=[
        "X-Request-ID",
        "X-Response-Time-Ms",
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
    ],
)

# 2. Request tracking (request_id, timing) — applied to all requests
app.add_middleware(RequestTrackingMiddleware)

# 3. Metrics collection (counts + duration)
app.add_middleware(PrometheusMetricsMiddleware)

# 4. Rate limiting
app.add_middleware(RateLimitMiddleware)

# 5. API Key auth on protected paths
app.add_middleware(APIKeyAuthMiddleware)

# === Global exception handlers (sanitized error responses) ===
register_exception_handlers(app)

# === Routers ===
# Lazy import to ensure settings are loaded first
from app.api.routes import (  # noqa: E402
    ai_predict,
    analytics,
    assets,
    chat,
    datasources,
    enterprise,
    health,
    overview,
    quant,
    socioeconomic,
    tariff,
    trade,
)

app.include_router(health.router)
app.include_router(overview.router, prefix="/api/overview", tags=["总览"])
app.include_router(trade.router, prefix="/api/trade", tags=["贸易分析"])
app.include_router(ai_predict.router, prefix="/api/ai", tags=["AI预测"])
app.include_router(tariff.router, prefix="/api/tariff", tags=["关税计算"])
app.include_router(chat.router, prefix="/api/chat", tags=["AI助手"])
app.include_router(assets.router, prefix="/api/assets", tags=["数据资产"])
app.include_router(datasources.router, prefix="/api/datasources", tags=["数据源管理"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["智能分析"])
app.include_router(quant.router, prefix="/api", tags=["量化分析"])
app.include_router(enterprise.router, prefix="/api/enterprise", tags=["企业风控中心"])
app.include_router(socioeconomic.router, prefix="/api/socioeconomic", tags=["社会经济仪表盘"])
