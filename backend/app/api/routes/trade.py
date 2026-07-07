"""Trade analysis routes -- trends, country comparison, ranking, sankey."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from typing import Optional

from app.models.database import get_db
from app.models.schemas_db import TradeRecord, Country
from app.models.schemas import (
    TrendPoint,
    CountryRadar,
    RankingItem,
    SankeyData,
    SankeyNode,
    SankeyLink,
)

router = APIRouter()

ASEAN_CODES = [
    "BRN", "KHM", "IDN", "LAO", "MYS",
    "MMR", "PHL", "SGP", "THA", "VNM",
]


# ── GET /trend ──────────────────────────────────────────────────────────────
@router.get("/trend", response_model=list[TrendPoint])
def get_trend(
    countries: Optional[str] = Query(None, description="Comma-separated ISO codes"),
    products: Optional[str] = Query(None, description="Comma-separated HS sections"),
    start_year: Optional[int] = Query(None),
    end_year: Optional[int] = Query(None),
    db: Session = Depends(get_db),
):
    """Monthly trade trend, optionally filtered by countries and products."""
    q = db.query(
        TradeRecord.year,
        TradeRecord.month,
        TradeRecord.partner,
        func.sum(TradeRecord.trade_value_usd).label("total"),
    ).filter(TradeRecord.reporter == "CHN")

    if countries:
        code_list = [c.strip() for c in countries.split(",") if c.strip()]
        if code_list:
            q = q.filter(TradeRecord.partner.in_(code_list))

    if products:
        prod_list = [p.strip() for p in products.split(",") if p.strip()]
        if prod_list:
            q = q.filter(TradeRecord.hs_section.in_(prod_list))

    if start_year:
        q = q.filter(TradeRecord.year >= start_year)
    if end_year:
        q = q.filter(TradeRecord.year <= end_year)

    rows = (
        q.group_by(TradeRecord.year, TradeRecord.month, TradeRecord.partner)
        .order_by(TradeRecord.year, TradeRecord.month)
        .all()
    )

    # Country name lookup
    partner_codes = list({r[2] for r in rows})
    country_names: dict[str, str] = {}
    if partner_codes:
        for c in db.query(Country).filter(Country.code.in_(partner_codes)).all():
            country_names[c.code] = c.name_cn

    return [
        TrendPoint(
            date=f"{r[0]}-{r[1]:02d}",
            value=round(r[3], 2),
            country=country_names.get(r[2], r[2]),
        )
        for r in rows
    ]


# ── GET /country-compare ────────────────────────────────────────────────────
@router.get("/country-compare", response_model=list[CountryRadar])
def get_country_compare(db: Session = Depends(get_db)):
    """Radar chart data for the 10 ASEAN member countries."""
    results: list[CountryRadar] = []

    for code in ASEAN_CODES:
        country = db.query(Country).filter(Country.code == code).first()
        if not country:
            continue

        # Trade volume (total trade value with China, latest year in DB)
        latest_year = (
            db.query(func.max(TradeRecord.year))
            .filter(TradeRecord.partner == code, TradeRecord.reporter == "CHN")
            .scalar()
        )
        if not latest_year:
            continue

        trade_volume = (
            db.query(func.coalesce(func.sum(TradeRecord.trade_value_usd), 0.0))
            .filter(
                TradeRecord.partner == code,
                TradeRecord.reporter == "CHN",
                TradeRecord.year == latest_year,
            )
            .scalar()
        )

        prev_volume = (
            db.query(func.coalesce(func.sum(TradeRecord.trade_value_usd), 0.0))
            .filter(
                TradeRecord.partner == code,
                TradeRecord.reporter == "CHN",
                TradeRecord.year == latest_year - 1,
            )
            .scalar()
        )
        growth_rate = ((trade_volume - prev_volume) / prev_volume * 100) if prev_volume else 0.0

        # Interdependence: trade / GDP ratio (simplified)
        gdp_usd = (country.gdp_billion_usd or 1) * 1e9
        interdependence = min((trade_volume / gdp_usd) * 100, 100) if gdp_usd else 0.0

        # Diversity: number of distinct HS sections traded
        section_count = (
            db.query(func.count(func.distinct(TradeRecord.hs_section)))
            .filter(
                TradeRecord.partner == code,
                TradeRecord.reporter == "CHN",
                TradeRecord.year == latest_year,
            )
            .scalar()
        )
        # Normalize to 0-100 (max ~20 sections)
        diversity = min((section_count or 0) / 20 * 100, 100)

        # RCEP utilization: share of trade under RCEP rates (proxied by rcep_member flag)
        rcep_utilization = 80.0 if country.rcep_member else 0.0

        results.append(
            CountryRadar(
                country=country.name_cn,
                trade_volume=round(trade_volume, 2),
                growth_rate=round(growth_rate, 2),
                interdependence=round(interdependence, 2),
                diversity=round(diversity, 2),
                rcep_utilization=rcep_utilization,
            )
        )

    return results


# ── GET /ranking ────────────────────────────────────────────────────────────
@router.get("/ranking", response_model=list[RankingItem])
def get_ranking(
    type: str = Query("country", pattern="^(country|product)$"),
    limit: int = Query(10, ge=1, le=50),
    db: Session = Depends(get_db),
):
    """Top-N ranking by country or product section."""
    latest_year = db.query(func.max(TradeRecord.year)).scalar()
    if not latest_year:
        return []

    prev_year = latest_year - 1

    if type == "country":
        rows = (
            db.query(
                TradeRecord.partner,
                func.sum(TradeRecord.trade_value_usd).label("total"),
            )
            .filter(
                TradeRecord.year == latest_year,
                TradeRecord.reporter == "CHN",
            )
            .group_by(TradeRecord.partner)
            .order_by(func.sum(TradeRecord.trade_value_usd).desc())
            .limit(limit)
            .all()
        )

        # Previous year lookup for growth
        prev_map = dict(
            db.query(
                TradeRecord.partner,
                func.sum(TradeRecord.trade_value_usd),
            )
            .filter(TradeRecord.year == prev_year, TradeRecord.reporter == "CHN")
            .group_by(TradeRecord.partner)
            .all()
        )

        total_all = (
            db.query(func.coalesce(func.sum(TradeRecord.trade_value_usd), 1.0))
            .filter(TradeRecord.year == latest_year, TradeRecord.reporter == "CHN")
            .scalar()
        )

        # Country name lookup
        codes = [r[0] for r in rows]
        name_map = {}
        if codes:
            for c in db.query(Country).filter(Country.code.in_(codes)).all():
                name_map[c.code] = c.name_cn

        return [
            RankingItem(
                name=name_map.get(r[0], r[0]),
                value=round(r[1], 2),
                growth=round(((r[1] - prev_map.get(r[0], 0)) / prev_map.get(r[0], 1)) * 100, 2)
                if prev_map.get(r[0]) else None,
                share=round(r[1] / total_all * 100, 2) if total_all else None,
            )
            for r in rows
        ]

    else:  # type == "product"
        rows = (
            db.query(
                TradeRecord.hs_section,
                func.sum(TradeRecord.trade_value_usd).label("total"),
            )
            .filter(
                TradeRecord.year == latest_year,
                TradeRecord.reporter == "CHN",
                TradeRecord.hs_section.isnot(None),
            )
            .group_by(TradeRecord.hs_section)
            .order_by(func.sum(TradeRecord.trade_value_usd).desc())
            .limit(limit)
            .all()
        )

        prev_map = dict(
            db.query(
                TradeRecord.hs_section,
                func.sum(TradeRecord.trade_value_usd),
            )
            .filter(
                TradeRecord.year == prev_year,
                TradeRecord.reporter == "CHN",
                TradeRecord.hs_section.isnot(None),
            )
            .group_by(TradeRecord.hs_section)
            .all()
        )

        total_all = (
            db.query(func.coalesce(func.sum(TradeRecord.trade_value_usd), 1.0))
            .filter(TradeRecord.year == latest_year, TradeRecord.reporter == "CHN")
            .scalar()
        )

        return [
            RankingItem(
                name=r[0],
                value=round(r[1], 2),
                growth=round(((r[1] - prev_map.get(r[0], 0)) / prev_map.get(r[0], 1)) * 100, 2)
                if prev_map.get(r[0]) else None,
                share=round(r[1] / total_all * 100, 2) if total_all else None,
            )
            for r in rows
        ]


# ── GET /sankey ─────────────────────────────────────────────────────────────
@router.get("/sankey", response_model=SankeyData)
def get_trade_sankey(
    year: int = Query(2024),
    db: Session = Depends(get_db),
):
    """Full sankey diagram: all countries -> product sections for a given year."""
    rows = (
        db.query(
            TradeRecord.partner,
            TradeRecord.hs_section,
            func.sum(TradeRecord.trade_value_usd).label("total"),
        )
        .filter(
            TradeRecord.year == year,
            TradeRecord.reporter == "CHN",
            TradeRecord.hs_section.isnot(None),
        )
        .group_by(TradeRecord.partner, TradeRecord.hs_section)
        .all()
    )

    if not rows:
        return SankeyData(nodes=[], links=[])

    # Country name lookup
    partner_codes = list({r[0] for r in rows})
    country_names: dict[str, str] = {}
    if partner_codes:
        for c in db.query(Country).filter(Country.code.in_(partner_codes)).all():
            country_names[c.code] = c.name_cn

    sections = sorted({r[1] for r in rows if r[1]})

    nodes = [SankeyNode(name=country_names.get(c, c), category="country") for c in sorted(partner_codes)]
    nodes += [SankeyNode(name=s, category="product") for s in sections]

    links = [
        SankeyLink(
            source=country_names.get(r[0], r[0]),
            target=r[1],
            value=round(r[2], 2),
        )
        for r in rows
        if r[1]
    ]

    return SankeyData(nodes=nodes, links=links)
