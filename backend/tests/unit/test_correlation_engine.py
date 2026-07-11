"""Tests for correlation engine."""

from __future__ import annotations

import numpy as np

from app.data.correlation_engine import (
    cluster_entities,
    cointegration_test,
    compute_correlation_matrix,
    detect_lead_lag,
    detect_regime_changes,
    full_analysis,
)


class TestCorrelationMatrix:
    def test_empty_data(self):
        result = compute_correlation_matrix([])
        assert result["countries"] == []

    def test_single_country(self):
        trade_data = [
            {"year": 2023, "month": i, "partner": "VNM", "hs_code": "01", "trade_value_usd": 100 + i * 10}
            for i in range(1, 7)
        ]
        result = compute_correlation_matrix(trade_data, entities="country")
        assert len(result["countries"]) == 1

    def test_two_countries(self):
        trade_data = [
            {"year": 2023, "month": i, "partner": "VNM", "hs_code": "01", "trade_value_usd": 100 + i * 10}
            for i in range(1, 7)
        ] + [
            {"year": 2023, "month": i, "partner": "THA", "hs_code": "01", "trade_value_usd": 200 + i * 20}
            for i in range(1, 7)
        ]
        result = compute_correlation_matrix(trade_data, entities="country")
        assert len(result["countries"]) == 2

    def test_by_product(self):
        trade_data = [
            {"year": 2023, "month": i, "partner": "VNM", "hs_code": "01", "trade_value_usd": 100 + i * 10}
            for i in range(1, 7)
        ] + [
            {"year": 2023, "month": i, "partner": "VNM", "hs_code": "02", "trade_value_usd": 200 + i * 20}
            for i in range(1, 7)
        ]
        result = compute_correlation_matrix(trade_data, entities="product")
        assert len(result["countries"]) == 2

    def test_spearman_method(self):
        trade_data = [
            {"year": 2023, "month": i, "partner": "VNM", "hs_code": "01", "trade_value_usd": 100 + i * 10}
            for i in range(1, 13)
        ] + [
            {"year": 2023, "month": i, "partner": "THA", "hs_code": "01", "trade_value_usd": 200 + i * 20}
            for i in range(1, 13)
        ]
        result = compute_correlation_matrix(trade_data, entities="country", method="spearman")
        assert result["method"] == "spearman"

    def test_invalid_method(self):
        trade_data = [
            {"year": 2023, "month": i, "partner": "VNM", "hs_code": "01", "trade_value_usd": 100 + i * 10}
            for i in range(1, 13)
        ] + [
            {"year": 2023, "month": i, "partner": "THA", "hs_code": "01", "trade_value_usd": 200 + i * 20}
            for i in range(1, 13)
        ]
        result = compute_correlation_matrix(trade_data, entities="country", method="invalid")
        assert result["method"] == "pearson"


class TestLeadLagDetection:
    def test_empty_trade_data(self):
        result = detect_lead_lag([], [{"year": 2023, "month": 1, "value": 100}])
        assert result["optimal_lag"] == 0

    def test_empty_macro_data(self):
        result = detect_lead_lag([{"year": 2023, "month": 1, "trade_value_usd": 100}], [])
        assert result["optimal_lag"] == 0

    def test_valid_data(self):
        trade_data = [{"year": 2023, "month": i, "trade_value_usd": 100 + i * 10} for i in range(1, 13)]
        macro_data = [{"year": 2023, "month": i, "value": 50 + i * 5} for i in range(1, 13)]
        result = detect_lead_lag(trade_data, macro_data, max_lag=3)
        assert "cross_correlation" in result


class TestCointegrationTest:
    def test_insufficient_data(self):
        a = np.array([1, 2, 3, 4, 5])
        b = np.array([2, 3, 4, 5, 6])
        result = cointegration_test(a, b)
        assert result["cointegrated"] is False

    def test_cointegrated_series(self):
        np.random.seed(42)
        n = 50
        b = np.cumsum(np.random.randn(n)) + 100
        a = 2 * b + np.random.randn(n) * 0.5
        result = cointegration_test(a, b)
        assert "cointegrated" in result
        assert "critical_values" in result

    def test_result_structure(self):
        np.random.seed(42)
        n = 30
        a = np.arange(n, dtype=float) + np.random.randn(n) * 0.1
        b = np.arange(n, dtype=float) * 2 + np.random.randn(n) * 0.1
        result = cointegration_test(a, b)
        assert "1%" in result["critical_values"]
        assert "5%" in result["critical_values"]
        assert "10%" in result["critical_values"]


class TestRegimeChanges:
    def test_insufficient_data(self):
        data = np.array([1, 2, 3, 4, 5])
        result = detect_regime_changes(data, min_segment=3)
        assert result["n_regimes"] == 1

    def test_constant_data(self):
        data = np.ones(50)
        result = detect_regime_changes(data, min_segment=6)
        assert result["n_regimes"] == 1

    def test_with_breakpoint(self):
        data = np.concatenate([np.ones(30) * 100, np.ones(30) * 200])
        result = detect_regime_changes(data, min_segment=6, threshold=1.5)
        assert "breakpoints" in result


class TestClusterEntities:
    def test_empty_data(self):
        result = cluster_entities([])
        assert result["clusters"] == []

    def test_insufficient_entities(self):
        trade_data = [
            {"year": 2023, "month": i, "partner": "VNM", "hs_code": "01", "trade_value_usd": 100 + i * 10}
            for i in range(1, 13)
        ]
        result = cluster_entities(trade_data, n_clusters=2)
        assert result["clusters"] == []

    def test_two_entities(self):
        trade_data = []
        for month in range(1, 13):
            trade_data.append({"year": 2023, "month": month, "partner": "VNM", "hs_code": "01", "trade_value_usd": 100 + month * 10})
            trade_data.append({"year": 2023, "month": month, "partner": "THA", "hs_code": "01", "trade_value_usd": 200 + month * 20})
        result = cluster_entities(trade_data, n_clusters=2, entities="country")
        assert "clusters" in result
        assert "method" in result

    def test_three_entities(self):
        trade_data = []
        for month in range(1, 13):
            trade_data.append({"year": 2023, "month": month, "partner": "VNM", "hs_code": "01", "trade_value_usd": 100 + month * 10})
            trade_data.append({"year": 2023, "month": month, "partner": "THA", "hs_code": "01", "trade_value_usd": 200 + month * 20})
            trade_data.append({"year": 2023, "month": month, "partner": "MYS", "hs_code": "01", "trade_value_usd": 150 + month * 15})
        result = cluster_entities(trade_data, n_clusters=2, entities="country")
        assert len(result["clusters"]) > 0

    def test_by_product(self):
        trade_data = []
        for month in range(1, 13):
            trade_data.append({"year": 2023, "month": month, "partner": "VNM", "hs_code": "01", "trade_value_usd": 100 + month * 10})
            trade_data.append({"year": 2023, "month": month, "partner": "VNM", "hs_code": "02", "trade_value_usd": 200 + month * 20})
            trade_data.append({"year": 2023, "month": month, "partner": "VNM", "hs_code": "03", "trade_value_usd": 150 + month * 15})
        result = cluster_entities(trade_data, n_clusters=2, entities="product")
        assert "clusters" in result


class TestFullAnalysis:
    def test_empty_data(self):
        result = full_analysis([])
        assert "analyses" in result
        assert "summary" in result

    def test_with_trade_data(self):
        trade_data = []
        for month in range(1, 13):
            trade_data.append({"year": 2023, "month": month, "partner": "VNM", "hs_code": "01", "trade_value_usd": 100 + month * 10})
            trade_data.append({"year": 2023, "month": month, "partner": "THA", "hs_code": "01", "trade_value_usd": 200 + month * 20})
        result = full_analysis(trade_data)
        assert "analyses" in result
        assert "correlation_country" in result["analyses"]
        assert "correlation_product" in result["analyses"]

    def test_with_macro_data(self):
        trade_data = []
        macro_data = []
        for month in range(1, 13):
            trade_data.append({"year": 2023, "month": month, "partner": "VNM", "hs_code": "01", "trade_value_usd": 100 + month * 10})
            macro_data.append({"year": 2023, "month": month, "value": 50 + month * 5})
        result = full_analysis(trade_data, macro_data=macro_data)
        assert "lead_lag" in result["analyses"]
