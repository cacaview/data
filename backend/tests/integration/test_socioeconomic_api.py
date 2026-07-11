"""Integration tests for socioeconomic routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestSocioeconomicMacroOverview:
    """Test macro overview endpoint."""

    def test_macro_overview_default_year(self, client: TestClient):
        """Test macro overview with default year."""
        response = client.get("/api/socioeconomic/macro-overview")
        assert response.status_code == 200
        data = response.json()
        assert "year" in data
        assert "region" in data
        assert data["region"] == "ASEAN"
        assert "countries" in data
        assert "total_countries" in data

    def test_macro_overview_specific_year(self, client: TestClient):
        """Test macro overview with specific year."""
        response = client.get("/api/socioeconomic/macro-overview?year=2024")
        assert response.status_code == 200
        data = response.json()
        assert data["year"] == 2024

    def test_macro_overview_country_structure(self, client: TestClient):
        """Test macro overview returns correct country structure."""
        response = client.get("/api/socioeconomic/macro-overview")
        data = response.json()
        if data["countries"]:
            country = data["countries"][0]
            assert "country" in country
            assert "country_name" in country
            assert "gdp_billion_usd" in country
            assert "population_million" in country
            assert "trade_volume_usd" in country


class TestSocioeconomicTradeImpact:
    """Test trade impact endpoint."""

    def test_trade_impact_default(self, client: TestClient):
        """Test trade impact with default parameters."""
        response = client.get("/api/socioeconomic/trade-impact")
        assert response.status_code == 200
        data = response.json()
        assert "year" in data
        assert "countries" in data

    def test_trade_impact_structure(self, client: TestClient):
        """Test trade impact returns correct structure."""
        response = client.get("/api/socioeconomic/trade-impact")
        data = response.json()
        if data["countries"]:
            impact = data["countries"][0]
            assert "country" in impact
            assert "country_name" in impact


class TestSocioeconomicSustainability:
    """Test sustainability endpoint."""

    def test_sustainability_default(self, client: TestClient):
        """Test sustainability with default parameters."""
        response = client.get("/api/socioeconomic/sustainability")
        assert response.status_code == 200
        data = response.json()
        assert "countries" in data

    def test_sustainability_structure(self, client: TestClient):
        """Test sustainability returns correct structure."""
        response = client.get("/api/socioeconomic/sustainability")
        data = response.json()
        if data["countries"]:
            country = data["countries"][0]
            assert "country" in country
            assert "country_name" in country
            assert "esg_score" in country


class TestSocioeconomicCompetitiveness:
    """Test competitiveness endpoint."""

    def test_competitiveness_default(self, client: TestClient):
        """Test competitiveness with default parameters."""
        response = client.get("/api/socioeconomic/competitiveness")
        assert response.status_code == 200
        data = response.json()
        assert "countries" in data

    def test_competitiveness_structure(self, client: TestClient):
        """Test competitiveness returns correct structure."""
        response = client.get("/api/socioeconomic/competitiveness")
        data = response.json()
        if data["countries"]:
            country = data["countries"][0]
            assert "country" in country
            assert "country_name" in country
            assert "competitiveness_score" in country


class TestSocioeconomicComprehensive:
    """Comprehensive tests for all socioeconomic endpoints."""

    def test_macro_overview_with_data(self, client: TestClient, sample_trade_records):
        """Test macro overview with sample data."""
        response = client.get("/api/socioeconomic/macro-overview?year=2023")
        assert response.status_code == 200
        data = response.json()
        assert data["year"] == 2023
        assert data["region"] == "ASEAN"

    def test_trade_impact_with_data(self, client: TestClient, sample_trade_records):
        """Test trade impact with sample data."""
        response = client.get("/api/socioeconomic/trade-impact?year=2023")
        assert response.status_code == 200
        data = response.json()
        assert data["year"] == 2023

    def test_sustainability_with_data(self, client: TestClient, sample_trade_records):
        """Test sustainability with sample data."""
        response = client.get("/api/socioeconomic/sustainability")
        assert response.status_code == 200
        data = response.json()
        assert "countries" in data

    def test_competitiveness_with_data(self, client: TestClient, sample_trade_records):
        """Test competitiveness with sample data."""
        response = client.get("/api/socioeconomic/competitiveness")
        assert response.status_code == 200
        data = response.json()
        assert "countries" in data
