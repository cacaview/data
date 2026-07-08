"""RCEP tariff savings tests."""

from app.data.analytics import calculate_rcep_savings


def test_basic_savings_calculation():
    result = calculate_rcep_savings(
        hs_code="854232",
        mfn_rate=10.0,
        rcep_rate=2.0,
        fta_rate=None,
        trade_value=1_000_000,
    )
    # MFN duty: 100k, RCEP duty: 20k -> savings 80k
    assert result["duty_mfn"] == 100_000.0
    assert result["duty_best"] == 20_000.0
    assert result["savings_usd"] == 80_000.0
    assert result["savings_pct"] == 80.0
    assert result["best_scheme"] == "RCEP"


def test_chooses_lowest_rate():
    """If ACFTA < RCEP, ACFTA wins."""
    result = calculate_rcep_savings(
        hs_code="111111",
        mfn_rate=15.0,
        rcep_rate=5.0,
        fta_rate=2.0,
        trade_value=500_000,
    )
    assert result["best_scheme"] == "ACFTA"
    assert result["best_rate"] == 2.0


def test_no_fta_uses_rcep():
    result = calculate_rcep_savings(
        hs_code="222222",
        mfn_rate=8.0,
        rcep_rate=0.0,
        fta_rate=None,
        trade_value=100_000,
    )
    assert result["best_scheme"] == "RCEP"
    assert result["best_rate"] == 0.0
    assert result["savings_usd"] == 8_000.0


def test_zero_mfn_zero_savings():
    result = calculate_rcep_savings(
        hs_code="x",
        mfn_rate=0.0,
        rcep_rate=0.0,
        fta_rate=None,
        trade_value=100,
    )
    assert result["savings_usd"] == 0.0
    assert result["savings_pct"] == 0.0


def test_zero_trade_value():
    result = calculate_rcep_savings(
        hs_code="x",
        mfn_rate=10.0,
        rcep_rate=0.0,
        fta_rate=None,
        trade_value=0,
    )
    assert result["duty_mfn"] == 0
    assert result["duty_best"] == 0
    assert result["savings_usd"] == 0
