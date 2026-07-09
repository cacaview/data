"""Value at Risk (VaR) Calculator for Trade Data.

Adapts financial VaR methodology to trade exposure risk:
- Historical VaR: percentile-based
- Parametric VaR: distribution-based
- Conditional VaR (CVaR): expected shortfall
- Stress testing: extreme scenario impact
- Risk contribution decomposition
"""
import logging
import warnings
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_float(v: Any) -> float:
    try:
        f = float(v)
        return f if np.isfinite(f) else 0.0
    except (TypeError, ValueError):
        return 0.0


def _monthly_returns(values: np.ndarray) -> np.ndarray:
    """Month-over-month percentage returns."""
    if len(values) < 2:
        return np.array([])
    returns = np.diff(values) / np.where(np.abs(values[:-1]) > 0, np.abs(values[:-1]), 1.0)
    return returns[np.isfinite(returns)]


def _trade_monthly_totals(trade_data: list) -> pd.DataFrame:
    """Aggregate trade records into monthly totals."""
    df = pd.DataFrame(trade_data)
    if df.empty or "trade_value_usd" not in df.columns:
        return df
    monthly = (
        df.groupby(["year", "month"])["trade_value_usd"]
        .sum()
        .reset_index()
        .sort_values(["year", "month"])
        .reset_index(drop=True)
    )
    return monthly


# ---------------------------------------------------------------------------
# Main VaR Functions
# ---------------------------------------------------------------------------

def calculate_var(trade_data: list, confidence_level: float = 0.95) -> dict:
    """Calculate Value at Risk for trade exposure.

    Parameters
    ----------
    trade_data : list[dict]
        Raw trade records with trade_value_usd, year, month.
    confidence_level : float
        Confidence level (0.90 to 0.99).

    Returns
    -------
    dict with var_historical, var_parametric, cvar, max_drawdown, volatility,
        risk_contributions, stress_tests.
    """
    df = _trade_monthly_totals(trade_data)
    if df.empty or len(df) < 6:
        return {
            "confidence_level": confidence_level,
            "var_historical": 0.0,
            "var_parametric": 0.0,
            "cvar": 0.0,
            "max_drawdown": 0.0,
            "volatility": 0.0,
            "risk_contributions": [],
            "stress_tests": [],
        }

    values = df["trade_value_usd"].values.astype(float)
    returns = _monthly_returns(values)

    if len(returns) < 3:
        return {
            "confidence_level": confidence_level,
            "var_historical": 0.0,
            "var_parametric": 0.0,
            "cvar": 0.0,
            "max_drawdown": 0.0,
            "volatility": 0.0,
            "risk_contributions": [],
            "stress_tests": [],
        }

    alpha = 1.0 - confidence_level

    # --- Historical VaR ---
    var_hist = float(-np.percentile(returns, alpha * 100))

    # --- Parametric VaR (normal distribution) ---
    mu = float(np.mean(returns))
    sigma = float(np.std(returns, ddof=1))
    z = stats.norm.ppf(alpha)
    var_param = float(-(mu + z * sigma))

    # --- CVaR (Expected Shortfall) ---
    threshold = np.percentile(returns, alpha * 100)
    tail = returns[returns <= threshold]
    cvar = float(-np.mean(tail)) if len(tail) > 0 else var_hist

    # --- Max Drawdown ---
    cummax = np.maximum.accumulate(values)
    drawdowns = (values - cummax) / np.where(cummax > 0, cummax, 1.0)
    max_dd = float(-np.min(drawdowns))

    # --- Volatility (annualized) ---
    vol_monthly = float(np.std(returns, ddof=1))
    vol_annual = vol_monthly * np.sqrt(12)

    # --- Stress Tests ---
    stress_tests = _run_stress_tests(values, returns)

    # --- Risk Contributions (by country/product) ---
    risk_contrib = _compute_risk_contributions(trade_data)

    return {
        "confidence_level": confidence_level,
        "var_historical": round(var_hist, 4),
        "var_parametric": round(var_param, 4),
        "cvar": round(cvar, 4),
        "max_drawdown": round(max_dd, 4),
        "volatility": round(vol_annual, 4),
        "var_absolute_usd": round(var_hist * float(np.mean(values)), 2),
        "risk_contributions": risk_contrib,
        "stress_tests": stress_tests,
        "description": (
            f"在{confidence_level*100:.0f}%置信度下，"
            f"贸易额月度波动最大预期损失为{var_hist*100:.1f}%。"
            f"年化波动率为{vol_annual*100:.1f}%。"
        ),
    }


def _run_stress_tests(values: np.ndarray, returns: np.ndarray) -> list[dict]:
    """Run predefined stress scenarios."""
    mean_val = float(np.mean(values))
    std_val = float(np.std(values)) if len(values) > 1 else mean_val * 0.1

    scenarios = [
        {"name": "金融危机", "name_en": "Financial Crisis", "return_shock": -0.30, "description": "类似2008年金融危机的贸易冲击"},
        {"name": "贸易战", "name_en": "Trade War", "return_shock": -0.20, "description": "关税战导致贸易大幅下降"},
        {"name": "疫情冲击", "name_en": "Pandemic Shock", "return_shock": -0.25, "description": "类似COVID-19的供应链中断"},
        {"name": "繁荣期", "name_en": "Boom Period", "return_shock": 0.25, "description": "贸易快速增长的乐观情景"},
        {"name": "温和衰退", "name_en": "Mild Recession", "return_shock": -0.10, "description": "经济温和放缓"},
    ]

    results = []
    for s in scenarios:
        impact = mean_val * s["return_shock"]
        new_val = mean_val + impact
        results.append({
            "name": s["name"],
            "name_en": s["name_en"],
            "shock_pct": s["return_shock"] * 100,
            "impact_usd": round(impact, 2),
            "resulting_value": round(max(0, new_val), 2),
            "description": s["description"],
        })

    return results


def _compute_risk_contributions(trade_data: list) -> list[dict]:
    """Compute risk contributions by partner country."""
    df = pd.DataFrame(trade_data)
    if df.empty or "partner" not in df.columns or "trade_value_usd" not in df.columns:
        return []

    # Compute contribution by country
    by_partner = df.groupby("partner")["trade_value_usd"].agg(["sum", "std", "count"]).reset_index()
    total = by_partner["sum"].sum()
    if total <= 0:
        return []

    results = []
    for _, row in by_partner.iterrows():
        weight = row["sum"] / total
        volatility = row["std"] / row["sum"] if row["sum"] > 0 else 0
        results.append({
            "partner": row["partner"],
            "weight": round(weight, 4),
            "volatility": round(_safe_float(volatility), 4),
            "risk_contribution": round(weight * _safe_float(volatility), 4),
            "trade_value": round(row["sum"], 2),
        })

    results.sort(key=lambda x: x["risk_contribution"], reverse=True)
    return results[:10]
