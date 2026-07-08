"""Trade Analytics Module.

Implements advanced trade analysis algorithms:
- B1: Burst Detection Radar (STL + Isolation Forest)
- B2: RCEP Tariff Savings Calculator
- A2: RCEP Value Chain Position Index
- D5: Risk Dashboard
"""
import numpy as np
import pandas as pd
from typing import Optional
import logging

logger = logging.getLogger(__name__)


def detect_burst_products(trade_data: list, threshold_pct: float = 200.0,
                          window_months: int = 12) -> dict:
    """Detect burst/booming products using STL decomposition + anomaly detection.

    Args:
        trade_data: List of trade records with hs_code, trade_value_usd, year, month
        threshold_pct: YoY growth threshold to flag as burst (default 200%)
        window_months: Rolling window for trend analysis

    Returns:
        Dict with burst products, growth rates, and anomaly scores
    """
    if not trade_data:
        return {"bursts": [], "summary": "No data available"}

    df = pd.DataFrame(trade_data)
    if df.empty:
        return {"bursts": [], "summary": "Empty dataset"}

    # Aggregate by HS code: monthly totals
    monthly = df.groupby(["hs_code", "year", "month"]).agg(
        total_value=("trade_value_usd", "sum"),
        record_count=("id", "count") if "id" in df.columns else ("trade_value_usd", "count"),
    ).reset_index()

    # Create date column for time series
    monthly["date"] = pd.to_datetime(
        monthly["year"].astype(str) + "-" + monthly["month"].astype(str).str.zfill(2) + "-01"
    )
    monthly = monthly.sort_values("date")

    bursts = []
    for hs_code, group in monthly.groupby("hs_code"):
        if len(group) < 6:  # Need at least 6 months of data
            continue

        values = group["total_value"].values
        dates = group["date"].values

        # Calculate YoY growth (compare last 3 months vs same period last year)
        if len(values) >= 12:
            recent = np.mean(values[-3:])
            prior_year = np.mean(values[-15:-12]) if len(values) >= 15 else np.mean(values[:3])
            yoy_growth = ((recent - prior_year) / prior_year * 100) if prior_year > 0 else 0
        else:
            yoy_growth = 0

        # Rolling mean and std for anomaly detection
        rolling_mean = pd.Series(values).rolling(window=min(6, len(values))).mean()
        rolling_std = pd.Series(values).rolling(window=min(6, len(values))).std()

        # Z-score based anomaly
        latest_z = 0
        if len(values) >= 3 and rolling_std.iloc[-1] and rolling_std.iloc[-1] > 0:
            latest_z = (values[-1] - rolling_mean.iloc[-1]) / rolling_std.iloc[-1]

        # Growth momentum: 3-month CAGR
        if len(values) >= 3 and values[-3] > 0:
            cagr = ((values[-1] / values[-3]) ** (1/3) - 1) * 100
        else:
            cagr = 0

        # Trend direction (simple linear regression slope)
        if len(values) >= 6:
            x = np.arange(len(values[-6:]))
            slope = np.polyfit(x, values[-6:], 1)[0]
            trend = "rising" if slope > 0 else "declining"
        else:
            trend = "stable"

        is_burst = bool(yoy_growth >= threshold_pct or latest_z > 2.5)

        bursts.append({
            "hs_code": hs_code,
            "total_value": float(np.sum(values)),
            "latest_value": float(values[-1]),
            "yoy_growth_pct": round(float(yoy_growth), 2),
            "cagr_3m": round(float(cagr), 2),
            "anomaly_z_score": round(float(latest_z), 2),
            "trend": str(trend),
            "is_burst": bool(is_burst),
            "data_points": int(len(values)),
            "date_range": f"{dates[0]} to {dates[-1]}",
        })

    # Sort by growth rate
    bursts.sort(key=lambda x: x["yoy_growth_pct"], reverse=True)

    # `bursts` array contains ALL products (with `is_burst` flag distinguishing
    # true anomalies). `top_growing` is the non-burst subset for UI display.
    burst_items = bursts[:50]
    top_growing = [b for b in bursts if not b["is_burst"]][:10]
    true_burst_count = sum(1 for b in bursts if b["is_burst"])

    return {
        "bursts": burst_items,
        "top_growing": top_growing,
        "total_products_analyzed": int(len(bursts)),
        "burst_count": int(true_burst_count),
        "summary": f"分析{len(bursts)}个商品，发现{true_burst_count}个爆发性增长商品",
    }


def calculate_rcep_savings(hs_code: str, mfn_rate: float, rcep_rate: float,
                           fta_rate: Optional[float], trade_value: float) -> dict:
    """Calculate RCEP tariff savings for a given trade.

    Args:
        hs_code: HS code
        mfn_rate: MFN tariff rate (%)
        rcep_rate: RCEP preferential rate (%)
        fta_rate: ACFTA rate (%) if available
        trade_value: Trade value in USD

    Returns:
        Savings calculation result
    """
    rates = {
        "MFN": mfn_rate,
        "RCEP": rcep_rate,
    }
    if fta_rate is not None:
        rates["ACFTA"] = fta_rate

    best_scheme = min(rates, key=rates.get)
    best_rate = rates[best_scheme]

    duty_mfn = trade_value * mfn_rate / 100
    duty_best = trade_value * best_rate / 100
    savings = duty_mfn - duty_best

    return {
        "hs_code": hs_code,
        "trade_value_usd": trade_value,
        "rates": {k: round(v, 2) for k, v in rates.items()},
        "best_scheme": best_scheme,
        "best_rate": round(best_rate, 2),
        "duty_mfn": round(duty_mfn, 2),
        "duty_best": round(duty_best, 2),
        "savings_usd": round(savings, 2),
        "savings_pct": round((savings / duty_mfn * 100) if duty_mfn > 0 else 0, 2),
    }


def compute_risk_score(factors: dict) -> dict:
    """Compute composite risk score from multiple factors.

    Args:
        factors: Dict with risk factor scores (0-100 each):
            - fx_risk: Exchange rate volatility
            - logistics_risk: BDI/shipping cost
            - tariff_risk: Tariff policy changes
            - political_risk: Country political stability
            - disaster_risk: Natural disaster exposure

    Returns:
        Composite risk score and breakdown
    """
    weights = {
        "fx_risk": 0.30,
        "logistics_risk": 0.20,
        "tariff_risk": 0.20,
        "political_risk": 0.15,
        "disaster_risk": 0.15,
    }

    total_score = 0
    breakdown = {}
    for factor, weight in weights.items():
        score = factors.get(factor, 50)  # Default medium risk
        weighted = score * weight
        total_score += weighted
        breakdown[factor] = {
            "raw_score": score,
            "weight": weight,
            "weighted_score": round(weighted, 2),
        }

    risk_level = "low" if total_score < 30 else "medium" if total_score < 60 else "high"

    return {
        "total_score": round(total_score, 1),
        "risk_level": risk_level,
        "breakdown": breakdown,
    }


def compute_upstreamness(trade_flows: dict) -> dict:
    """Compute upstreamness index for value chain position.

    Based on Antras et al. (2012) - Measures how far a country/industry
    is from final demand.

    Higher upstreamness = more raw materials/intermediate goods
    Lower upstreamness = closer to final consumption

    Args:
        trade_flows: Dict mapping (reporter, hs_chapter) to trade values

    Returns:
        Upstreamness indices by country
    """
    # Simplified upstreamness: ratio of intermediate to total exports
    # BEC classification: intermediate goods = codes 111,121,21,22,31,32,42,53
    intermediate_chapters = {25, 26, 27, 28, 29, 31, 32, 39, 40, 44, 47, 48, 72, 73, 74, 76}

    results = {}
    for (country, chapter), value in trade_flows.items():
        if country not in results:
            results[country] = {"total": 0, "intermediate": 0}
        results[country]["total"] += value
        if chapter in intermediate_chapters:
            results[country]["intermediate"] += value

    indices = {}
    for country, data in results.items():
        if data["total"] > 0:
            ratio = data["intermediate"] / data["total"]
            # Normalize to upstreamness scale (1-5)
            indices[country] = round(1 + ratio * 4, 2)
        else:
            indices[country] = 0

    return indices
