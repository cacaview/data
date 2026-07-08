"""Trade analytics service.

Pure-Python business logic for trade trend, ranking, comparison,
and sankey analysis. No SQLAlchemy queries here — all data is
loaded via trade_repo.
"""
from __future__ import annotations

from typing import List, Optional, Sequence, Tuple

from sqlalchemy.orm import Session

from app.core.constants import (
    ASEAN_COUNTRY_CODES,
    DEFAULT_RCEP_UTILIZATION_PCT,
    HS_SECTION_NORMALIZATION_BASE,
    RANKING_DEFAULT_LIMIT,
    RANKING_MAX_LIMIT,
)
from app.models.schemas import (
    CountryRadar,
    RankingItem,
    SankeyData,
    SankeyLink,
    SankeyNode,
    TrendPoint,
)
from app.repositories import trade_repo


# === Trend ===

def get_trend(
    db: Session,
    *,
    countries: Optional[Sequence[str]] = None,
    sections: Optional[Sequence[str]] = None,
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
) -> List[TrendPoint]:
    """Build monthly trend points with country name resolution."""
    rows = trade_repo.fetch_trend_rows(
        db,
        countries=countries,
        sections=sections,
        start_year=start_year,
        end_year=end_year,
    )
    partner_codes = list({r[2] for r in rows})
    name_map = trade_repo.get_country_name_map(db, partner_codes)
    return [
        TrendPoint(
            date=f"{r[0]}-{r[1]:02d}",
            value=round(r[3], 2),
            country=name_map.get(r[2], r[2]),
        )
        for r in rows
    ]


# === Country compare (radar) ===

def _compute_country_radar(
    db: Session, code: str
) -> Optional[CountryRadar]:
    """Build a CountryRadar for one country. Returns None if no trade data."""
    country = trade_repo.get_country(db, code)
    if not country:
        return None

    latest_year = trade_repo.get_latest_year_for_partner(db, code)
    if not latest_year:
        return None

    trade_volume = trade_repo.sum_trade_value(db, year=latest_year, partner=code)
    prev_volume = trade_repo.sum_trade_value(db, year=latest_year - 1, partner=code)
    growth_rate = (
        ((trade_volume - prev_volume) / prev_volume * 100) if prev_volume else 0.0
    )

    # Interdependence: trade / GDP ratio (clamped 0-100)
    gdp_usd = (country.gdp_billion_usd or 1) * 1e9
    interdependence = (
        min((trade_volume / gdp_usd) * 100, 100) if gdp_usd else 0.0
    )

    section_count = trade_repo.count_distinct_sections(
        db, year=latest_year, partner=code
    )
    diversity = min(
        section_count / HS_SECTION_NORMALIZATION_BASE * 100, 100
    )

    rcep_utilization = DEFAULT_RCEP_UTILIZATION_PCT if country.rcep_member else 0.0

    return CountryRadar(
        country=country.name_cn,
        trade_volume=round(trade_volume, 2),
        growth_rate=round(growth_rate, 2),
        interdependence=round(interdependence, 2),
        diversity=round(diversity, 2),
        rcep_utilization=rcep_utilization,
    )


def get_country_compare(db: Session) -> List[CountryRadar]:
    """Build radar data for the 10 ASEAN member countries."""
    radars: list[CountryRadar] = []
    for code in ASEAN_COUNTRY_CODES:
        radar = _compute_country_radar(db, code)
        if radar is not None:
            radars.append(radar)
    return radars


# === Ranking ===

def _safe_growth(current: float, previous: float) -> Optional[float]:
    """Compute YoY growth as a percentage. Returns None when previous == 0."""
    if not previous:
        return None
    return round((current - previous) / previous * 100, 2)


def _rank_by_group(
    db: Session,
    *,
    group_by: str,
    latest_year: int,
    limit: int,
) -> List[RankingItem]:
    """Generic ranking: get top N for the given group_by key."""
    rows = trade_repo.sum_trade_value_grouped(db, year=latest_year, group_by=group_by)
    if not rows:
        return []
    rows = rows[:limit]

    # Previous-year totals (single batch query via a second grouped call)
    prev_rows = trade_repo.sum_trade_value_grouped(
        db, year=latest_year - 1, group_by=group_by
    )
    prev_map = {k: v for k, v in prev_rows}

    total_all = trade_repo.sum_trade_value(db, year=latest_year)
    if total_all <= 0:
        total_all = 1.0

    # Country names only needed when grouping by partner
    name_map: dict[str, str] = {}
    if group_by == "partner":
        codes = [k for k, _ in rows]
        name_map = trade_repo.get_country_name_map(db, codes)

    items: list[RankingItem] = []
    for key, value in rows:
        prev = prev_map.get(key, 0.0)
        items.append(
            RankingItem(
                name=name_map.get(key, key) if group_by == "partner" else key,
                value=round(value, 2),
                growth=_safe_growth(value, prev),
                share=round(value / total_all * 100, 2),
            )
        )
    return items


def get_ranking(
    db: Session,
    *,
    rank_type: str,  # 'country' or 'product'
    limit: int = RANKING_DEFAULT_LIMIT,
) -> List[RankingItem]:
    """Top-N ranking by country (partner) or product (HS section)."""
    if not (1 <= limit <= RANKING_MAX_LIMIT):
        limit = RANKING_DEFAULT_LIMIT

    latest_year = trade_repo.get_latest_year(db)
    if not latest_year:
        return []

    group_by = "partner" if rank_type == "country" else "hs_section"
    return _rank_by_group(
        db, group_by=group_by, latest_year=latest_year, limit=limit
    )


# === Sankey ===

def get_sankey(db: Session, year: int) -> SankeyData:
    """Build sankey data: partners -> product sections for a year."""
    rows = trade_repo.fetch_sankey_rows(db, year=year)
    if not rows:
        return SankeyData(nodes=[], links=[])

    partner_codes = list({r[0] for r in rows})
    name_map = trade_repo.get_country_name_map(db, partner_codes)
    sections = sorted({r[1] for r in rows if r[1]})

    nodes = [
        SankeyNode(name=name_map.get(c, c), category="country")
        for c in sorted(partner_codes)
    ]
    nodes += [SankeyNode(name=s, category="product") for s in sections]

    links = [
        SankeyLink(
            source=name_map.get(r[0], r[0]),
            target=r[1],
            value=round(r[2], 2),
        )
        for r in rows
        if r[1]
    ]
    return SankeyData(nodes=nodes, links=links)
