"""ACTAP - ASEAN Cross-Border Trade AI Analytics Platform.
FastAPI application entry point.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.models.database import engine, Base
from app.mock_data.init_db import init_database
from app.api.routes import overview, trade, ai_predict, tariff, chat, assets, datasources, analytics


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and mock data on startup."""
    Base.metadata.create_all(bind=engine)
    init_database()
    yield


app = FastAPI(
    title="ACTAP - 东盟跨境贸易AI智能分析平台",
    description="ASEAN Cross-Border Trade AI Analytics Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(overview.router, prefix="/api/overview", tags=["总览"])
app.include_router(trade.router, prefix="/api/trade", tags=["贸易分析"])
app.include_router(ai_predict.router, prefix="/api/ai", tags=["AI预测"])
app.include_router(tariff.router, prefix="/api/tariff", tags=["关税计算"])
app.include_router(chat.router, prefix="/api/chat", tags=["AI助手"])
app.include_router(assets.router, prefix="/api/assets", tags=["数据资产"])
app.include_router(datasources.router, prefix="/api/datasources", tags=["数据源管理"])
app.include_router(analytics.router, prefix="/api/analytics", tags=["智能分析"])


@app.get("/api/health")
def health_check():
    return {"status": "ok", "version": "1.0.0"}
