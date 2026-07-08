"""Tariff API integration tests."""


def test_calculate_tariff_with_default_rates(client, sample_trade_records, sample_countries):
    """Tariff calc should work even without tariff rules (fallback rates)."""
    r = client.post("/api/tariff/calculate", json={
        "hs_code": "854232",
        "origin_country": "VNM",
        "target_country": "CHN",
        "value_usd": 100000,
    })
    assert r.status_code == 200
    data = r.json()
    assert "mfn_rate" in data
    assert "best_rate" in data
    assert "savings" in data
    assert "rule_of_origin" in data


def test_common_codes_returns_list(client, sample_trade_records):
    r = client.get("/api/tariff/common-codes")
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)


def test_calculate_tariff_with_tariff_rule(client, sample_trade_records, sample_countries, session):
    """When a tariff rule exists, use its rates."""
    from app.models.schemas_db import TariffRule
    rule = TariffRule(
        hs_code="854232",
        partner_country="VNM",
        mfn_rate=10.0,
        rcep_rate=5.0,
        fta_rate=3.0,
        rule_of_origin="RVC 40%",
    )
    session.add(rule)
    session.commit()

    r = client.post("/api/tariff/calculate", json={
        "hs_code": "854232",
        "origin_country": "VNM",
        "target_country": "CHN",
        "value_usd": 100000,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["mfn_rate"] == 10.0
    assert data["best_rate"] == 3.0  # FTA is best
    assert data["savings"] > 0
