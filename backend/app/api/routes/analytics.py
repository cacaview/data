"""Analytics API Routes.

Implements P0 killer features:
- /burst-radar: B1 - Burst product detection
- /risk-dashboard: D5 - Composite risk dashboard
- /upstreamness: A2 - Value chain position index
- /tariff-savings: B2 - RCEP tariff savings calculator
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func

from app.models.database import get_db
from app.models.schemas_db import TradeRecord, Country, TariffRule

router = APIRouter()


@router.get("/burst-radar")
def get_burst_radar(
    partner: str = Query("VNM", description="Partner country ISO code"),
    threshold: float = Query(200.0, description="YoY growth % threshold for burst detection"),
    db: Session = Depends(get_db),
):
    """B1: Detect burst/booming products using anomaly detection.

    Analyzes monthly trade data to find products with sudden growth spikes.
    Uses rolling statistics and YoY comparison for robust detection.
    """
    # Get trade data for this partner
    records = (
        db.query(TradeRecord)
        .filter(TradeRecord.partner == partner, TradeRecord.trade_flow == "export")
        .all()
    )

    if not records:
        return {"bursts": [], "summary": f"No trade data for {partner}"}

    # Convert to list of dicts for the analytics module
    trade_data = []
    for r in records:
        trade_data.append({
            "hs_code": r.hs_code,
            "trade_value_usd": r.trade_value_usd,
            "year": r.year,
            "month": r.month,
            "id": r.id,
        })

    from app.data.analytics import detect_burst_products
    result = detect_burst_products(trade_data, threshold_pct=threshold)

    # Enrich with country/product names
    partner_obj = db.query(Country).filter(Country.code == partner).first()
    result["partner"] = partner
    result["partner_name"] = partner_obj.name_cn if partner_obj else partner

    return result


@router.get("/risk-dashboard")
def get_risk_dashboard(
    country: str = Query("VNM", description="Target country ISO code"),
    db: Session = Depends(get_db),
):
    """D5: Composite risk dashboard with 5 risk dimensions.

    Returns risk scores for: FX, logistics, tariff, political, disaster.
    Each score is 0-100 (higher = more risky).
    """
    # Get country info
    country_obj = db.query(Country).filter(Country.code == country).first()

    # Compute risk factors based on available data
    # In production, these would pull from real APIs
    risk_factors = _compute_risk_factors(country, db)

    from app.data.analytics import compute_risk_score
    result = compute_risk_score(risk_factors)
    result["country"] = country
    result["country_name"] = country_obj.name_cn if country_obj else country

    # Add recommendations based on risk level
    if result["risk_level"] == "high":
        result["recommendations"] = [
            "建议缩短账期至30天以内",
            "增加汇率对冲工具使用",
            "分散出口目的地降低集中度风险",
        ]
    elif result["risk_level"] == "medium":
        result["recommendations"] = [
            "持续监控汇率波动",
            "关注RCEP降税时间表优化关税",
            "评估替代供应链方案",
        ]
    else:
        result["recommendations"] = [
            "风险可控，可适度扩大贸易规模",
            "利用RCEP优惠进一步降低成本",
        ]

    return result


@router.get("/upstreamness")
def get_upstreamness(
    year: int = Query(2023, description="Year for analysis"),
    db: Session = Depends(get_db),
):
    """A2: Compute value chain upstreamness index.

    Measures how far each ASEAN country is from final demand
    in the China-ASEAN trade network.
    """
    # Aggregate trade by partner and HS chapter
    records = (
        db.query(
            TradeRecord.partner,
            TradeRecord.hs_chapter,
            func.sum(TradeRecord.trade_value_usd).label("total_value"),
        )
        .filter(TradeRecord.year == year, TradeRecord.trade_flow == "export")
        .group_by(TradeRecord.partner, TradeRecord.hs_chapter)
        .all()
    )

    trade_flows = {}
    for r in records:
        if r.hs_chapter:
            trade_flows[(r.partner, r.hs_chapter)] = r.total_value or 0

    from app.data.analytics import compute_upstreamness
    indices = compute_upstreamness(trade_flows)

    # Enrich with country names
    countries = {c.code: c for c in db.query(Country).all()}
    result = []
    for code, idx in sorted(indices.items(), key=lambda x: x[1], reverse=True):
        c = countries.get(code)
        result.append({
            "country": code,
            "country_name": c.name_cn if c else code,
            "upstreamness_index": idx,
            "position": "上游（原材料/中间品）" if idx > 3 else "中游" if idx > 2 else "下游（终端消费品）",
        })

    return {"year": year, "upstreamness": result}


@router.get("/tariff-savings")
def get_tariff_savings(
    partner: str = Query("VNM", description="Target country"),
    db: Session = Depends(get_db),
):
    """B2: Calculate potential RCEP tariff savings across all HS codes.

    Returns total savings if all trade used RCEP preferential rates.
    """
    # Get all tariff rules for this partner
    rules = db.query(TariffRule).filter(TariffRule.partner_country == partner).all()
    if not rules:
        return {"error": f"No tariff rules for {partner}"}

    # Get actual trade values
    trade_values = {}
    records = (
        db.query(TradeRecord.hs_code, func.sum(TradeRecord.trade_value_usd))
        .filter(TradeRecord.partner == partner, TradeRecord.trade_flow == "export")
        .group_by(TradeRecord.hs_code)
        .all()
    )
    for r in records:
        trade_values[r[0]] = r[1] or 0

    from app.data.analytics import calculate_rcep_savings
    savings_list = []
    total_savings = 0

    for rule in rules:
        trade_val = trade_values.get(rule.hs_code, 0)
        if trade_val <= 0:
            continue

        result = calculate_rcep_savings(
            rule.hs_code, rule.mfn_rate or 0, rule.rcep_rate or 0,
            rule.fta_rate, trade_val,
        )
        result["rule_of_origin"] = rule.rule_of_origin or ""
        savings_list.append(result)
        total_savings += result["savings_usd"]

    savings_list.sort(key=lambda x: x["savings_usd"], reverse=True)

    partner_obj = db.query(Country).filter(Country.code == partner).first()
    return {
        "partner": partner,
        "partner_name": partner_obj.name_cn if partner_obj else partner,
        "total_potential_savings_usd": round(total_savings, 2),
        "items": savings_list[:50],
        "summary": f"RCEP潜在节省: ${total_savings:,.0f}",
    }


def _compute_risk_factors(country: str, db: Session) -> dict:
    """Compute risk factors for a country based on available data.

    Returns scores 0-100 for each dimension.
    """
    # Base scores by country (simplified heuristic)
    country_risk = {
        "VNM": {"fx": 35, "logistics": 25, "tariff": 20, "political": 30, "disaster": 40},
        "THA": {"fx": 30, "logistics": 20, "tariff": 15, "political": 35, "disaster": 30},
        "MYS": {"fx": 25, "logistics": 20, "tariff": 15, "political": 20, "disaster": 25},
        "IDN": {"fx": 40, "logistics": 35, "tariff": 25, "political": 30, "disaster": 50},
        "PHL": {"fx": 35, "logistics": 30, "tariff": 20, "political": 35, "disaster": 55},
        "SGP": {"fx": 15, "logistics": 10, "tariff": 10, "political": 10, "disaster": 15},
        "MMR": {"fx": 60, "logistics": 55, "tariff": 45, "political": 70, "disaster": 40},
        "KHM": {"fx": 45, "logistics": 40, "tariff": 30, "political": 45, "disaster": 35},
        "LAO": {"fx": 50, "logistics": 45, "tariff": 35, "political": 40, "disaster": 30},
        "BRN": {"fx": 20, "logistics": 25, "tariff": 15, "political": 15, "disaster": 20},
    }
    return country_risk.get(country, {"fx": 50, "logistics": 50, "tariff": 50, "political": 50, "disaster": 50})
