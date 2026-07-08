"""Trade API integration tests (end-to-end through HTTP)."""


def test_trend_returns_points_with_country_names(client, sample_trade_records):
    r = client.get("/api/trade/trend?countries=VNM")
    assert r.status_code == 200
    points = r.json()
    assert isinstance(points, list)
    assert points
    assert all("date" in p and "value" in p and "country" in p for p in points)
    assert all(p["country"] == "越南" for p in points)


def test_trend_filters_by_year(client, sample_trade_records):
    r = client.get("/api/trade/trend?start_year=2024&end_year=2024")
    assert r.status_code == 200
    assert all(p["date"].startswith("2024") for p in r.json())


def test_country_compare_returns_radars(client, sample_trade_records, sample_countries):
    r = client.get("/api/trade/country-compare")
    assert r.status_code == 200
    radars = r.json()
    countries = {radar["country"] for radar in radars}
    assert {"越南", "泰国", "印度尼西亚"} <= countries


def test_ranking_country_default(client, sample_trade_records):
    r = client.get("/api/trade/ranking")
    assert r.status_code == 200
    items = r.json()
    assert items
    # Descending by value
    for a, b in zip(items, items[1:], strict=False):
        assert a["value"] >= b["value"]


def test_ranking_type_validation(client, sample_trade_records):
    """Invalid type must be rejected with 422."""
    r = client.get("/api/trade/ranking?type=invalid")
    assert r.status_code == 422
    body = r.json()
    assert body["error_code"] == "VALIDATION_ERROR"
    assert "request_id" in body


def test_ranking_limit_bounds(client, sample_trade_records):
    """limit must be 1-50."""
    r1 = client.get("/api/trade/ranking?limit=0")
    assert r1.status_code == 422
    r2 = client.get("/api/trade/ranking?limit=51")
    assert r2.status_code == 422


def test_sankey_returns_structure(client, sample_trade_records):
    r = client.get("/api/trade/sankey?year=2024")
    assert r.status_code == 200
    data = r.json()
    assert "nodes" in data
    assert "links" in data
    if data["links"]:
        node_names = {n["name"] for n in data["nodes"]}
        for link in data["links"]:
            assert link["source"] in node_names
            assert link["target"] in node_names


def test_sankey_empty_year_returns_empty_sankey(client, sample_trade_records):
    r = client.get("/api/trade/sankey?year=1990")
    assert r.status_code == 200
    data = r.json()
    assert data == {"nodes": [], "links": []}


def test_sankey_missing_year_param_rejected(client, sample_trade_records):
    r = client.get("/api/trade/sankey")
    assert r.status_code == 422
