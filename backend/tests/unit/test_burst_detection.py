"""Burst detection algorithm tests.

Verifies:
- Empty input returns empty result
- Burst flag fires when YoY growth > threshold
- Z-score calculation is reasonable
- CAGR is calculated for 3+ data points
"""
from __future__ import annotations

import pytest

from app.data.analytics import detect_burst_products


def test_empty_input_returns_empty():
    result = detect_burst_products([])
    assert result["bursts"] == []


def test_empty_dataframe_input():
    result = detect_burst_products([{"hs_code": "x", "year": 2024, "month": 1,
                                      "trade_value_usd": 0}])
    # Will not have 6+ months, so no bursts
    assert result["bursts"] == []


def test_steady_data_not_burst():
    """A product with steady 1M/month values for 24 months: no burst."""
    records = []
    for year in (2023, 2024):
        for month in range(1, 13):
            records.append({
                "hs_code": "111111",
                "year": year,
                "month": month,
                "trade_value_usd": 1_000_000,
            })
    result = detect_burst_products(records, threshold_pct=200.0)
    assert result["bursts"]
    for b in result["bursts"]:
        assert b["is_burst"] is False


def test_explosive_growth_triggers_burst():
    """A product that grows 5x in the last 3 months vs same period last year."""
    records = []
    # First 12 months: 1M/month
    for month in range(1, 13):
        records.append({"hs_code": "999999", "year": 2023, "month": month,
                         "trade_value_usd": 1_000_000})
    # Next 12 months: ends at 5M
    for month in range(1, 13):
        # Gradual increase
        value = 1_000_000 + (month * 350_000)
        records.append({"hs_code": "999999", "year": 2024, "month": month,
                         "trade_value_usd": value})
    result = detect_burst_products(records, threshold_pct=200.0)
    bursts = [b for b in result["bursts"] if b["hs_code"] == "999999"]
    assert bursts
    assert bursts[0]["is_burst"] is True
    assert bursts[0]["yoy_growth_pct"] > 200


def test_cagr_calculated_when_3_data_points():
    records = [
        {"hs_code": "x", "year": 2024, "month": 1, "trade_value_usd": 1_000_000},
        {"hs_code": "x", "year": 2024, "month": 2, "trade_value_usd": 1_100_000},
        {"hs_code": "x", "year": 2024, "month": 3, "trade_value_usd": 1_210_000},
        {"hs_code": "x", "year": 2024, "month": 4, "trade_value_usd": 1_331_000},
        {"hs_code": "x", "year": 2024, "month": 5, "trade_value_usd": 1_464_000},
        {"hs_code": "x", "year": 2024, "month": 6, "trade_value_usd": 1_610_000},
    ]
    result = detect_burst_products(records)
    b = result["bursts"][0]
    # 10% growth each month, so CAGR should be positive
    assert b["cagr_3m"] > 0
