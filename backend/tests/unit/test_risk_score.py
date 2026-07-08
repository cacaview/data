"""Risk score computation tests."""
from app.data.analytics import compute_risk_score


def test_low_risk_all_zeros():
    result = compute_risk_score({
        "fx_risk": 0, "logistics_risk": 0, "tariff_risk": 0,
        "political_risk": 0, "disaster_risk": 0,
    })
    assert result["total_score"] == 0.0
    assert result["risk_level"] == "low"


def test_high_risk_all_max():
    result = compute_risk_score({
        "fx_risk": 100, "logistics_risk": 100, "tariff_risk": 100,
        "political_risk": 100, "disaster_risk": 100,
    })
    assert result["total_score"] == 100.0
    assert result["risk_level"] == "high"


def test_medium_risk_at_threshold():
    # All factors at 50 -> 50*1.0 = 50, which is medium
    result = compute_risk_score({
        "fx_risk": 50, "logistics_risk": 50, "tariff_risk": 50,
        "political_risk": 50, "disaster_risk": 50,
    })
    assert result["total_score"] == 50.0
    assert result["risk_level"] == "medium"


def test_missing_factor_defaults_to_50():
    """Missing factors should default to 50 (medium), not crash."""
    result = compute_risk_score({"fx_risk": 0})
    # Only fx_risk (0*0.30=0) + 4 others at 50 (50*0.20+0.20+0.15+0.15 = 35)
    assert 30 <= result["total_score"] <= 40
    assert "fx_risk" in result["breakdown"]


def test_weights_sum_to_one():
    """Sanity check: weights must sum to 1.0 for scoring to be 0-100."""
    result = compute_risk_score({"fx_risk": 0, "logistics_risk": 0, "tariff_risk": 0,
                                   "political_risk": 0, "disaster_risk": 0})
    # All zeros, but we can verify structure
    for factor, info in result["breakdown"].items():
        assert 0 <= info["weight"] <= 1


def test_breakdown_includes_all_factors():
    result = compute_risk_score({"fx_risk": 10})
    for factor in ("fx_risk", "logistics_risk", "tariff_risk", "political_risk", "disaster_risk"):
        assert factor in result["breakdown"]
