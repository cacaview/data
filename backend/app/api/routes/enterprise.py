"""Enterprise Risk Command Center API Routes.

Provides enterprise-facing risk management features:
- /enterprise/risk-monitor: Supply chain risk scoring by country
- /enterprise/compliance: Trade compliance and sanctions screening
- /enterprise/cost-optimizer: Cross-FTA tariff cost optimization
- /enterprise/supply-chain-map: Network visualization data
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.schemas_db import Country, TariffRule, TradeRecord

router = APIRouter()


# ── Risk Monitor ──
@router.get("/risk-monitor")
def get_risk_monitor(
    year: int = Query(2023, description="Year for trade data analysis"),
    db: Session = Depends(get_db),
):
    """Supply chain risk scoring for all trade partner countries.

    Returns per-country risk scores across multiple dimensions (FX,
    logistics, tariff, political, disaster) together with a composite
    score and risk level (high / medium / low).
    """
    countries = db.query(Country).all()

    results = []
    for c in countries:
        # Aggregate export trade value for this partner
        trade_val = (
            db.query(func.sum(TradeRecord.trade_value_usd))
            .filter(
                TradeRecord.partner == c.code,
                TradeRecord.year == year,
                TradeRecord.trade_flow == "export",
            )
            .scalar()
        ) or 0

        risk = _compute_country_risk(c.code)
        avg_score = round(sum(risk.values()) / len(risk), 1)

        if avg_score >= 50:
            risk_level = "high"
        elif avg_score >= 30:
            risk_level = "medium"
        else:
            risk_level = "low"

        results.append({
            "country": c.code,
            "country_name": c.name_cn,
            "country_name_en": c.name_en,
            "trade_value_usd": round(trade_val, 2),
            "risk_score": avg_score,
            "risk_level": risk_level,
            "risk_factors": risk,
            "latitude": c.latitude,
            "longitude": c.longitude,
        })

    # Sort by risk score descending (most risky first)
    results.sort(key=lambda x: x["risk_score"], reverse=True)

    high_count = sum(1 for r in results if r["risk_level"] == "high")
    return {
        "year": year,
        "total_partners": len(results),
        "high_risk_count": high_count,
        "countries": results,
    }


def _compute_country_risk(country: str) -> dict:
    """Compute risk factor scores (0-100) for a country.

    Each dimension is scored independently; higher values indicate
    greater risk.
    """
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
    return country_risk.get(
        country, {"fx": 50, "logistics": 50, "tariff": 50, "political": 50, "disaster": 50}
    )


# ── Compliance ──
@router.get("/compliance")
def get_compliance(
    entity_name: str = Query(..., min_length=1, description="Entity name to screen"),
    db: Session = Depends(get_db),
):
    """Simulated trade compliance and sanctions screening.

    Checks the given entity name against a mock sanctions list and
    returns a clearance status. In production this would integrate with
    real sanctions databases (OFAC, UN, EU).
    """
    # Mock sanctions list for demonstration purposes
    mock_sanctions_list = {
        "global trade corp", "risky ventures ltd", "sanctioned entity llc",
        "blacklisted co", "restricted trading inc",
    }

    entity_lower = entity_name.strip().lower()

    # Exact match check
    if entity_lower in mock_sanctions_list:
        return {
            "entity": entity_name,
            "status": "flagged",
            "risk_level": "critical",
            "lists_checked": ["OFAC SDN", "UN Sanctions", "EU Consolidated"],
            "match_type": "exact",
            "details": "Entity found on sanctions list. Immediate review required.",
        }

    # Partial / fuzzy match check
    partial_matches = [entry for entry in mock_sanctions_list if entity_lower in entry]
    if partial_matches:
        return {
            "entity": entity_name,
            "status": "flagged",
            "risk_level": "warning",
            "lists_checked": ["OFAC SDN", "UN Sanctions", "EU Consolidated"],
            "match_type": "partial",
            "details": f"Partial match found: {', '.join(partial_matches)}. Manual review recommended.",
        }

    return {
        "entity": entity_name,
        "status": "clear",
        "risk_level": "low",
        "lists_checked": ["OFAC SDN", "UN Sanctions", "EU Consolidated"],
        "match_type": "none",
        "details": "No matches found across all checked sanctions lists.",
    }


# ── Cost Optimizer ──
@router.get("/cost-optimizer")
def get_cost_optimizer(
    hs_code: str | None = Query(None, description="Filter by HS code"),
    partners: str = Query("VNM,THA,MYS,IDN", description="Comma-separated partner ISO codes"),
    year: int = Query(2023, description="Year for trade value data"),
    db: Session = Depends(get_db),
):
    """Compare tariff costs across different FTA schemes.

    For each HS code and partner, shows the effective duty under MFN,
    RCEP, and applicable FTA rates, and identifies the best scheme
    together with potential savings.
    """
    partner_list = [p.strip() for p in partners.split(",") if p.strip()]

    query = db.query(TariffRule).filter(TariffRule.partner_country.in_(partner_list))
    if hs_code:
        query = query.filter(TariffRule.hs_code == hs_code)

    rules = query.all()
    if not rules:
        return {"comparisons": [], "summary": "No tariff rules found for given parameters"}

    # Aggregate trade values per (hs_code, partner) for the year
    trade_q = (
        db.query(
            TradeRecord.hs_code,
            TradeRecord.partner,
            func.sum(TradeRecord.trade_value_usd).label("total_value"),
        )
        .filter(
            TradeRecord.partner.in_(partner_list),
            TradeRecord.year == year,
            TradeRecord.trade_flow == "export",
        )
        .group_by(TradeRecord.hs_code, TradeRecord.partner)
        .all()
    )
    trade_map = {(t.hs_code, t.partner): (t.total_value or 0) for t in trade_q}

    comparisons = []
    for rule in rules:
        trade_value = trade_map.get((rule.hs_code, rule.partner_country), 0)
        mfn_rate = rule.mfn_rate or 0
        rcep_rate = rule.rcep_rate or 0
        fta_rate = rule.fta_rate

        mfn_duty = trade_value * mfn_rate / 100
        rcep_duty = trade_value * rcep_rate / 100

        best_rate = rcep_rate
        best_scheme = "RCEP"

        fta_duty = None
        if fta_rate is not None and fta_rate < best_rate:
            best_rate = fta_rate
            best_scheme = "FTA"
            fta_duty = trade_value * fta_rate / 100

        savings = mfn_duty - (trade_value * best_rate / 100)

        comparisons.append({
            "hs_code": rule.hs_code,
            "partner": rule.partner_country,
            "trade_value_usd": round(trade_value, 2),
            "mfn_rate": mfn_rate,
            "rcep_rate": rcep_rate,
            "fta_rate": fta_rate,
            "mfn_duty_usd": round(mfn_duty, 2),
            "rcep_duty_usd": round(rcep_duty, 2),
            "fta_duty_usd": round(fta_duty, 2) if fta_duty is not None else None,
            "best_rate": best_rate,
            "best_scheme": best_scheme,
            "savings_vs_mfn_usd": round(savings, 2),
            "rule_of_origin": rule.rule_of_origin or "",
        })

    comparisons.sort(key=lambda x: x["savings_vs_mfn_usd"], reverse=True)

    total_savings = sum(c["savings_vs_mfn_usd"] for c in comparisons)
    return {
        "year": year,
        "total_rules_evaluated": len(comparisons),
        "total_potential_savings_usd": round(total_savings, 2),
        "comparisons": comparisons,
    }


# ── Supply Chain Map ──
@router.get("/supply-chain-map")
def get_supply_chain_map(
    year: int = Query(2023, description="Year for trade flow data"),
    db: Session = Depends(get_db),
):
    """Trade flow network data for graph visualization.

    Returns nodes (countries) and edges (trade flows with values)
    suitable for rendering in a network / graph visualization library.
    """
    countries = {c.code: c for c in db.query(Country).all()}

    # Build the central hub node (China)
    nodes = [
        {
            "id": "CHN",
            "name": "中国",
            "name_en": "China",
            "latitude": 35.86,
            "longitude": 104.19,
            "role": "hub",
            "gdp_billion_usd": None,
        }
    ]

    # Aggregate total export trade value per partner
    trade_totals = (
        db.query(
            TradeRecord.partner,
            func.sum(TradeRecord.trade_value_usd).label("total_value"),
        )
        .filter(TradeRecord.year == year, TradeRecord.trade_flow == "export")
        .group_by(TradeRecord.partner)
        .all()
    )
    trade_map = {t.partner: (t.total_value or 0) for t in trade_totals}

    for code, c in countries.items():
        if code == "CHN":
            continue
        nodes.append({
            "id": code,
            "name": c.name_cn,
            "name_en": c.name_en,
            "latitude": c.latitude,
            "longitude": c.longitude,
            "role": "partner",
            "gdp_billion_usd": c.gdp_billion_usd,
        })

    # Build edges from China to each trade partner
    max_trade = max(trade_map.values()) if trade_map else 1
    edges = []
    for partner_code, trade_val in trade_map.items():
        if trade_val <= 0:
            continue
        edges.append({
            "source": "CHN",
            "target": partner_code,
            "trade_value_usd": round(trade_val, 2),
            "thickness": round(max(0.5, trade_val / max_trade * 10), 2),
        })

    edges.sort(key=lambda e: e["trade_value_usd"], reverse=True)

    return {
        "year": year,
        "nodes": nodes,
        "edges": edges,
        "total_trade_flows": len(edges),
    }
