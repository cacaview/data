"""Integration tests for quant routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestQuantForecast:
    def test_forecast_default(self, client: TestClient):
        response = client.get("/api/quant/forecast")
        assert response.status_code == 200
        data = response.json()
        assert "model_name" in data

    def test_forecast_with_partner(self, client: TestClient):
        response = client.get("/api/quant/forecast?partner=THA")
        assert response.status_code == 200

    def test_forecast_with_model(self, client: TestClient):
        response = client.get("/api/quant/forecast?model=auto_arima")
        assert response.status_code == 200

    def test_forecast_with_holt_winters(self, client: TestClient):
        response = client.get("/api/quant/forecast?model=holt_winters")
        assert response.status_code == 200

    def test_forecast_with_horizon(self, client: TestClient):
        response = client.get("/api/quant/forecast?horizon=12")
        assert response.status_code == 200

    def test_forecast_with_sample_data(self, client: TestClient, sample_trade_records):
        response = client.get("/api/quant/forecast?partner=VNM")
        assert response.status_code == 200
        data = response.json()
        assert "model_name" in data


class TestQuantCorrelation:
    def test_correlation_by_country(self, client: TestClient):
        response = client.get("/api/quant/correlation?entities=country")
        assert response.status_code == 200

    def test_correlation_by_product(self, client: TestClient):
        response = client.get("/api/quant/correlation?entities=product")
        assert response.status_code == 200

    def test_correlation_with_sample_data(self, client: TestClient, sample_trade_records):
        response = client.get("/api/quant/correlation?entities=country")
        assert response.status_code == 200

    def test_correlation_clusters(self, client: TestClient, sample_trade_records):
        response = client.get("/api/quant/correlation/clusters?n_clusters=2")
        assert response.status_code == 200
        data = response.json()
        assert "clusters" in data


class TestQuantSignals:
    def test_signals_default(self, client: TestClient):
        response = client.get("/api/quant/signals")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_signals_with_partner(self, client: TestClient):
        response = client.get("/api/quant/signals?partner=VNM")
        assert response.status_code == 200

    def test_signals_with_sample_data(self, client: TestClient, sample_trade_records):
        response = client.get("/api/quant/signals?partner=VNM")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


class TestQuantFactors:
    def test_factors_default(self, client: TestClient):
        response = client.get("/api/quant/factors")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_factors_with_partner(self, client: TestClient, sample_trade_records):
        response = client.get("/api/quant/factors?partner=VNM")
        assert response.status_code == 200

    def test_attribute_change(self, client: TestClient, sample_trade_records):
        response = client.get("/api/quant/factors/attribute?partner=VNM&start_year=2023&start_month=1&end_year=2024&end_month=12")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)


class TestQuantVaR:
    def test_var_default(self, client: TestClient):
        response = client.get("/api/quant/var")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_var_with_partner(self, client: TestClient):
        response = client.get("/api/quant/var?partner=VNM")
        assert response.status_code == 200

    def test_var_with_confidence(self, client: TestClient):
        response = client.get("/api/quant/var?confidence=0.99")
        assert response.status_code == 200

    def test_var_with_sample_data(self, client: TestClient, sample_trade_records):
        response = client.get("/api/quant/var?partner=VNM")
        assert response.status_code == 200


class TestQuantPortfolio:
    def test_portfolio_default(self, client: TestClient):
        response = client.get("/api/quant/portfolio")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_portfolio_with_sample_data(self, client: TestClient, sample_trade_records):
        response = client.get("/api/quant/portfolio")
        assert response.status_code == 200


class TestQuantBacktest:
    def test_backtest_default(self, client: TestClient):
        response = client.get("/api/quant/backtest")
        assert response.status_code in [200, 405]

    def test_backtest_with_sample_data(self, client: TestClient, sample_trade_records):
        response = client.get("/api/quant/backtest")
        assert response.status_code in [200, 405]
