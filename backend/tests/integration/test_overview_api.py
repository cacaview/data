"""Overview API integration tests."""


def test_summary_returns_kpi(client, sample_trade_records):
    r = client.get("/api/overview/summary")
    assert r.status_code == 200
    data = r.json()
    assert "total_trade_value" in data
    assert "yoy_growth" in data
    assert "partner_count" in data
    assert "top_partners" in data
    assert "monthly_trend" in data
    assert "top_growth_products" in data
    assert "rcep_utilization" in data


def test_trade_map_returns_points_and_arcs(client, sample_trade_records, sample_countries):
    r = client.get("/api/overview/trade-map")
    assert r.status_code == 200
    data = r.json()
    assert "points" in data
    assert "arcs" in data


def test_sankey_returns_nodes_and_links(client, sample_trade_records):
    r = client.get("/api/overview/sankey")
    assert r.status_code == 200
    data = r.json()
    assert "nodes" in data
    assert "links" in data


def test_trend_mini_returns_points(client, sample_trade_records):
    r = client.get("/api/overview/trend-mini")
    assert r.status_code == 200
    points = r.json()
    assert isinstance(points, list)
    if points:
        assert "date" in points[0]
        assert "value" in points[0]
