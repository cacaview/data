"""AI prediction routes -- LSTM mock, K-Means clustering, risk alerts."""

import hashlib
import math

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.constants import (
    MOM_CHANGE_HIGH_THRESHOLD,
    MOM_CHANGE_MEDIUM_THRESHOLD,
    YOY_DROP_HIGH_THRESHOLD,
    YOY_DROP_MEDIUM_THRESHOLD,
)
from app.models.database import get_db
from app.models.schemas import ClusterItem, PredictionPoint, PredictionResult, RiskAlert
from app.models.schemas_db import Country, Product, TradeRecord

router = APIRouter()


def _simple_seed(key: str) -> float:
    """Deterministic pseudo-random float in [0, 1) from a string key."""
    h = hashlib.md5(key.encode()).hexdigest()
    return int(h[:8], 16) / 0xFFFFFFFF


# ── GET /prediction ─────────────────────────────────────────────────────────
@router.get("/prediction", response_model=PredictionResult)
def get_prediction(
    country: str | None = Query(None, description="ISO country code"),
    product: str | None = Query(None, description="HS section name"),
    db: Session = Depends(get_db),
):
    """Mock LSTM prediction using historical data + sine-wave projection.

    When a real model is deployed, replace the body of this function.
    """
    # Pull historical monthly data
    q = db.query(
        TradeRecord.year,
        TradeRecord.month,
        func.sum(TradeRecord.trade_value_usd).label("total"),
    ).filter(TradeRecord.reporter == "CHN")

    if country:
        q = q.filter(TradeRecord.partner == country)
    if product:
        q = q.filter(TradeRecord.hs_section == product)

    rows = (
        q.group_by(TradeRecord.year, TradeRecord.month)
        .order_by(TradeRecord.year, TradeRecord.month)
        .all()
    )

    if not rows:
        # Return empty result if no data
        return PredictionResult(model_name="LSTM-Mock", mape=0.0, data=[])

    # Build actual series
    actual_values = [r[2] for r in rows]
    actual_dates = [f"{r[0]}-{r[1]:02d}" for r in rows]

    # Compute mean & std for synthetic predictions
    mean_val = sum(actual_values) / len(actual_values)
    variance = sum((v - mean_val) ** 2 for v in actual_values) / max(len(actual_values), 1)
    std_val = math.sqrt(variance) if variance > 0 else mean_val * 0.05

    seed = _simple_seed(f"{country or 'all'}:{product or 'all'}")

    # Build prediction points: historical actuals + 6-month forecast
    data: list[PredictionPoint] = []

    # Historical data with "predicted" overlay
    for i, (date, val) in enumerate(zip(actual_dates, actual_values, strict=False)):
        phase = seed * 2 * math.pi + i * 0.3
        noise = std_val * 0.1 * math.sin(phase)
        predicted = val + noise
        data.append(PredictionPoint(date=date, actual=round(val, 2), predicted=round(predicted, 2)))

    # 6-month forward forecast
    last_year, last_month = rows[-1][0], rows[-1][1]
    for i in range(1, 7):
        m = last_month + i
        y = last_year
        while m > 12:
            m -= 12
            y += 1

        phase = seed * 2 * math.pi + (len(actual_values) + i) * 0.3
        trend = mean_val * (1 + 0.02 * i + 0.05 * math.sin(phase))
        noise = std_val * 0.15 * math.sin(phase + 1)
        predicted = trend + noise
        margin = std_val * 0.2 * (1 + i * 0.1)

        data.append(
            PredictionPoint(
                date=f"{y}-{m:02d}",
                predicted=round(predicted, 2),
                lower=round(predicted - margin, 2),
                upper=round(predicted + margin, 2),
            )
        )

    # Compute mock MAPE on historical portion
    mape_sum = 0.0
    for pt in data:
        if pt.actual and pt.predicted and pt.actual != 0:
            mape_sum += abs(pt.actual - pt.predicted) / abs(pt.actual)
    mape = (mape_sum / len(actual_values) * 100) if actual_values else 0.0

    return PredictionResult(
        model_name="LSTM-Mock",
        mape=round(mape, 2),
        data=data,
    )


# ── GET /clustering ─────────────────────────────────────────────────────────
@router.get("/clustering", response_model=list[ClusterItem])
def get_clustering(db: Session = Depends(get_db)):
    """K-Means style clustering of products by trade value and growth.

    Uses a simple 3-cluster heuristic on trade_value and growth_rate.
    """
    latest_year = db.query(func.max(TradeRecord.year)).scalar()
    if not latest_year:
        return []

    prev_year = latest_year - 1

    # Current year product stats
    current = dict(
        db.query(
            TradeRecord.hs_section,
            func.sum(TradeRecord.trade_value_usd),
        )
        .filter(
            TradeRecord.year == latest_year,
            TradeRecord.reporter == "CHN",
            TradeRecord.hs_section.isnot(None),
        )
        .group_by(TradeRecord.hs_section)
        .all()
    )

    prev = dict(
        db.query(
            TradeRecord.hs_section,
            func.sum(TradeRecord.trade_value_usd),
        )
        .filter(
            TradeRecord.year == prev_year,
            TradeRecord.reporter == "CHN",
            TradeRecord.hs_section.isnot(None),
        )
        .group_by(TradeRecord.hs_section)
        .all()
    )

    if not current:
        return []

    # Get a representative HS code for each section
    section_hs = dict(
        db.query(TradeRecord.hs_section, func.min(TradeRecord.hs_code))
        .filter(
            TradeRecord.year == latest_year,
            TradeRecord.reporter == "CHN",
            TradeRecord.hs_section.isnot(None),
        )
        .group_by(TradeRecord.hs_section)
        .all()
    )

    # Product name lookup from products table
    hs_codes = [v for v in section_hs.values() if v]
    prod_names: dict[str, str] = {}
    if hs_codes:
        for p in db.query(Product).filter(Product.hs_code.in_(hs_codes)).all():
            prod_names[p.hs_code] = p.hs_name_cn or p.hs_name_en or p.hs_code

    # Compute values and thresholds for clustering
    items_data = []
    for section, value in current.items():
        prev_val = prev.get(section, 0) or 0
        growth = ((value - prev_val) / prev_val * 100) if prev_val else 0.0
        items_data.append((section, value, growth))

    # Determine cluster boundaries (terciles by trade value)
    sorted_by_val = sorted(items_data, key=lambda x: x[1])
    n = len(sorted_by_val)
    high_threshold = sorted_by_val[int(n * 0.66)][1] if n > 2 else sorted_by_val[-1][1]
    mid_threshold = sorted_by_val[int(n * 0.33)][1] if n > 1 else 0

    cluster_labels = {0: "低贸易量", 1: "中等贸易量", 2: "高贸易量"}

    results: list[ClusterItem] = []
    for section, value, growth in items_data:
        if value >= high_threshold:
            cluster = 2
        elif value >= mid_threshold:
            cluster = 1
        else:
            cluster = 0

        hs_code = section_hs.get(section, "0000")
        name = prod_names.get(hs_code, section)

        results.append(
            ClusterItem(
                hs_code=hs_code,
                name=name,
                trade_value=round(value, 2),
                growth_rate=round(growth, 2),
                cluster=cluster,
                cluster_label=cluster_labels[cluster],
            )
        )

    return results


# ── GET /risk-alerts ────────────────────────────────────────────────────────
@router.get("/risk-alerts", response_model=list[RiskAlert])
def get_risk_alerts(db: Session = Depends(get_db)):
    """Detect anomalous trade patterns as risk alerts.

    Flags countries/sections where trade value dropped sharply or
    volatility is high relative to the mean.
    """
    latest_year = db.query(func.max(TradeRecord.year)).scalar()
    if not latest_year:
        return []

    prev_year = latest_year - 1

    # Country-level risk: sharp YoY drops
    current_country = dict(
        db.query(TradeRecord.partner, func.sum(TradeRecord.trade_value_usd))
        .filter(TradeRecord.year == latest_year, TradeRecord.reporter == "CHN")
        .group_by(TradeRecord.partner)
        .all()
    )
    prev_country = dict(
        db.query(TradeRecord.partner, func.sum(TradeRecord.trade_value_usd))
        .filter(TradeRecord.year == prev_year, TradeRecord.reporter == "CHN")
        .group_by(TradeRecord.partner)
        .all()
    )

    country_names: dict[str, str] = {}
    codes = list(current_country.keys())
    if codes:
        for c in db.query(Country).filter(Country.code.in_(codes)).all():
            country_names[c.code] = c.name_cn

    alerts: list[RiskAlert] = []

    for code, val in current_country.items():
        prev_val = prev_country.get(code, 0) or 0
        if prev_val == 0:
            continue

        change_pct = (val - prev_val) / prev_val * 100
        name = country_names.get(code, code)

        if change_pct < YOY_DROP_HIGH_THRESHOLD:
            alerts.append(
                RiskAlert(
                    date=f"{latest_year}-01",
                    level="high",
                    country=name,
                    description=f"{name}对华贸易额同比下降{abs(change_pct):.1f}%，降幅显著",
                    suggestion=f"建议关注{name}市场政策变化，评估供应链替代方案",
                    metric_value=round(change_pct, 2),
                )
            )
        elif change_pct < YOY_DROP_MEDIUM_THRESHOLD:
            alerts.append(
                RiskAlert(
                    date=f"{latest_year}-01",
                    level="medium",
                    country=name,
                    description=f"{name}对华贸易额同比下降{abs(change_pct):.1f}%",
                    suggestion=f"建议跟踪{name}经济指标，做好风险预案",
                    metric_value=round(change_pct, 2),
                )
            )

    # Monthly volatility detection: large month-to-month swings
    monthly = (
        db.query(
            TradeRecord.year,
            TradeRecord.month,
            func.sum(TradeRecord.trade_value_usd).label("total"),
        )
        .filter(TradeRecord.year == latest_year, TradeRecord.reporter == "CHN")
        .group_by(TradeRecord.year, TradeRecord.month)
        .order_by(TradeRecord.year, TradeRecord.month)
        .all()
    )

    if len(monthly) >= 3:
        values = [r[2] for r in monthly]
        sum(values) / len(values)
        for i in range(1, len(values)):
            if values[i - 1] == 0:
                continue
            mom_change = (values[i] - values[i - 1]) / values[i - 1] * 100
            if abs(mom_change) > MOM_CHANGE_MEDIUM_THRESHOLD:
                level = "high" if abs(mom_change) > MOM_CHANGE_HIGH_THRESHOLD else "medium"
                alerts.append(
                    RiskAlert(
                        date=f"{monthly[i][0]}-{monthly[i][1]:02d}",
                        level=level,
                        country="全局",
                        description=f"月度贸易额环比波动{mom_change:+.1f}%，波动异常",
                        suggestion="建议排查数据质量或关注突发性贸易事件",
                        metric_value=round(mom_change, 2),
                    )
                )

    # Sort by severity
    level_order = {"high": 0, "medium": 1, "low": 2}
    alerts.sort(key=lambda a: (level_order.get(a.level, 3), a.date))

    return alerts
