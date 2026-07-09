"""Trade Strategy Backtesting Engine.

Enables scenario simulation for trade strategy decisions:
- What-if tariff changes
- FX rate shock simulation
- Demand shift scenarios
- Monte Carlo stress testing
"""
import logging
from typing import Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)


def _safe_float(v: Any) -> float:
    try:
        f = float(v)
        return f if np.isfinite(f) else 0.0
    except (TypeError, ValueError):
        return 0.0


def _trade_monthly(trade_data: list) -> pd.DataFrame:
    df = pd.DataFrame(trade_data)
    if df.empty:
        return df
    group_cols = ["year", "month"]
    if "partner" in df.columns:
        group_cols.append("partner")
    return (
        df.groupby(group_cols)["trade_value_usd"]
        .sum()
        .reset_index()
        .sort_values(["year", "month"])
    )


def run_scenario(trade_data: list, scenario: dict,
                 partner: str = None) -> dict:
    """Run a what-if scenario on trade data.

    Parameters
    ----------
    trade_data : list[dict]
        Raw trade records.
    scenario : dict
        Scenario parameters:
        - tariff_change_pct: % change in tariff rate
        - fx_change_pct: % change in exchange rate
        - demand_change_pct: % shift in demand
    partner : str
        Partner country code filter.

    Returns
    -------
    dict with baseline, simulated, impact, winners/losers, sensitivity.
    """
    monthly = _trade_monthly(trade_data)
    if monthly.empty or len(monthly) < 2:
        return {
            "scenario": scenario,
            "baseline_total": 0,
            "simulated_total": 0,
            "impact_pct": 0,
            "impact_usd": 0,
        }

    # Baseline total
    baseline_total = monthly["trade_value_usd"].sum()

    # --- Apply scenario effects ---
    # Trade elasticity estimates
    # Tariff elasticity: -1.5 (1% tariff increase → 1.5% trade decrease)
    # FX elasticity: +1.2 (1% currency depreciation → 1.2% export increase)
    # Demand elasticity: +1.0 (1% demand change → 1% trade change)

    tariff_pct = scenario.get("tariff_change_pct") or 0
    fx_pct = scenario.get("fx_change_pct") or 0
    demand_pct = scenario.get("demand_change_pct") or 0

    tariff_elasticity = -1.5
    fx_elasticity = 1.2
    demand_elasticity = 1.0

    # Combined effect
    combined_effect = (
        tariff_pct * tariff_elasticity / 100 +
        fx_pct * fx_elasticity / 100 +
        demand_pct * demand_elasticity / 100
    )

    simulated_total = baseline_total * (1 + combined_effect)
    impact_usd = simulated_total - baseline_total
    impact_pct = (impact_usd / baseline_total * 100) if baseline_total > 0 else 0

    # --- Partner-level impact ---
    partners = monthly["partner"].unique()
    winners = []
    losers = []

    for p in partners:
        p_data = monthly[monthly["partner"] == p]
        p_total = p_data["trade_value_usd"].sum()
        p_share = p_total / baseline_total if baseline_total > 0 else 0

        # Partners with higher share in affected products are more impacted
        partner_impact = p_total * combined_effect

        entry = {
            "partner": p,
            "baseline_value": round(p_total, 2),
            "simulated_value": round(p_total + partner_impact, 2),
            "impact_pct": round(combined_effect * 100, 2),
            "impact_usd": round(partner_impact, 2),
            "share": round(p_share, 4),
        }

        if partner_impact > 0:
            winners.append(entry)
        elif partner_impact < 0:
            losers.append(entry)

    winners.sort(key=lambda x: x["impact_usd"], reverse=True)
    losers.sort(key=lambda x: x["impact_usd"])

    # --- Sensitivity analysis ---
    sensitivity = []
    for shock in [-20, -10, -5, 5, 10, 20]:
        for factor_name, elasticity in [("tariff", tariff_elasticity),
                                         ("fx", fx_elasticity),
                                         ("demand", demand_elasticity)]:
            effect = shock * elasticity / 100
            sensitivity.append({
                "factor": factor_name,
                "shock_pct": shock,
                "trade_impact_pct": round(effect * 100, 2),
                "trade_impact_usd": round(baseline_total * effect, 2),
            })

    return {
        "scenario": {
            "tariff_change_pct": tariff_pct,
            "fx_change_pct": fx_pct,
            "demand_change_pct": demand_pct,
            "combined_effect_pct": round(combined_effect * 100, 2),
        },
        "baseline_total": round(baseline_total, 2),
        "simulated_total": round(simulated_total, 2),
        "impact_pct": round(impact_pct, 2),
        "impact_usd": round(impact_usd, 2),
        "winners": winners[:5],
        "losers": losers[:5],
        "sensitivity": sensitivity,
        "description": (
            f"情景模拟结果: "
            f"基准贸易额 ${baseline_total:,.0f}，"
            f"模拟后 ${simulated_total:,.0f}，"
            f"变化 {impact_pct:+.1f}% (${impact_usd:+,.0f})"
        ),
    }


def monte_carlo_simulation(trade_data: list, n_sims: int = 1000,
                           horizon_months: int = 12) -> dict:
    """Run Monte Carlo simulation on future trade values.

    Uses geometric Brownian motion with historical drift/volatility.
    """
    df = _trade_monthly(trade_data)
    if df.empty or len(df) < 6:
        return {"simulations": [], "percentiles": {}, "risk_metrics": {}}

    values = df["trade_value_usd"].values.astype(float)
    returns = np.diff(values) / np.where(np.abs(values[:-1]) > 0, np.abs(values[:-1]), 1.0)
    returns = returns[np.isfinite(returns)]

    if len(returns) < 3:
        return {"simulations": [], "percentiles": {}, "risk_metrics": {}}

    mu = np.mean(returns)
    sigma = np.std(returns, ddof=1)
    last_val = values[-1]

    # Generate simulations
    sims = np.zeros((n_sims, horizon_months))
    for i in range(n_sims):
        random_returns = np.random.normal(mu, sigma, horizon_months)
        price_path = last_val * np.cumprod(1 + random_returns)
        sims[i] = price_path

    # Percentiles
    percentiles = {}
    for p in [5, 25, 50, 75, 95]:
        percentiles[f"p{p}"] = [round(float(np.percentile(sims[:, m], p)), 2)
                                  for m in range(horizon_months)]

    # Risk metrics
    final_values = sims[:, -1]
    risk_metrics = {
        "mean": round(float(np.mean(final_values)), 2),
        "median": round(float(np.median(final_values)), 2),
        "var_95": round(float(np.percentile(final_values, 5)), 2),
        "worst_case": round(float(np.min(final_values)), 2),
        "best_case": round(float(np.max(final_values)), 2),
        "prob_decline": round(float(np.mean(final_values < last_val)), 4),
    }

    return {
        "n_simulations": n_sims,
        "horizon_months": horizon_months,
        "current_value": round(last_val, 2),
        "percentiles": percentiles,
        "risk_metrics": risk_metrics,
    }
