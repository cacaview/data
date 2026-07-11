"""Integration tests for datasources routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestDatasourceStatus:
    """Test datasource status endpoint."""

    def test_datasource_status(self, client: TestClient):
        response = client.get("/api/datasources/status")
        assert response.status_code == 200
        data = response.json()
        assert "total_sources" in data
        assert "active" in data
        assert "sources" in data

    def test_datasource_status_structure(self, client: TestClient):
        response = client.get("/api/datasources/status")
        data = response.json()
        if data["sources"]:
            source = data["sources"][0]
            assert "name" in source
            assert "type" in source
            assert "status" in source


class TestDatasourceExchangeRates:
    """Test exchange rates endpoint."""

    def test_exchange_rates(self, client: TestClient):
        response = client.get("/api/datasources/exchange-rates")
        assert response.status_code in [200, 503]


class TestDatasourceMacro:
    """Test macro profile endpoint."""

    def test_macro_profile_china(self, client: TestClient):
        response = client.get("/api/datasources/macro/CHN")
        assert response.status_code in [200, 503]

    def test_macro_profile_vietnam(self, client: TestClient):
        response = client.get("/api/datasources/macro/VNM")
        assert response.status_code in [200, 503]


class TestDatasourceCommodity:
    """Test commodity prices endpoint."""

    def test_commodity_prices(self, client: TestClient):
        response = client.get("/api/datasources/commodity-prices")
        assert response.status_code in [200, 503]


class TestDatasourceRefresh:
    """Test data refresh endpoint."""

    def test_refresh_data(self, client: TestClient):
        response = client.post("/api/datasources/refresh")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert data["status"] == "success"


class TestDatasourceComtrade:
    """Test Comtrade summary endpoint."""

    def test_comtrade_summary(self, client: TestClient):
        response = client.get("/api/datasources/comtrade/summary")
        assert response.status_code in [200, 503]


class TestDatasourceIMFValidation:
    """Test IMF validation endpoint."""

    def test_imf_validation(self, client: TestClient):
        response = client.get("/api/datasources/imf-validation?partner=VNM&year=2023")
        assert response.status_code in [200, 400, 503]
