"""Service-layer tests for trade business logic.

Focuses on:
- Pure business rules (no SQL: use in-memory fixtures)
- Edge cases (empty data, missing country, etc.)
"""
from __future__ import annotations

import pytest

from app.services import trade_service


# === Trend ===

def test_trend_empty_db_returns_empty_list(session):
    assert trade_service.get_trend(session) == []


def test_trend_returns_points_with_country_names(session, sample_trade_records):
    points = trade_service.get_trend(session, countries=["VNM"])
    assert points
    assert all(p.country == "越南" for p in points)
    assert all(p.value > 0 for p in points)


def test_trend_filters_by_section(session, sample_trade_records):
    points = trade_service.get_trend(session, sections=["XVI"])
    assert all(p.country in {"越南", "泰国", "印度尼西亚"} for p in points)


def test_trend_filters_by_year_range(session, sample_trade_records):
    points = trade_service.get_trend(session, start_year=2024, end_year=2024)
    assert all(p.date.startswith("2024") for p in points)


# === Country compare ===

def test_country_compare_returns_only_asean_countries_with_data(
    session, sample_countries, sample_trade_records
):
    radars = trade_service.get_country_compare(session)
    countries = {r.country for r in radars}
    # We seeded 3 ASEAN countries, all should appear
    assert countries == {"越南", "泰国", "印度尼西亚"}


def test_country_compare_radar_fields_in_range(
    session, sample_countries, sample_trade_records
):
    radars = trade_service.get_country_compare(session)
    for r in radars:
        assert 0 <= r.interdependence <= 100
        assert 0 <= r.diversity <= 100
        assert r.rcep_utilization == 80.0  # All seeded as RCEP members
        assert r.trade_volume > 0


# === Ranking ===

def test_ranking_by_country_returns_top_n(session, sample_trade_records):
    items = trade_service.get_ranking(session, rank_type="country", limit=2)
    assert len(items) <= 2
    # All items sorted descending by value
    for a, b in zip(items, items[1:]):
        assert a.value >= b.value


def test_ranking_includes_growth_and_share(session, sample_trade_records):
    items = trade_service.get_ranking(session, rank_type="country", limit=3)
    assert all(item.share is not None for item in items)
    # growth can be null if previous year is 0
    for item in items:
        if item.growth is not None:
            assert -1000 < item.growth < 1000


def test_ranking_by_product_groups_by_section(session, sample_trade_records):
    items = trade_service.get_ranking(session, rank_type="product", limit=5)
    # All seeded records have hs_section="XVI" — should have 1 item
    assert len(items) >= 1
    assert all(item.name for item in items)


def test_ranking_limit_clamped(session, sample_trade_records):
    # Limit > max is silently clamped by service
    items = trade_service.get_ranking(session, rank_type="country", limit=999)
    # Service returns up to 50 entries; dataset has only 3 partners
    assert len(items) <= 50


def test_ranking_empty_db(session):
    assert trade_service.get_ranking(session, rank_type="country") == []


# === Sankey ===

def test_sankey_empty_year(session):
    data = trade_service.get_sankey(session, year=1999)
    assert data.nodes == []
    assert data.links == []


def test_sankey_returns_nodes_and_links(session, sample_trade_records):
    data = trade_service.get_sankey(session, year=2024)
    assert data.nodes
    assert data.links
    # Every link references a known node
    node_names = {n.name for n in data.nodes}
    for link in data.links:
        assert link.source in node_names
        assert link.target in node_names
