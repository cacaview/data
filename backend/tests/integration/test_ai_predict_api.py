"""Integration tests for AI prediction routes."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestAIPrediction:
    """Test AI prediction endpoint."""

    def test_prediction_default(self, client: TestClient):
        response = client.get("/api/ai/prediction")
        assert response.status_code == 200
        data = response.json()
        assert "model_name" in data
        assert "mape" in data
        assert "data" in data

    def test_prediction_with_country(self, client: TestClient):
        response = client.get("/api/ai/prediction?country=VNM")
        assert response.status_code == 200
        data = response.json()
        assert "model_name" in data

    def test_prediction_with_product(self, client: TestClient):
        response = client.get("/api/ai/prediction?product=Electronics")
        assert response.status_code == 200

    def test_prediction_data_structure(self, client: TestClient):
        response = client.get("/api/ai/prediction")
        data = response.json()
        if data["data"]:
            point = data["data"][0]
            assert "date" in point
            assert "actual" in point or "predicted" in point

    def test_prediction_with_both_filters(self, client: TestClient):
        response = client.get("/api/ai/prediction?country=VNM&product=Electronics")
        assert response.status_code == 200

    def test_prediction_with_sample_data(self, client: TestClient, sample_trade_records):
        response = client.get("/api/ai/prediction?country=VNM")
        assert response.status_code == 200
        data = response.json()
        assert "model_name" in data


class TestAIClusters:
    """Test K-Means clustering endpoint."""

    def test_clusters_default(self, client: TestClient):
        response = client.get("/api/ai/clustering")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_clusters_with_k(self, client: TestClient):
        response = client.get("/api/ai/clustering?k=3")
        assert response.status_code == 200

    def test_clusters_structure(self, client: TestClient):
        response = client.get("/api/ai/clustering")
        data = response.json()
        if data:
            cluster = data[0]
            assert "cluster" in cluster
            assert "cluster_label" in cluster
            assert "hs_code" in cluster

    def test_clusters_with_sample_data(self, client: TestClient, sample_trade_records):
        response = client.get("/api/ai/clustering?k=2")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestAIRiskAlerts:
    """Test risk alerts endpoint."""

    def test_risk_alerts_default(self, client: TestClient):
        response = client.get("/api/ai/risk-alerts")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_risk_alerts_structure(self, client: TestClient):
        response = client.get("/api/ai/risk-alerts")
        data = response.json()
        if data:
            alert = data[0]
            assert "country" in alert
            assert "level" in alert
            assert "description" in alert

    def test_risk_alerts_with_sample_data(self, client: TestClient, sample_trade_records):
        response = client.get("/api/ai/risk-alerts")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
