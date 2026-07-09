"""Socioeconomic Dashboard API Routes.

Provides macro-level socioeconomic analysis:
- /socioeconomic/macro-overview: ASEAN country macro indicators
- /socioeconomic/trade-impact: Trade impact on GDP, employment
- /socioeconomic/sustainability: ESG/sustainability metrics
- /socioeconomic/competitiveness: Trade competitiveness indices
"""

import hashlib

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.schemas_db import Country, TradeRecord

router = APIRouter()


# ── Macro Overview ──
@router.get("/macro-overview")
def get_macro_overview(
    year: int = Query(2023, description="Year for trade volume data"),
    db: Session = Depends(get_db),
):
    """Return GDP, population, trade volume, and growth rates for ASEAN countries.

    Combines static Country attributes with aggregated trade data from
    TradeRecord for the specified year.
    """
    asean_countries = db.query(Country).filter(Country.asean_member == 1).all()

    # Aggregate total trade value per partner for the year
    trade_totals = (
        db.query(
            TradeRecord.partner,
            func.sum(TradeRecord.trade_value_usd).label("total_value"),
        )
        .filter(TradeRecord.year == year)
        .group_by(TradeRecord.partner)
        .all()
    )
    trade_map = {t.partner: (t.total_value or 0) for t in trade_totals}

    # Derive a simple growth rate by comparing with the previous year
    trade_prev = (
        db.query(
            TradeRecord.partner,
            func.sum(TradeRecord.trade_value_usd).label("total_value"),
        )
        .filter(TradeRecord.year == year - 1)
        .group_by(TradeRecord.partner)
        .all()
    )
    prev_map = {t.partner: (t.total_value or 0) for t in trade_prev}

    countries_data = []
    for c in asean_countries:
        trade_volume = trade_map.get(c.code, 0)
        prev_volume = prev_map.get(c.code, 0)
        growth = (
            round((trade_volume - prev_volume) / prev_volume * 100, 2)
            if prev_volume > 0
            else 0.0
        )
        gdp = c.gdp_billion_usd or 0
        pop = c.population_million or 0
        trade_to_gdp = round(trade_volume / (gdp * 1e9) * 100, 2) if gdp > 0 else 0.0

        countries_data.append({
            "country": c.code,
            "country_name": c.name_cn,
            "country_name_en": c.name_en,
            "gdp_billion_usd": gdp,
            "population_million": pop,
            "gdp_per_capita_usd": round(gdp * 1e9 / (pop * 1e6), 2) if pop > 0 else 0,
            "trade_volume_usd": round(trade_volume, 2),
            "trade_to_gdp_pct": trade_to_gdp,
            "trade_growth_pct": growth,
            "rcep_member": bool(c.rcep_member),
        })

    countries_data.sort(key=lambda x: x["gdp_billion_usd"], reverse=True)
    return {
        "year": year,
        "region": "ASEAN",
        "countries": countries_data,
        "total_countries": len(countries_data),
    }


# ── Trade Impact ──
@router.get("/trade-impact")
def get_trade_impact(
    year: int = Query(2023, description="Year for analysis"),
    db: Session = Depends(get_db),
):
    """Calculate trade impact on macroeconomic indicators.

    Computes trade-to-GDP ratio, trade growth contribution, and
    employment proxy metrics for each trade partner country.
    """
    countries = {c.code: c for c in db.query(Country).all()}

    # Current year trade aggregation by partner
    current = (
        db.query(
            TradeRecord.partner,
            func.sum(TradeRecord.trade_value_usd).label("total_value"),
        )
        .filter(TradeRecord.year == year, TradeRecord.trade_flow == "export")
        .group_by(TradeRecord.partner)
        .all()
    )
    current_map = {t.partner: (t.total_value or 0) for t in current}

    # Previous year for growth calculation
    previous = (
        db.query(
            TradeRecord.partner,
            func.sum(TradeRecord.trade_value_usd).label("total_value"),
        )
        .filter(TradeRecord.year == year - 1, TradeRecord.trade_flow == "export")
        .group_by(TradeRecord.partner)
        .all()
    )
    prev_map = {t.partner: (t.total_value or 0) for t in previous}

    # Top product per partner
    top_products = {}
    top_product_rows = (
        db.query(
            TradeRecord.partner,
            TradeRecord.hs_code,
            func.sum(TradeRecord.trade_value_usd).label("val"),
        )
        .filter(TradeRecord.year == year, TradeRecord.trade_flow == "export")
        .group_by(TradeRecord.partner, TradeRecord.hs_code)
        .all()
    )
    for row in top_product_rows:
        p = row.partner
        v = row.val or 0
        if p not in top_products or v > top_products[p]["value"]:
            top_products[p] = {"hs_code": row.hs_code, "value": v}

    results = []
    total_global_trade = sum(current_map.values()) or 1

    for code, trade_val in current_map.items():
        c = countries.get(code)
        if not c:
            continue
        gdp = c.gdp_billion_usd or 0
        pop = c.population_million or 0
        trade_to_gdp = round(trade_val / (gdp * 1e9) * 100, 2) if gdp > 0 else 0.0

        prev_val = prev_map.get(code, 0)
        growth = (
            round((trade_val - prev_val) / prev_val * 100, 2)
            if prev_val > 0
            else 0.0
        )
        market_share = round(trade_val / total_global_trade * 100, 2)
        # Employment proxy: ~1 job per $50k of trade value
        employment_proxy = round(trade_val / 50_000)

        top = top_products.get(code, {})
        results.append({
            "country": code,
            "country_name": c.name_cn,
            "gdp_billion_usd": gdp,
            "trade_value_usd": round(trade_val, 2),
            "trade_to_gdp_pct": trade_to_gdp,
            "trade_growth_pct": growth,
            "market_share_pct": market_share,
            "employment_proxy": employment_proxy,
            "trade_intensity_index": round(trade_val / (pop * 1e6), 2) if pop > 0 else 0,
            "top_product_hs": top.get("hs_code", ""),
        })

    results.sort(key=lambda x: x["trade_value_usd"], reverse=True)
    return {
        "year": year,
        "total_export_partners": len(results),
        "total_export_value_usd": round(sum(current_map.values()), 2),
        "countries": results,
    }


# ── Sustainability ──
@router.get("/sustainability")
def get_sustainability(
    db: Session = Depends(get_db),
):
    """Return ESG / sustainability metrics for trade partner countries.

    Since real ESG data integration is planned for Phase 4, this
    endpoint uses deterministic mock data derived from country codes
    to provide stable, reproducible scores for frontend development.
    """
    countries = db.query(Country).all()
    results = []

    for c in countries:
        mock = _get_mock_esg(c.code)
        results.append({
            "country": c.code,
            "country_name": c.name_cn,
            "country_name_en": c.name_en,
            "carbon_intensity_kg_per_kusd": mock["carbon_intensity"],
            "environmental_score": mock["env_score"],
            "social_score": mock["social_score"],
            "governance_score": mock["gov_score"],
            "esg_rating": mock["rating"],
            "renewable_energy_pct": mock["renewable_pct"],
            "deforestation_risk": mock["deforestation_risk"],
            "labor_rights_index": mock["labor_rights"],
        })

    results.sort(key=lambda x: x["environmental_score"], reverse=True)
    return {
        "data_source": "deterministic_mock",
        "note": "Real ESG integration planned for Phase 4",
        "countries": results,
    }


def _get_mock_esg(country_code: str) -> dict:
    """Generate deterministic ESG scores from country code.

    Uses a hash of the country code so the same country always
    produces the same scores across runs, while different countries
    get varied but plausible values.
    """
    seed = int(hashlib.md5(country_code.encode()).hexdigest()[:8], 16)

    # Country-specific overrides for realistic baseline values
    overrides = {
        "SGP": {"carbon_intensity": 35, "env_score": 78, "social_score": 82, "gov_score": 90, "renewable_pct": 12, "deforestation_risk": "low", "labor_rights": 75},
        "MYS": {"carbon_intensity": 120, "env_score": 62, "social_score": 65, "gov_score": 68, "renewable_pct": 22, "deforestation_risk": "medium", "labor_rights": 60},
        "THA": {"carbon_intensity": 110, "env_score": 58, "social_score": 60, "gov_score": 55, "renewable_pct": 18, "deforestation_risk": "medium", "labor_rights": 55},
        "VNM": {"carbon_intensity": 150, "env_score": 52, "social_score": 58, "gov_score": 50, "renewable_pct": 28, "deforestation_risk": "medium", "labor_rights": 50},
        "IDN": {"carbon_intensity": 160, "env_score": 48, "social_score": 55, "gov_score": 52, "renewable_pct": 25, "deforestation_risk": "high", "labor_rights": 48},
        "PHL": {"carbon_intensity": 130, "env_score": 55, "social_score": 57, "gov_score": 53, "renewable_pct": 20, "deforestation_risk": "medium", "labor_rights": 52},
        "MMR": {"carbon_intensity": 180, "env_score": 40, "social_score": 35, "gov_score": 28, "renewable_pct": 45, "deforestation_risk": "high", "labor_rights": 30},
        "KHM": {"carbon_intensity": 170, "env_score": 42, "social_score": 40, "gov_score": 35, "renewable_pct": 55, "deforestation_risk": "high", "labor_rights": 35},
        "LAO": {"carbon_intensity": 140, "env_score": 50, "social_score": 42, "gov_score": 38, "renewable_pct": 70, "deforestation_risk": "medium", "labor_rights": 38},
        "BRN": {"carbon_intensity": 90, "env_score": 55, "social_score": 60, "gov_score": 72, "renewable_pct": 5, "deforestation_risk": "low", "labor_rights": 60},
    }

    if country_code in overrides:
        o = overrides[country_code]
        total_score = (o["env_score"] + o["social_score"] + o["gov_score"]) / 3
    else:
        # Generate plausible scores deterministically from hash
        o = {
            "carbon_intensity": 100 + (seed % 100),
            "env_score": 40 + (seed % 40),
            "social_score": 40 + ((seed >> 8) % 40),
            "gov_score": 40 + ((seed >> 16) % 40),
            "renewable_pct": 5 + (seed % 60),
            "deforestation_risk": ["low", "medium", "high"][seed % 3],
            "labor_rights": 30 + ((seed >> 4) % 50),
        }
        total_score = (o["env_score"] + o["social_score"] + o["gov_score"]) / 3

    if total_score >= 70:
        rating = "A"
    elif total_score >= 60:
        rating = "B"
    elif total_score >= 50:
        rating = "C"
    elif total_score >= 40:
        rating = "D"
    else:
        rating = "E"

    o["rating"] = rating
    return o


# ── Competitiveness ──
@router.get("/competitiveness")
def get_competitiveness(
    year: int = Query(2023, description="Year for analysis"),
    db: Session = Depends(get_db),
):
    """Compute trade competitiveness indices for trade partner countries.

    Calculates Revealed Comparative Advantage (RCA), market share, and
    growth competitiveness metrics to evaluate each partner's trade
    position.
    """
    countries = {c.code: c for c in db.query(Country).all()}

    # Current year aggregation by (partner, hs_chapter)
    chapter_data = (
        db.query(
            TradeRecord.partner,
            TradeRecord.hs_chapter,
            func.sum(TradeRecord.trade_value_usd).label("total_value"),
        )
        .filter(
            TradeRecord.year == year,
            TradeRecord.trade_flow == "export",
            TradeRecord.hs_chapter.isnot(None),
        )
        .group_by(TradeRecord.partner, TradeRecord.hs_chapter)
        .all()
    )

    # Total trade per country
    country_totals: dict[str, float] = {}
    # Total trade per HS chapter (global)
    chapter_globals: dict[int, float] = {}
    # Country -> chapter -> value
    country_chapter: dict[str, dict[int, float]] = {}

    for row in chapter_data:
        val = row.total_value or 0
        country_totals[row.partner] = country_totals.get(row.partner, 0) + val
        chapter_globals[row.hs_chapter] = chapter_globals.get(row.hs_chapter, 0) + val
        country_chapter.setdefault(row.partner, {})[row.hs_chapter] = val

    total_global = sum(chapter_globals.values()) or 1

    # Growth data: current year vs previous year totals
    current_totals = (
        db.query(
            TradeRecord.partner,
            func.sum(TradeRecord.trade_value_usd).label("total_value"),
        )
        .filter(TradeRecord.year == year, TradeRecord.trade_flow == "export")
        .group_by(TradeRecord.partner)
        .all()
    )
    current_map = {t.partner: (t.total_value or 0) for t in current_totals}

    prev_totals = (
        db.query(
            TradeRecord.partner,
            func.sum(TradeRecord.trade_value_usd).label("total_value"),
        )
        .filter(TradeRecord.year == year - 1, TradeRecord.trade_flow == "export")
        .group_by(TradeRecord.partner)
        .all()
    )
    prev_map = {t.partner: (t.total_value or 0) for t in prev_totals}

    # Find top RCA chapter per country
    top_rca: dict[str, dict] = {}
    for partner, chapters in country_chapter.items():
        country_total = country_totals.get(partner, 0)
        if country_total == 0:
            continue
        best_rca = 0.0
        best_ch = 0
        for ch, ch_val in chapters.items():
            ch_global = chapter_globals.get(ch, 0)
            s_ij = ch_val / country_total
            s_j = ch_global / total_global
            rca = round(s_ij / s_j, 2) if s_j > 0 else 0
            if rca > best_rca:
                best_rca = rca
                best_ch = ch
        top_rca[partner] = {"hs_chapter": best_ch, "rca": best_rca}

    # Assemble results
    results = []
    for code, c in countries.items():
        ct = country_totals.get(code, 0)
        market_share = round(ct / total_global * 100, 2)

        cur = current_map.get(code, 0)
        prev = prev_map.get(code, 0)
        growth = round((cur - prev) / prev * 100, 2) if prev > 0 else 0.0

        rca_info = top_rca.get(code, {"hs_chapter": 0, "rca": 0})
        results.append({
            "country": code,
            "country_name": c.name_cn,
            "country_name_en": c.name_en,
            "trade_value_usd": round(ct, 2),
            "market_share_pct": market_share,
            "growth_competitiveness_pct": growth,
            "top_rca_chapter": rca_info["hs_chapter"],
            "top_rca_value": rca_info["rca"],
            "gdp_billion_usd": c.gdp_billion_usd,
        })

    results.sort(key=lambda x: x["top_rca_value"], reverse=True)
    return {
        "year": year,
        "total_partners": len(results),
        "countries": results,
        "rca_note": "RCA > 1 indicates revealed comparative advantage in that sector",
    }
