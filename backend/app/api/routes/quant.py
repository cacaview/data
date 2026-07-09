"""Quantitative Analytics API Routes.

Implements quant-style analysis features:
- /quant/factors: Multi-factor trade decomposition
- /quant/correlation: Cross-country correlation & cointegration
- /quant/signals: Trading signals dashboard
- /quant/forecast: Advanced time series forecasting
- /quant/var: Value at Risk for trade
- /quant/portfolio: Trade portfolio optimization
- /quant/backtest: Trade scenario backtesting
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.schemas_db import TradeRecord

router = APIRouter(prefix="/quant", tags=["Quantitative Analytics"])


def _get_trade_data(db: Session, partner: str | None = None,
                    hs_code: str | None = None) -> list[dict]:
    """Extract trade records as list of dicts for analytics modules."""
    query = db.query(TradeRecord)
    if partner:
        query = query.filter(TradeRecord.partner == partner)
    if hs_code:
        query = query.filter(TradeRecord.hs_code == hs_code)
    records = query.all()
    return [
        {
            "id": r.id,
            "year": r.year,
            "month": r.month,
            "reporter": r.reporter,
            "partner": r.partner,
            "hs_code": r.hs_code,
            "hs_chapter": r.hs_chapter,
            "hs_section": r.hs_section,
            "trade_value_usd": r.trade_value_usd,
            "trade_flow": r.trade_flow,
        }
        for r in records
    ]


# ── Forecast ──
@router.get("/forecast")
def get_forecast(
    partner: str = Query("VNM", description="Partner country code"),
    hs_code: str | None = Query(None, description="HS code filter"),
    model: str = Query("ensemble", description="Model: auto_arima/holt_winters/ensemble"),
    horizon: int = Query(6, ge=1, le=24, description="Forecast horizon in months"),
    db: Session = Depends(get_db),
):
    """Advanced time series forecasting using ARIMA, Holt-Winters, or ensemble."""
    from app.data.ts_models import forecast_trade_series

    trade_data = _get_trade_data(db, partner=partner, hs_code=hs_code)
    if not trade_data:
        return {"model_name": model, "mape": 0, "rmse": 0, "data": [], "error": "No data"}

    result = forecast_trade_series(trade_data, partner=partner or "ALL",
                                   hs_code=hs_code or "ALL", horizon=horizon)
    return result


# ── Correlation ──
@router.get("/correlation")
def get_correlation(
    entities: str = Query("country", description="Correlate by 'country' or 'product'"),
    db: Session = Depends(get_db),
):
    """Compute correlation matrix across countries or product categories."""
    from app.data.correlation_engine import compute_correlation_matrix

    trade_data = _get_trade_data(db)
    if not trade_data:
        return {"entities": [], "matrix": [], "method": "pearson"}

    result = compute_correlation_matrix(trade_data, entities=entities)
    return result


@router.get("/correlation/clusters")
def get_clusters(
    n_clusters: int = Query(3, ge=2, le=8, description="Number of clusters"),
    db: Session = Depends(get_db),
):
    """Cluster countries/products by trade patterns."""
    from app.data.correlation_engine import cluster_entities

    trade_data = _get_trade_data(db)
    if not trade_data:
        return {"clusters": [], "explained_variance": 0, "n_clusters": n_clusters}

    result = cluster_entities(trade_data, n_clusters=n_clusters)
    return result


# ── Signals ──
@router.get("/signals")
def get_signals(
    partner: str = Query("VNM", description="Partner country code"),
    hs_code: str | None = Query(None, description="HS code filter"),
    db: Session = Depends(get_db),
):
    """Generate composite trading signals for trade opportunities."""
    from app.data.signal_generator import generate_signals

    trade_data = _get_trade_data(db, partner=partner, hs_code=hs_code)
    if not trade_data:
        return {"composite_score": 0, "action": "HOLD", "confidence": 0, "description": "No data"}

    result = generate_signals(trade_data, partner=partner, hs_code=hs_code)
    return result


# ── Factor Analysis ──
@router.get("/factors")
def get_factor_analysis(
    partner: str | None = Query(None, description="Partner country code filter"),
    db: Session = Depends(get_db),
):
    """Multi-factor trade decomposition analysis."""
    from app.data.factor_engine import factor_analysis_report

    trade_data = _get_trade_data(db, partner=partner)
    if not trade_data:
        return {"factors": [], "description": "No data"}

    result = factor_analysis_report(trade_data, partner=partner)
    return result


@router.get("/factors/attribute")
def attribute_change(
    partner: str = Query("VNM"),
    start_year: int = Query(2022),
    start_month: int = Query(1),
    end_year: int = Query(2024),
    end_month: int = Query(12),
    db: Session = Depends(get_db),
):
    """Attribute trade value change between two periods to contributing factors."""
    from app.data.factor_engine import attribute_trade_change

    trade_data = _get_trade_data(db, partner=partner)
    if not trade_data:
        return {"factors": [], "total_change": 0, "r_squared": 0}

    result = attribute_trade_change(
        trade_data,
        period_start=(start_year, start_month),
        period_end=(end_year, end_month),
    )
    return result


# ── VaR ──
@router.get("/var")
def get_var(
    partner: str = Query("VNM", description="Partner country code"),
    confidence: float = Query(0.95, ge=0.90, le=0.99, description="Confidence level"),
    db: Session = Depends(get_db),
):
    """Calculate Value at Risk for trade exposure."""
    from app.data.var_calculator import calculate_var

    trade_data = _get_trade_data(db, partner=partner)
    if not trade_data:
        return {"var_historical": 0, "var_parametric": 0, "cvar": 0, "volatility": 0}

    result = calculate_var(trade_data, confidence_level=confidence)
    return result


# ── Portfolio Optimization ──
@router.get("/portfolio")
def get_portfolio_optimization(
    min_weight: float = Query(0.02, ge=0, le=0.2),
    db: Session = Depends(get_db),
):
    """Optimize trade portfolio across partners for diversification."""
    from app.data.portfolio_optimizer import optimize_portfolio

    trade_data = _get_trade_data(db)
    if not trade_data:
        return {"weights": [], "efficient_frontier": [], "hhi_current": 0}

    result = optimize_portfolio(trade_data, min_weight=min_weight)
    return result


# ── Backtesting ──
@router.post("/backtest")
def run_backtest(
    partner: str = Query("VNM"),
    tariff_change_pct: float | None = Query(None, description="Tariff change %"),
    fx_change_pct: float | None = Query(None, description="FX rate change %"),
    demand_change_pct: float | None = Query(None, description="Demand change %"),
    db: Session = Depends(get_db),
):
    """Run scenario backtesting on trade strategy."""
    from app.data.backtest_engine import run_scenario

    trade_data = _get_trade_data(db, partner=partner)
    if not trade_data:
        return {"scenario": {}, "baseline_total": 0, "simulated_total": 0}

    scenario = {
        "tariff_change_pct": tariff_change_pct,
        "fx_change_pct": fx_change_pct,
        "demand_change_pct": demand_change_pct,
    }
    result = run_scenario(trade_data, scenario, partner=partner)
    return result
