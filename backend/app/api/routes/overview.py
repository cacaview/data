"""Overview dashboard routes -- KPI summary, map, sankey, mini-trend."""
from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.schemas_db import TradeRecord, Country
from app.models.schemas import (
    KPISummary,
    TradeMapPoint,
    TradeMapArc,
    SankeyData,
    SankeyNode,
    SankeyLink,
    TrendPoint,
)

router = APIRouter()

CURRENT_YEAR = 2025


# ── GET /summary ────────────────────────────────────────────────────────────
@router.get("/summary", response_model=KPISummary)
def get_summary(db: Session = Depends(get_db)):
    """KPI cards for the overview dashboard."""
    # Total trade value for current year
    total_current = (
        db.query(func.coalesce(func.sum(TradeRecord.trade_value_usd), 0.0))
        .filter(TradeRecord.year == CURRENT_YEAR)
        .scalar()
    )

    # Total trade value for previous year (YoY)
    total_prev = (
        db.query(func.coalesce(func.sum(TradeRecord.trade_value_usd), 0.0))
        .filter(TradeRecord.year == CURRENT_YEAR - 1)
        .scalar()
    )

    yoy_growth = ((total_current - total_prev) / total_prev * 100) if total_prev else 0.0

    # Number of distinct trade partners
    partner_count = (
        db.query(func.count(func.distinct(TradeRecord.partner)))
        .filter(TradeRecord.year == CURRENT_YEAR)
        .scalar()
    )

    # Number of distinct product sections
    product_categories = (
        db.query(func.count(func.distinct(TradeRecord.hs_section)))
        .filter(TradeRecord.year == CURRENT_YEAR)
        .scalar()
    )

    # Top partner by trade value
    top_partner_row = (
        db.query(
            TradeRecord.partner,
            func.sum(TradeRecord.trade_value_usd).label("total"),
        )
        .filter(TradeRecord.year == CURRENT_YEAR)
        .group_by(TradeRecord.partner)
        .order_by(func.sum(TradeRecord.trade_value_usd).desc())
        .first()
    )
    if top_partner_row:
        country = db.query(Country).filter(Country.code == top_partner_row[0]).first()
        top_partner = country.name_cn if country else top_partner_row[0]
    else:
        top_partner = "N/A"

    # Top product section by trade value
    top_product_row = (
        db.query(
            TradeRecord.hs_section,
            func.sum(TradeRecord.trade_value_usd).label("total"),
        )
        .filter(TradeRecord.year == CURRENT_YEAR)
        .group_by(TradeRecord.hs_section)
        .order_by(func.sum(TradeRecord.trade_value_usd).desc())
        .first()
    )
    top_product = top_product_row[0] if top_product_row and top_product_row[0] else "N/A"

    return KPISummary(
        total_trade_value=round(total_current, 2),
        yoy_growth=round(yoy_growth, 2),
        partner_count=partner_count,
        product_categories=product_categories,
        top_partner=top_partner,
        top_product=top_product,
    )


# ── GET /trade-map ──────────────────────────────────────────────────────────
@router.get("/trade-map")
def get_trade_map(db: Session = Depends(get_db)):
    """Trade map data: country points + arcs from China to partners."""
    # Aggregate trade value per partner for current year
    partner_agg = (
        db.query(
            TradeRecord.partner,
            func.sum(TradeRecord.trade_value_usd).label("total"),
        )
        .filter(TradeRecord.year == CURRENT_YEAR, TradeRecord.reporter == "CHN")
        .group_by(TradeRecord.partner)
        .all()
    )

    # Previous year for growth calculation
    prev_agg = dict(
        db.query(
            TradeRecord.partner,
            func.sum(TradeRecord.trade_value_usd),
        )
        .filter(TradeRecord.year == CURRENT_YEAR - 1, TradeRecord.reporter == "CHN")
        .group_by(TradeRecord.partner)
        .all()
    )

    # Top products per partner
    top_products_map: dict[str, list[str]] = {}
    for partner_code, _ in partner_agg:
        tops = (
            db.query(TradeRecord.hs_section)
            .filter(
                TradeRecord.year == CURRENT_YEAR,
                TradeRecord.partner == partner_code,
                TradeRecord.reporter == "CHN",
            )
            .group_by(TradeRecord.hs_section)
            .order_by(func.sum(TradeRecord.trade_value_usd).desc())
            .limit(3)
            .all()
        )
        top_products_map[partner_code] = [t[0] for t in tops if t[0]]

    # China coordinates
    china = db.query(Country).filter(Country.code == "CHN").first()
    china_lat = china.latitude if china else 35.86
    china_lon = china.longitude if china else 104.19

    points: list[TradeMapPoint] = []
    arcs: list[TradeMapArc] = []

    for partner_code, total in partner_agg:
        country = db.query(Country).filter(Country.code == partner_code).first()
        if not country:
            continue

        prev_val = prev_agg.get(partner_code, 0) or 0
        growth = ((total - prev_val) / prev_val * 100) if prev_val else 0.0

        points.append(
            TradeMapPoint(
                country_code=partner_code,
                country_name=country.name_cn,
                latitude=country.latitude or 0,
                longitude=country.longitude or 0,
                trade_value=round(total, 2),
                growth_rate=round(growth, 2),
                top_products=top_products_map.get(partner_code, []),
            )
        )

        arcs.append(
            TradeMapArc(
                from_code="CHN",
                to_code=partner_code,
                from_name="中国",
                to_name=country.name_cn,
                trade_value=round(total, 2),
                coords=[
                    [china_lon, china_lat],
                    [country.longitude or 0, country.latitude or 0],
                ],
            )
        )

    return {"points": points, "arcs": arcs}


# ── GET /sankey ─────────────────────────────────────────────────────────────
@router.get("/sankey", response_model=SankeyData)
def get_overview_sankey(db: Session = Depends(get_db)):
    """Sankey diagram: top-5 countries -> product sections for current year."""
    # Top 5 countries by trade value
    top_countries = (
        db.query(
            TradeRecord.partner,
            func.sum(TradeRecord.trade_value_usd).label("total"),
        )
        .filter(TradeRecord.year == CURRENT_YEAR, TradeRecord.reporter == "CHN")
        .group_by(TradeRecord.partner)
        .order_by(func.sum(TradeRecord.trade_value_usd).desc())
        .limit(5)
        .all()
    )

    country_codes = [c[0] for c in top_countries]

    # Country name lookup
    country_names = {}
    if country_codes:
        for c in db.query(Country).filter(Country.code.in_(country_codes)).all():
            country_names[c.code] = c.name_cn

    # Flows: country -> product section
    flows = (
        db.query(
            TradeRecord.partner,
            TradeRecord.hs_section,
            func.sum(TradeRecord.trade_value_usd).label("total"),
        )
        .filter(
            TradeRecord.year == CURRENT_YEAR,
            TradeRecord.reporter == "CHN",
            TradeRecord.partner.in_(country_codes),
        )
        .group_by(TradeRecord.partner, TradeRecord.hs_section)
        .all()
    )

    # Collect product sections
    sections = set()
    for _, section, _ in flows:
        if section:
            sections.add(section)

    nodes = [SankeyNode(name=country_names.get(c, c), category="country") for c in country_codes]
    nodes += [SankeyNode(name=s, category="product") for s in sorted(sections)]

    links = []
    for partner, section, total in flows:
        if not section:
            continue
        links.append(
            SankeyLink(
                source=country_names.get(partner, partner),
                target=section,
                value=round(total, 2),
            )
        )

    return SankeyData(nodes=nodes, links=links)


# ── GET /trend-mini ─────────────────────────────────────────────────────────
@router.get("/trend-mini", response_model=list[TrendPoint])
def get_trend_mini(db: Session = Depends(get_db)):
    """Monthly total trade value for the last 12 months (sparkline data)."""
    # Determine the latest month in the database
    latest = (
        db.query(TradeRecord.year, TradeRecord.month)
        .order_by(TradeRecord.year.desc(), TradeRecord.month.desc())
        .first()
    )
    if not latest:
        return []

    latest_year, latest_month = latest

    # Compute 12-month window
    results = []
    for i in range(11, -1, -1):
        m = latest_month - i
        y = latest_year
        while m <= 0:
            m += 12
            y -= 1

        total = (
            db.query(func.coalesce(func.sum(TradeRecord.trade_value_usd), 0.0))
            .filter(TradeRecord.year == y, TradeRecord.month == m)
            .scalar()
        )
        results.append(
            TrendPoint(date=f"{y}-{m:02d}", value=round(total, 2))
        )

    return results
