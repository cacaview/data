"""Integration tests for enterprise routes."""

from __future__ import annotations

from fastapi.testclient import TestClient


class TestEnterpriseRiskMonitor:
    """Test risk monitor endpoint."""

    def test_risk_monitor_default_year(self, client: TestClient):
        """Test risk monitor with default year."""
        response = client.get("/api/enterprise/risk-monitor")
        assert response.status_code == 200
        data = response.json()
        assert "year" in data
        assert "total_partners" in data
        assert "high_risk_count" in data
        assert "countries" in data

    def test_risk_monitor_specific_year(self, client: TestClient):
        """Test risk monitor with specific year."""
        response = client.get("/api/enterprise/risk-monitor?year=2024")
        assert response.status_code == 200
        data = response.json()
        assert data["year"] == 2024

    def test_risk_monitor_country_structure(self, client: TestClient):
        """Test risk monitor returns correct country structure."""
        response = client.get("/api/enterprise/risk-monitor")
        data = response.json()
        if data["countries"]:
            country = data["countries"][0]
            assert "country" in country
            assert "country_name" in country
            assert "risk_score" in country
            assert "risk_level" in country
            assert "risk_factors" in country
            assert country["risk_level"] in ["high", "medium", "low"]


class TestEnterpriseCompliance:
    """Test compliance screening endpoint."""

    def test_compliance_clear(self, client: TestClient):
        """Test compliance check for clear entity."""
        response = client.get("/api/enterprise/compliance?entity_name=SafeTrade Inc")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "clear"
        assert data["risk_level"] == "low"

    def test_compliance_flagged_exact(self, client: TestClient):
        """Test compliance check for exact match on sanctions list."""
        response = client.get("/api/enterprise/compliance?entity_name=global trade corp")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "flagged"
        assert data["risk_level"] == "critical"
        assert data["match_type"] == "exact"

    def test_compliance_flagged_partial(self, client: TestClient):
        """Test compliance check for partial match."""
        response = client.get("/api/enterprise/compliance?entity_name=global trade")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "flagged"
        assert data["match_type"] == "partial"


class TestEnterpriseCostOptimizer:
    """Test cost optimizer endpoint."""

    def test_cost_optimizer_default(self, client: TestClient):
        """Test cost optimizer with default parameters."""
        response = client.get("/api/enterprise/cost-optimizer")
        assert response.status_code == 200
        data = response.json()
        assert "comparisons" in data

    def test_cost_optimizer_with_hs_code(self, client: TestClient):
        """Test cost optimizer with HS code filter."""
        response = client.get("/api/enterprise/cost-optimizer?hs_code=0101")
        assert response.status_code == 200

    def test_cost_optimizer_with_partners(self, client: TestClient):
        """Test cost optimizer with specific partners."""
        response = client.get("/api/enterprise/cost-optimizer?partners=VNM,THA")
        assert response.status_code == 200

    def test_cost_optimizer_structure(self, client: TestClient):
        """Test cost optimizer returns correct structure."""
        response = client.get("/api/enterprise/cost-optimizer")
        data = response.json()
        if data["comparisons"]:
            comparison = data["comparisons"][0]
            assert "hs_code" in comparison
            assert "partner" in comparison
            assert "mfn_rate" in comparison


class TestEnterpriseSupplyChainMap:
    """Test supply chain map endpoint."""

    def test_supply_chain_map(self, client: TestClient):
        """Test supply chain map data."""
        response = client.get("/api/enterprise/supply-chain-map")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
        assert "year" in data

    def test_supply_chain_map_structure(self, client: TestClient):
        """Test supply chain map returns correct structure."""
        response = client.get("/api/enterprise/supply-chain-map")
        data = response.json()
        assert "year" in data
        assert "total_trade_flows" in data


class TestEnterpriseComprehensive:
    """Comprehensive tests for all enterprise endpoints."""

    def test_risk_monitor_with_data(self, client: TestClient, sample_trade_records):
        """Test risk monitor with sample data."""
        response = client.get("/api/enterprise/risk-monitor?year=2023")
        assert response.status_code == 200
        data = response.json()
        assert data["year"] == 2023

    def test_compliance_with_data(self, client: TestClient, sample_trade_records):
        """Test compliance with sample data."""
        response = client.get("/api/enterprise/compliance?entity_name=SafeTrade Inc")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "clear"

    def test_cost_optimizer_with_data(
        self, client: TestClient, sample_trade_records, sample_tariff_rules
    ):
        """Test cost optimizer with sample data including tariff rules."""
        response = client.get("/api/enterprise/cost-optimizer?year=2023")
        assert response.status_code == 200
        data = response.json()
        assert "comparisons" in data
        if data["comparisons"]:
            comp = data["comparisons"][0]
            assert "hs_code" in comp
            assert "mfn_rate" in comp
            assert "rcep_rate" in comp
            assert "best_scheme" in comp
            assert "savings_vs_mfn_usd" in comp

    def test_cost_optimizer_with_hs_code_filter(
        self, client: TestClient, sample_trade_records, sample_tariff_rules
    ):
        """Test cost optimizer with HS code filter."""
        response = client.get("/api/enterprise/cost-optimizer?hs_code=854232&year=2023")
        assert response.status_code == 200
        data = response.json()
        assert "comparisons" in data

    def test_cost_optimizer_with_partners(
        self, client: TestClient, sample_trade_records, sample_tariff_rules
    ):
        """Test cost optimizer with specific partners."""
        response = client.get("/api/enterprise/cost-optimizer?partners=VNM,THA&year=2023")
        assert response.status_code == 200
        data = response.json()
        assert "comparisons" in data

    def test_supply_chain_map_with_data(self, client: TestClient, sample_trade_records):
        """Test supply chain map with sample data."""
        response = client.get("/api/enterprise/supply-chain-map")
        assert response.status_code == 200
        data = response.json()
        assert "nodes" in data
        assert "edges" in data
