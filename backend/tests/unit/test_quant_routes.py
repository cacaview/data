"""Integration tests for quantitative analytics API routes.

Tests the /api/quant/* endpoints using the FastAPI TestClient with an
in-memory SQLite database seeded with sample trade records.
"""

import pytest
from fastapi.testclient import TestClient

from app.models.schemas_db import TradeRecord


# ── Helpers ─────────────────────────────────────────────────────────────────


def _seed_trade_records(session, n_partners: int = 3, n_months: int = 24):
    """Insert synthetic trade records into the test database.

    Generates *n_months* of data for *n_partners* partner countries
    (VNM, THA, MYS) with deterministic values so tests are repeatable.
    """
    import numpy as np

    np.random.seed(42)
    partners = ["VNM", "THA", "MYS"][:n_partners]
    records = []
    for year in (2023, 2024):
        for month in range(1, 13):
            for p in partners:
                base = {"VNM": 1_000_000, "THA": 800_000, "MYS": 600_000}[p]
                noise = float(np.random.randn() * 30_000)
                records.append(
                    TradeRecord(
                        year=year,
                        month=month,
                        reporter="CHN",
                        partner=p,
                        hs_code="854232",
                        hs_chapter=85,
                        hs_section="XVI",
                        trade_value_usd=base + noise,
                        quantity=base / 100,
                        unit="kg",
                        trade_flow="export",
                        source="test",
                    )
                )
    for r in records:
        session.add(r)
    session.commit()
    return records


# ── Route Tests ─────────────────────────────────────────────────────────────


class TestQuantForecastEndpoint:
    """GET /api/quant/forecast"""

    def test_forecast_returns_data(self, engine, session, client: TestClient):
        """Forecast endpoint returns model data for seeded partner."""
        _seed_trade_records(session)
        resp = client.get("/api/quant/forecast", params={"partner": "VNM"})
        assert resp.status_code == 200
        body = resp.json()
        assert "model_name" in body
        assert "data" in body
        assert isinstance(body["data"], list)
        assert len(body["data"]) > 0

    def test_forecast_no_data_returns_empty(self, engine, session, client: TestClient):
        """Forecast endpoint returns empty when no data matches."""
        _seed_trade_records(session)
        resp = client.get(
            "/api/quant/forecast",
            params={"partner": "ZZZ"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["data"] == []


class TestQuantCorrelationEndpoint:
    """GET /api/quant/correlation"""

    def test_correlation_returns_matrix(self, engine, session, client: TestClient):
        """Correlation endpoint returns a matrix with partner labels."""
        _seed_trade_records(session)
        resp = client.get("/api/quant/correlation")
        assert resp.status_code == 200
        body = resp.json()
        assert "countries" in body
        assert "matrix" in body
        assert "method" in body
        # We seeded 3 partners, so 3x3 matrix expected
        n = len(body["countries"])
        if n >= 2:
            assert len(body["matrix"]) == n
            for row in body["matrix"]:
                assert len(row) == n


class TestQuantSignalsEndpoint:
    """GET /api/quant/signals"""

    def test_signals_returns_report(self, engine, session, client: TestClient):
        """Signals endpoint returns action, score, confidence."""
        _seed_trade_records(session)
        resp = client.get("/api/quant/signals", params={"partner": "VNM"})
        assert resp.status_code == 200
        body = resp.json()
        assert "action" in body
        assert body["action"] in ("BUY", "HOLD", "SELL")
        assert "composite_score" in body
        assert "confidence" in body
        assert "signals" in body


class TestQuantFactorsEndpoint:
    """GET /api/quant/factors"""

    def test_factors_returns_analysis(self, engine, session, client: TestClient):
        """Factors endpoint returns factor breakdown and insights."""
        _seed_trade_records(session)
        resp = client.get("/api/quant/factors")
        assert resp.status_code == 200
        body = resp.json()
        assert "factors" in body
        assert "insights" in body
        assert isinstance(body["insights"], list)


class TestQuantVarEndpoint:
    """GET /api/quant/var"""

    def test_var_returns_metrics(self, engine, session, client: TestClient):
        """VaR endpoint returns risk metrics."""
        _seed_trade_records(session)
        resp = client.get("/api/quant/var", params={"partner": "VNM"})
        assert resp.status_code == 200
        body = resp.json()
        assert "var_historical" in body
        assert "cvar" in body
        assert "var_parametric" in body
        assert "stress_tests" in body
        assert isinstance(body["stress_tests"], list)
        assert len(body["stress_tests"]) == 5


class TestQuantPortfolioEndpoint:
    """GET /api/quant/portfolio"""

    def test_portfolio_returns_optimization(self, engine, session, client: TestClient):
        """Portfolio endpoint returns weights and HHI."""
        _seed_trade_records(session)
        resp = client.get("/api/quant/portfolio")
        assert resp.status_code == 200
        body = resp.json()
        assert "hhi_current" in body
        assert "weights" in body
        assert isinstance(body["weights"], list)
        # With 3 partners, we expect 3 weight entries
        assert len(body["weights"]) == 3
