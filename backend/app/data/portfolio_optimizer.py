"""Trade Portfolio Optimization.

Applies Modern Portfolio Theory (Markowitz) to trade partner allocation:
- Computes optimal weights to minimize concentration risk
- Generates efficient frontier
- Provides diversification benefit metrics
"""
import logging
from typing import Any

import numpy as np
import pandas as pd
from scipy.optimize import minimize

logger = logging.getLogger(__name__)


def _safe_float(v: Any) -> float:
    try:
        f = float(v)
        return f if np.isfinite(f) else 0.0
    except (TypeError, ValueError):
        return 0.0


def _partner_monthly_matrix(trade_data: list) -> pd.DataFrame:
    """Create partner x month pivot table."""
    df = pd.DataFrame(trade_data)
    if df.empty or "partner" not in df.columns:
        return pd.DataFrame()
    monthly = (
        df.groupby(["year", "month", "partner"])["trade_value_usd"]
        .sum()
        .reset_index()
    )
    monthly["_sort_key"] = monthly["year"].astype(int) * 100 + monthly["month"].astype(int)
    pivot = monthly.pivot_table(
        index="_sort_key", columns="partner", values="trade_value_usd", fill_value=0
    )
    return pivot.sort_index()


def optimize_portfolio(trade_data: list, min_weight: float = 0.02,
                       max_weight: float = 0.50) -> dict:
    """Optimize trade portfolio for diversification.

    Parameters
    ----------
    trade_data : list[dict]
        Raw trade records.
    min_weight : float
        Minimum allocation per partner.
    max_weight : float
        Maximum allocation per partner.

    Returns
    -------
    dict with weights, efficient_frontier, HHI metrics.
    """
    pivot = _partner_monthly_matrix(trade_data)
    if pivot.empty or pivot.shape[1] < 2:
        return {
            "hhi_current": 1.0,
            "hhi_optimal": 1.0,
            "weights": [],
            "efficient_frontier": [],
            "optimal_sharpe": 0.0,
            "diversification_benefit": 0.0,
        }

    partners = list(pivot.columns)
    n = len(partners)
    returns_df = pivot.pct_change().dropna()
    returns = returns_df.values

    if returns.shape[0] < 2:
        return _empty_result(partners, pivot)

    # --- Current weights ---
    total_value = pivot.iloc[-1].values
    total = total_value.sum()
    current_weights = total_value / total if total > 0 else np.ones(n) / n

    # --- Statistics ---
    mean_returns = np.mean(returns, axis=0)
    cov_matrix = np.cov(returns, rowvar=False) * 12  # Annualized
    if cov_matrix.ndim == 0:
        cov_matrix = np.array([[float(cov_matrix)]])

    # Ensure positive definite
    eigvals = np.linalg.eigvalsh(cov_matrix)
    if np.min(eigvals) < 1e-8:
        cov_matrix += np.eye(n) * 1e-6

    # --- Current HHI ---
    hhi_current = float(np.sum(current_weights ** 2))

    # --- Optimize: Maximize Sharpe Ratio ---
    def neg_sharpe(w):
        port_return = np.dot(w, mean_returns) * 12
        port_vol = np.sqrt(np.dot(w, np.dot(cov_matrix, w)))
        if port_vol < 1e-10:
            return 1e10
        return -(port_return / port_vol)

    constraints = [{"type": "eq", "fun": lambda w: np.sum(w) - 1.0}]
    bounds = [(min_weight, max_weight)] * n
    w0 = np.ones(n) / n

    try:
        result = minimize(
            neg_sharpe, w0, method="SLSQP",
            bounds=bounds, constraints=constraints,
            options={"maxiter": 500, "ftol": 1e-12},
        )
        optimal_weights = result.x if result.success else current_weights
    except Exception:
        optimal_weights = current_weights

    hhi_optimal = float(np.sum(optimal_weights ** 2))

    # --- Efficient Frontier ---
    frontier = _compute_efficient_frontier(mean_returns, cov_matrix, n, bounds)

    # --- Weight comparison ---
    weights = []
    for i, partner in enumerate(partners):
        weights.append({
            "name": partner,
            "current_weight": round(_safe_float(current_weights[i]), 4),
            "optimal_weight": round(_safe_float(optimal_weights[i]), 4),
            "trade_value": round(_safe_float(total_value[i]), 2),
            "risk_contribution": round(
                _safe_float(optimal_weights[i] * np.sqrt(cov_matrix[i, i])),
                4,
            ),
        })

    weights.sort(key=lambda x: x["optimal_weight"], reverse=True)

    # Optimal Sharpe
    opt_return = np.dot(optimal_weights, mean_returns) * 12
    opt_vol = np.sqrt(np.dot(optimal_weights, np.dot(cov_matrix, optimal_weights)))
    opt_sharpe = opt_return / opt_vol if opt_vol > 1e-10 else 0.0

    diversification = hhi_current - hhi_optimal

    return {
        "hhi_current": round(hhi_current, 4),
        "hhi_optimal": round(hhi_optimal, 4),
        "n_partners": n,
        "weights": weights,
        "efficient_frontier": frontier,
        "optimal_sharpe": round(_safe_float(opt_sharpe), 4),
        "diversification_benefit": round(_safe_float(diversification), 4),
        "description": (
            f"当前HHI集中度指数: {hhi_current:.4f}，"
            f"优化后: {hhi_optimal:.4f}。"
            f"多元化收益: {diversification:.4f}。"
        ),
    }


def _compute_efficient_frontier(mean_returns, cov_matrix, n, bounds,
                                n_points: int = 20) -> list[dict]:
    """Compute points on the efficient frontier."""
    target_returns = np.linspace(
        np.min(mean_returns) * 12, np.max(mean_returns) * 12, n_points
    )
    frontier = []

    for target in target_returns:
        def portfolio_vol(w):
            return np.sqrt(np.dot(w, np.dot(cov_matrix, w)))

        constraints = [
            {"type": "eq", "fun": lambda w: np.sum(w) - 1.0},
            {"type": "eq", "fun": lambda w, t=target: np.dot(w, mean_returns) * 12 - t},
        ]
        w0 = np.ones(n) / n

        try:
            res = minimize(
                portfolio_vol, w0, method="SLSQP",
                bounds=bounds, constraints=constraints,
                options={"maxiter": 300, "ftol": 1e-10},
            )
            if res.success:
                vol = float(res.fun)
                sharpe = target / vol if vol > 1e-10 else 0.0
                frontier.append({
                    "risk": round(vol, 4),
                    "return_rate": round(target, 4),
                    "sharpe_ratio": round(sharpe, 4),
                })
        except Exception:
            continue

    return frontier


def _empty_result(partners, pivot):
    weights = []
    for p in partners:
        val = pivot[p].iloc[-1] if p in pivot.columns else 0
        weights.append({"name": p, "current_weight": 0, "optimal_weight": 0, "trade_value": round(val, 2)})
    return {
        "hhi_current": 1.0, "hhi_optimal": 1.0,
        "weights": weights, "efficient_frontier": [],
        "optimal_sharpe": 0.0, "diversification_benefit": 0.0,
    }
