"""Unit tests for quantitative analytics engine modules.

Tests the pure algorithm modules that don't require database access:
- ts_models: Time series models (ARIMA, Holt-Winters, STL, etc.)
- signal_generator: Trading signals
- var_calculator: Value at Risk
- factor_engine: Multi-factor analysis
- correlation_engine: Correlation & cointegration
- portfolio_optimizer: Trade portfolio optimization
- backtest_engine: Trade strategy backtesting
"""

import numpy as np
import pytest

from app.data.backtest_engine import monte_carlo_simulation, run_scenario
from app.data.correlation_engine import compute_correlation_matrix
from app.data.factor_engine import factor_analysis_report
from app.data.portfolio_optimizer import optimize_portfolio
from app.data.signal_generator import generate_signals
from app.data.ts_models import (
    auto_arima,
    change_point_detect,
    forecast_trade_series,
    holt_winters,
    stl_decompose,
)
from app.data.var_calculator import calculate_var

# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def sample_trade_data():
    """36 months of synthetic trade data."""
    np.random.seed(42)
    return [
        {
            "year": y,
            "month": m,
            "trade_value_usd": 1_000_000 + np.random.randn() * 50_000,
            "partner": "VNM",
            "hs_code": "8471",
            "trade_flow": "export",
        }
        for y in range(2022, 2025)
        for m in range(1, 13)
    ]


@pytest.fixture
def multi_partner_data(sample_trade_data):
    """Trade data with multiple partners."""
    np.random.seed(99)
    data = []
    for p in ("VNM", "THA", "MYS"):
        for d in sample_trade_data:
            d2 = dict(d)
            d2["partner"] = p
            d2["trade_value_usd"] = float(d["trade_value_usd"] * np.random.uniform(0.3, 2.0))
            data.append(d2)
    return data


@pytest.fixture
def constant_trade_data():
    """36 months of constant-valued trade data."""
    return [
        {"year": y, "month": m, "trade_value_usd": 500_000.0,
         "partner": "VNM", "hs_code": "8471", "trade_flow": "export"}
        for y in range(2022, 2025) for m in range(1, 13)
    ]


@pytest.fixture
def single_point_data():
    """Single trade data point."""
    return [
        {"year": 2024, "month": 1, "trade_value_usd": 1_000_000,
         "partner": "VNM", "hs_code": "8471", "trade_flow": "export"},
    ]


@pytest.fixture
def short_trade_data():
    """5 months of trade data (short series)."""
    np.random.seed(42)
    return [
        {"year": 2024, "month": m,
         "trade_value_usd": 1_000_000 + np.random.randn() * 20_000,
         "partner": "VNM", "hs_code": "8471", "trade_flow": "export"}
        for m in range(1, 6)
    ]


# ── Signal Generator Tests ──────────────────────────────────────────────────


class TestSignalGenerator:
    """Tests for app.data.signal_generator."""

    def test_signal_generator_returns_action(self, sample_trade_data):
        """Signal report has action, score, confidence."""
        result = generate_signals(sample_trade_data)
        assert "action" in result
        assert result["action"] in ("BUY", "HOLD", "SELL")
        assert "composite_score" in result
        assert -100 <= result["composite_score"] <= 100
        assert "confidence" in result
        assert 0 <= result["confidence"] <= 1
        assert "signals" in result
        assert "description" in result

    def test_signal_generator_empty_data(self):
        """Empty list returns HOLD."""
        result = generate_signals([])
        assert result["action"] == "HOLD"
        assert result["confidence"] == 0.0
        assert result["composite_score"] == 0.0

    def test_signal_generator_single_point(self, single_point_data):
        """Single data point does not crash."""
        result = generate_signals(single_point_data)
        assert "action" in result
        assert result["action"] == "HOLD"  # too few points for signals

    def test_signal_generator_has_sub_signals(self, sample_trade_data):
        """Report includes all five sub-signals."""
        result = generate_signals(sample_trade_data)
        for key in ("momentum", "rsi", "mean_reversion", "breakout", "volatility"):
            assert key in result["signals"], f"Missing sub-signal: {key}"

    def test_signal_generator_history_length(self, sample_trade_data):
        """History list has one entry per month of input data."""
        result = generate_signals(sample_trade_data)
        # Data has 36 months, so history should have 36 entries
        assert len(result["history"]) == 36

    def test_signal_generator_with_filter(self, multi_partner_data):
        """Filtering by partner returns a valid report."""
        result = generate_signals(multi_partner_data, partner="THA")
        assert result["action"] in ("BUY", "HOLD", "SELL")
        assert result["confidence"] >= 0


# ── VaR Calculator Tests ────────────────────────────────────────────────────


class TestVarCalculator:
    """Tests for app.data.var_calculator."""

    def test_var_calculator_basic(self, sample_trade_data):
        """VaR result has var_historical, cvar."""
        result = calculate_var(sample_trade_data, confidence_level=0.95)
        assert "var_historical" in result
        assert "cvar" in result
        assert "var_parametric" in result
        assert "max_drawdown" in result
        assert "volatility" in result
        assert isinstance(result["var_historical"], float)
        assert isinstance(result["cvar"], float)

    def test_var_calculator_empty(self):
        """Empty list returns zeros."""
        result = calculate_var([], confidence_level=0.95)
        assert result["var_historical"] == 0.0
        assert result["var_parametric"] == 0.0
        assert result["cvar"] == 0.0
        assert result["max_drawdown"] == 0.0
        assert result["volatility"] == 0.0

    def test_var_calculator_stress_tests(self, sample_trade_data):
        """Has 5 stress scenarios."""
        result = calculate_var(sample_trade_data)
        assert "stress_tests" in result
        assert len(result["stress_tests"]) == 5
        # Verify each scenario has required fields
        for scenario in result["stress_tests"]:
            assert "name" in scenario
            assert "name_en" in scenario
            assert "shock_pct" in scenario
            assert "impact_usd" in scenario
            assert "resulting_value" in scenario

    def test_var_calculator_risk_contributions(self, multi_partner_data):
        """Risk contributions are returned for multi-partner data."""
        result = calculate_var(multi_partner_data)
        assert "risk_contributions" in result
        assert len(result["risk_contributions"]) > 0
        for rc in result["risk_contributions"]:
            assert "partner" in rc
            assert "weight" in rc
            assert "risk_contribution" in rc

    def test_var_calculator_confidence_levels(self, sample_trade_data):
        """Different confidence levels produce different VaR values."""
        var_90 = calculate_var(sample_trade_data, confidence_level=0.90)
        var_99 = calculate_var(sample_trade_data, confidence_level=0.99)
        # Higher confidence should mean higher VaR (more negative return threshold)
        # VaR is expressed as positive number representing loss
        assert var_99["var_historical"] >= var_90["var_historical"]


# ── Time Series Models Tests ────────────────────────────────────────────────


class TestTimeSeriesModels:
    """Tests for app.data.ts_models (STL, ARIMA, Holt-Winters, ensemble)."""

    def test_stl_decomposition_basic(self, sample_trade_data):
        """STL has trend, seasonal, residual."""
        # Aggregate to monthly series
        values = _aggregate_monthly(sample_trade_data)
        result = stl_decompose(values, period=12)
        assert "trend" in result
        assert "seasonal" in result
        assert "residual" in result
        assert len(result["trend"]) == len(values)
        assert len(result["seasonal"]) == len(values)
        assert len(result["residual"]) == len(values)
        assert "diagnostics" in result
        assert result["diagnostics"]["n_obs"] == len(values)

    def test_stl_decomposition_short_series(self, short_trade_data):
        """Short series handled gracefully."""
        values = _aggregate_monthly(short_trade_data)
        result = stl_decompose(values, period=12)
        # 5 points is below _MIN_STL (24), should return error/empty
        assert "error" in result or len(result["trend"]) == 0

    def test_auto_arima_basic(self, sample_trade_data):
        """Auto ARIMA returns fitted values and forecast."""
        values = _aggregate_monthly(sample_trade_data)
        result = auto_arima(values)
        assert "model" in result
        assert result["model"] == "auto_arima"
        if "error" not in result:
            assert "forecast" in result
            assert "fitted" in result
            assert len(result["fitted"]) > 0

    def test_auto_arima_short_data(self, single_point_data):
        """Short data handled gracefully."""
        values = _aggregate_monthly(single_point_data)
        result = auto_arima(values)
        assert "error" in result  # not enough data

    def test_auto_arima_constant(self, constant_trade_data):
        """Constant values handled."""
        values = _aggregate_monthly(constant_trade_data)
        result = auto_arima(values)
        assert "model" in result
        # Constant series should be handled (flat forecast)
        if "error" not in result:
            assert result.get("diagnostics", {}).get("constant_series") is True

    def test_holt_winters_basic(self, sample_trade_data):
        """Holt-Winters returns model output with forecast."""
        values = _aggregate_monthly(sample_trade_data)
        result = holt_winters(values, seasonal_periods=12)
        assert "model" in result
        assert result["model"] == "holt_winters"
        if "error" not in result:
            assert "forecast" in result
            assert len(result["forecast"]) > 0

    def test_forecast_trade_series_basic(self, sample_trade_data):
        """forecast_trade_series returns expected structure."""
        result = forecast_trade_series(
            sample_trade_data, partner="VNM", hs_code="8471", horizon=6,
        )
        assert "model_name" in result
        assert "mape" in result
        assert "data" in result
        assert len(result["data"]) > 0

    def test_forecast_trade_series_empty(self):
        """Empty data returns empty result."""
        result = forecast_trade_series([], partner="VNM", hs_code="8471")
        assert result["model_name"] == "TS-none"
        assert result["data"] == []

    def test_change_point_detect_basic(self, sample_trade_data):
        """Change point detection returns expected structure."""
        values = _aggregate_monthly(sample_trade_data)
        result = change_point_detect(values)
        assert "change_points" in result
        assert "segments" in result
        assert "diagnostics" in result


# ── Factor Engine Tests ─────────────────────────────────────────────────────


class TestFactorEngine:
    """Tests for app.data.factor_engine."""

    def test_factor_analysis_has_insights(self, sample_trade_data):
        """Returns insights list."""
        result = factor_analysis_report(sample_trade_data, partner="VNM")
        assert "insights" in result
        assert isinstance(result["insights"], list)
        assert "factors" in result
        assert "seasonal" in result
        assert "charts" in result

    def test_factor_analysis_empty(self):
        """Empty data handled gracefully."""
        result = factor_analysis_report([], partner="VNM")
        assert result["factors"] == {}
        assert result["insights"] == []
        assert result["summary"] == "No trade data available for analysis"

    def test_factor_analysis_structure(self, sample_trade_data):
        """Factor analysis returns all expected sub-factors."""
        result = factor_analysis_report(sample_trade_data)
        factors = result["factors"]
        assert "exchange_rate" in factors
        assert "seasonal" in factors
        assert "commodity_price" in factors
        assert "gdp_growth" in factors
        assert "attribution" in factors

    def test_factor_analysis_trend(self, sample_trade_data):
        """Trend direction is detected."""
        result = factor_analysis_report(sample_trade_data)
        assert "trend" in result
        assert result["trend"]["direction"] in ("rising", "declining", "stable")
        assert "strength" in result["trend"]

    def test_factor_analysis_single_point(self, single_point_data):
        """Single point does not crash."""
        result = factor_analysis_report(single_point_data)
        assert "factors" in result


# ── Correlation Engine Tests ────────────────────────────────────────────────


class TestCorrelationEngine:
    """Tests for app.data.correlation_engine."""

    def test_correlation_matrix_basic(self, multi_partner_data):
        """Matrix dimensions match entities."""
        result = compute_correlation_matrix(multi_partner_data, entities="country")
        assert "countries" in result
        assert "matrix" in result
        assert "method" in result
        n = len(result["countries"])
        if n >= 2:
            assert len(result["matrix"]) == n
            for row in result["matrix"]:
                assert len(row) == n

    def test_correlation_matrix_single_partner(self, sample_trade_data):
        """Single partner returns minimal result."""
        result = compute_correlation_matrix(sample_trade_data, entities="country")
        # Only VNM, so < 2 entities
        assert len(result["countries"]) <= 1
        # Matrix should be [[1.0]] or empty
        if result["matrix"]:
            assert result["matrix"] == [[1.0]]

    def test_correlation_matrix_empty(self):
        """Empty data returns empty result."""
        result = compute_correlation_matrix([], entities="country")
        assert result["countries"] == []
        assert result["matrix"] == []

    def test_correlation_matrix_method(self, multi_partner_data):
        """Method is recorded in output."""
        result = compute_correlation_matrix(multi_partner_data, method="spearman")
        assert result["method"] == "spearman"


# ── Portfolio Optimizer Tests ───────────────────────────────────────────────


class TestPortfolioOptimizer:
    """Tests for app.data.portfolio_optimizer."""

    def test_portfolio_optimization_basic(self, multi_partner_data):
        """Has HHI, weights."""
        result = optimize_portfolio(multi_partner_data)
        assert "hhi_current" in result
        assert "hhi_optimal" in result
        assert "weights" in result
        assert len(result["weights"]) > 0
        assert "diversification_benefit" in result
        assert "efficient_frontier" in result

    def test_portfolio_optimization_single_partner(self, sample_trade_data):
        """Single partner returns empty/minimal result."""
        result = optimize_portfolio(sample_trade_data)
        # Only 1 partner (< 2), should return defaults
        assert result["hhi_current"] == 1.0
        assert result["hhi_optimal"] == 1.0
        assert result["weights"] == []

    def test_portfolio_optimization_empty(self):
        """Empty data returns defaults."""
        result = optimize_portfolio([])
        assert result["hhi_current"] == 1.0
        assert result["weights"] == []

    def test_portfolio_optimization_weights_sum(self, multi_partner_data):
        """Optimal weights sum approximately to 1.0."""
        result = optimize_portfolio(multi_partner_data)
        if result["weights"]:
            total = sum(w["optimal_weight"] for w in result["weights"])
            assert abs(total - 1.0) < 0.05  # within 5% tolerance


# ── Backtest Engine Tests ───────────────────────────────────────────────────


class TestBacktestEngine:
    """Tests for app.data.backtest_engine."""

    def test_backtest_scenario_basic(self, sample_trade_data):
        """Has baseline, simulated, impact."""
        scenario = {"tariff_change_pct": 5.0, "fx_change_pct": 0, "demand_change_pct": 0}
        result = run_scenario(sample_trade_data, scenario)
        assert "baseline_total" in result
        assert "simulated_total" in result
        assert "impact_pct" in result
        assert "impact_usd" in result
        assert "winners" in result
        assert "losers" in result
        assert "sensitivity" in result

    def test_backtest_scenario_empty(self):
        """Empty data returns zeros."""
        scenario = {"tariff_change_pct": 5.0}
        result = run_scenario([], scenario)
        assert result["baseline_total"] == 0
        assert result["simulated_total"] == 0
        assert result["impact_pct"] == 0

    def test_backtest_scenario_tariff_effect(self, sample_trade_data):
        """Positive tariff change reduces trade (negative impact)."""
        scenario = {"tariff_change_pct": 10.0, "fx_change_pct": 0, "demand_change_pct": 0}
        result = run_scenario(sample_trade_data, scenario)
        # Tariff elasticity is -1.5, so +10% tariff -> -15% trade
        assert result["impact_pct"] < 0

    def test_backtest_monte_carlo_basic(self, sample_trade_data):
        """Monte Carlo returns simulations and risk metrics."""
        result = monte_carlo_simulation(sample_trade_data, n_sims=100, horizon_months=6)
        assert "n_simulations" in result
        assert result["n_simulations"] == 100
        assert "percentiles" in result
        assert "risk_metrics" in result
        assert len(result["percentiles"].get("p50", [])) == 6

    def test_backtest_monte_carlo_empty(self):
        """Empty data returns empty simulations."""
        result = monte_carlo_simulation([])
        assert result["simulations"] == []
        assert result["percentiles"] == {}


# ── Helpers ─────────────────────────────────────────────────────────────────


def _aggregate_monthly(trade_data: list) -> np.ndarray:
    """Aggregate trade records into a sorted monthly time series array."""
    import pandas as pd

    df = pd.DataFrame(trade_data)
    monthly = (
        df.groupby(["year", "month"])["trade_value_usd"]
        .sum()
        .reset_index()
        .sort_values(["year", "month"])
    )
    return monthly["trade_value_usd"].values.astype(float)
