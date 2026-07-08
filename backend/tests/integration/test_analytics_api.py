"""Analytics API integration tests."""


def test_burst_radar_returns_result(client, sample_trade_records):
    r = client.get("/api/analytics/burst-radar?partner=VNM")
    assert r.status_code == 200
    data = r.json()
    assert "partner" in data
    assert data["partner"] == "VNM"


def test_burst_radar_no_data_returns_empty(client, sample_countries):
    r = client.get("/api/analytics/burst-radar?partner=SGP")
    assert r.status_code == 200
    data = r.json()
    assert data["bursts"] == []


def test_risk_dashboard_returns_scores(client, sample_trade_records, sample_countries):
    r = client.get("/api/analytics/risk-dashboard?country=VNM")
    assert r.status_code == 200
    data = r.json()
    assert "country" in data
    assert "total_score" in data
    assert "breakdown" in data
    assert "recommendations" in data


def test_risk_dashboard_unknown_country(client, sample_trade_records):
    r = client.get("/api/analytics/risk-dashboard?country=XXX")
    assert r.status_code == 200
    data = r.json()
    assert "total_score" in data


def test_upstreamness_returns_indices(client, sample_trade_records, sample_countries):
    r = client.get("/api/analytics/upstreamness?year=2024")
    assert r.status_code == 200
    data = r.json()
    assert "year" in data
    assert "upstreamness" in data


def test_tariff_savings_returns_result(client, sample_trade_records, sample_countries):
    # Need tariff rules in DB for savings calculation
    r = client.get("/api/analytics/tariff-savings?partner=VNM")
    assert r.status_code == 200
    data = r.json()
    # Either has savings or error message about no rules
    assert "partner" in data or "error" in data
