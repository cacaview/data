"""Repository-layer tests for trade data access."""

from __future__ import annotations

from app.repositories import trade_repo


def test_get_latest_year_empty(session):
    assert trade_repo.get_latest_year(session) is None


def test_get_latest_year_with_data(session, sample_trade_records):
    assert trade_repo.get_latest_year(session) == 2024


def test_get_latest_year_for_partner(session, sample_trade_records):
    assert trade_repo.get_latest_year_for_partner(session, "VNM") == 2024


def test_get_latest_year_for_missing_partner(session, sample_trade_records):
    assert trade_repo.get_latest_year_for_partner(session, "XYZ") is None


def test_sum_trade_value_for_year(session, sample_trade_records):
    total = trade_repo.sum_trade_value(session, year=2024, partner="VNM")
    assert total > 0


def test_sum_trade_value_for_missing_partner(session, sample_trade_records):
    total = trade_repo.sum_trade_value(session, year=2024, partner="XYZ")
    assert total == 0.0


def test_count_distinct_sections(session, sample_trade_records):
    # All seeded records have hs_section="XVI"
    count = trade_repo.count_distinct_sections(session, year=2024, partner="VNM")
    assert count == 1


def test_get_country_name_map(session, sample_countries):
    m = trade_repo.get_country_name_map(session, ["VNM", "THA", "MISSING"])
    assert m == {"VNM": "越南", "THA": "泰国"}


def test_fetch_trend_rows_orders_by_year_month(session, sample_trade_records):
    rows = trade_repo.fetch_trend_rows(session)
    assert rows
    for a, b in zip(rows, rows[1:], strict=False):
        # year then month
        assert (a[0], a[1]) <= (b[0], b[1])
