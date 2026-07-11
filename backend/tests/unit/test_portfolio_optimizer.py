"""Tests for portfolio optimizer."""

from __future__ import annotations

import pytest
from app.data.portfolio_optimizer import optimize_portfolio, _partner_monthly_matrix, _safe_float


class TestSafeFloat:
    def test_normal_value(self):
        assert _safe_float(3.14) == 3.14

    def test_string_number(self):
        assert _safe_float("2.5") == 2.5

    def test_none_returns_zero(self):
        assert _safe_float(None) == 0.0

    def test_nan_returns_zero(self):
        import math
        assert _safe_float(float('nan')) == 0.0

    def test_inf_returns_zero(self):
        assert _safe_float(float('inf')) == 0.0

    def test_invalid_string(self):
        assert _safe_float("abc") == 0.0


class TestPartnerMonthlyMatrix:
    def test_empty_data(self):
        result = _partner_monthly_matrix([])
        assert result.empty

    def test_no_partner_column(self):
        result = _partner_monthly_matrix([{"year": 2023, "month": 1, "value": 100}])
        assert result.empty

    def test_valid_data(self):
        data = [
            {"year": 2023, "month": 1, "partner": "VNM", "trade_value_usd": 1000},
            {"year": 2023, "month": 1, "partner": "THA", "trade_value_usd": 2000},
            {"year": 2023, "month": 2, "partner": "VNM", "trade_value_usd": 1500},
            {"year": 2023, "month": 2, "partner": "THA", "trade_value_usd": 2500},
        ]
        result = _partner_monthly_matrix(data)
        assert not result.empty
        assert "VNM" in result.columns
        assert "THA" in result.columns


class TestOptimizePortfolio:
    def test_empty_data(self):
        result = optimize_portfolio([])
        assert result["hhi_current"] == 1.0
        assert result["weights"] == []

    def test_single_partner(self):
        data = [
            {"year": 2023, "month": i, "partner": "VNM", "trade_value_usd": 1000 * i}
            for i in range(1, 13)
        ]
        result = optimize_portfolio(data)
        assert result["hhi_current"] == 1.0

    def test_multiple_partners(self):
        data = []
        for m in range(1, 13):
            data.append({"year": 2023, "month": m, "partner": "VNM", "trade_value_usd": 1000000 * (1 + m * 0.1)})
            data.append({"year": 2023, "month": m, "partner": "THA", "trade_value_usd": 800000 * (1 + m * 0.05)})
            data.append({"year": 2023, "month": m, "partner": "IDN", "trade_value_usd": 600000 * (1 + m * 0.08)})
        result = optimize_portfolio(data)
        assert "hhi_current" in result
        assert "hhi_optimal" in result
        assert "weights" in result
        assert len(result["weights"]) == 3
        assert "efficient_frontier" in result
        assert "optimal_sharpe" in result
        assert "diversification_benefit" in result
